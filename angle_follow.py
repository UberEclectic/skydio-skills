from __future__ import absolute_import
from __future__ import print_function
import math
import numpy as np

# Math helpers
from vehicle.skills.util import core
import shared.util.common.math as ac_math
from shared.util.error_reporter import error_reporter as er
from shared.util.time_manager import time_manager as tm

# The base class for all Skills
from vehicle.skills.skills import Skill
from vehicle.skills.util.filters import AzimuthFilter
from vehicle.skills.util.image_space import ImageSpaceOffsets
from vehicle.skills.util.ui import UiSlider
from vehicle.skills.util.ui import UiToggle


class AngleFollow(Skill):
    """
    Follow the user from a specified angle relative to their velocity.
    """

    USER_SETTINGS = (
        UiSlider(
            identifier="angle",
            label="Angle",
            detail="The follow angle, relative to the subject's velocity.",
            min_value=-180,
            max_value=180,
            value=0,
            units="deg",
        ),
        UiToggle(
            identifier="pitch_lock",
            label="Look at Horizon",
            detail="Keep the camera aimed flat at the horizon, if possible.",
            value=False,
        ),
    )

    def __init__(self):
        super(AngleFollow, self).__init__()
        self.was_following = False
        self.downsampler = tm.DownSampler(1.0)

        # Helper for leading the subject in image space while moving.
        # Put the subject on the left of the frame if vehicle is filming from the side and the
        # subject is running left to right.
        self.image_space_offsets = ImageSpaceOffsets(
            max_x_offset_scale=-1.0/6,
            max_y_offset_scale=0.0,
            max_offset_speed=4.0
        )

        self.image_space_deadzone = (0.25, 0.2)

        # Minimum speed at which to use feedforward subject velocity, to prevent wobbling in hover.
        self.subject_velocity_min_feedforward = 2.0

        # Azimuth Filter
        self.azimuth_filter = AzimuthFilter(time_constant=2.0)

    def setting_changed(self, api, setting):
        if setting.id == 'angle':
            # round to the nearest 45
            new_value = ac_math.clamp(round(setting.value / 45.0) * 45, -180, 180)
            setting.value = new_value
            self.set_needs_layout()

    def button_pressed(self, api, button_id):
        if button_id == 'stop':
            api.subject.cancel_subject_tracking(api.utime)

    def get_onscreen_controls(self, api):
        """ Add buttons and titles to the skydio app based on current skill state. """
        controls = {}
        controls['height_slider_enabled'] = True
        if api.subject.has_subject_track():
            controls['arrows_enabled'] = False
            controls['show_stop'] = True
            controls['zoom_slider_enabled'] = True
            controls['steering_enabled'] = False
            controls['double_tap_enabled'] = False
            controls['drag_enabled'] = False
            controls['tap_targets_enabled'] = False
            controls['promoted_control'] = 'angle'
        else:
            controls['arrows_enabled'] = True
            controls['show_stop'] = False
            controls['zoom_slider_enabled'] = False
            controls['steering_enabled'] = True
            controls['double_tap_enabled'] = True
            controls['drag_enabled'] = True
            controls['tap_targets_enabled'] = True
            controls['promoted_control'] = None
        return controls

    def get_relative_azimuth_desired(self, api):
        """
        Convert the user's angle setting to a azimuth in radians
        """
        return -math.radians(self.get_value_for_user_setting('angle'))

    def compute_azimuth(self, api):
        subject_velocity = api.subject.get_velocity()
        relative_azimuth_desired = self.get_relative_azimuth_desired(api)
        vehicle_azimuth = api.vehicle.get_azimuth(reference_point=api.subject.get_position())

        # TODO(matt): we may want to lock this until the subject has moved significantly.
        subject_azimuth = self.azimuth_filter(api.utime, subject_velocity)

        if subject_azimuth is None or subject_velocity is None or relative_azimuth_desired is None or vehicle_azimuth is None:
            # Missing variables. Dont set aggressiveness
            api.focus.set_azimuth(weight=0.0)
            return

        subject_speed = np.linalg.norm(subject_velocity)

        azimuth = ac_math.mod_2_pi(subject_azimuth + relative_azimuth_desired)

        # Set the desired azimuth with max weight
        # TODO(matt): there may be situations where we want to lower the weight.
        # Like if the vehicle is getting stuck and could find a better way if the constraint was relaxed.
        api.focus.set_azimuth(azimuth, weight=1.0)

        offsets = self.image_space_offsets.get_image_space_offset(
            vehicle_azimuth, subject_azimuth, subject_velocity)

        # TODO(matt): convert to new api calls
        api.focus.settings.image_space.normalized_coordinates.data += offsets
        api.focus.settings.image_space.aggressiveness = 0.8
        api.focus.settings.image_space.dead_zone.data = self.image_space_deadzone

        # TODO(matt): how important are these?
        api.focus.settings.image_space.discounting_halflife = 0.25
        api.focus.settings.image_space.centering_aggressiveness = 0.1

        # Add a feed-forward vehicle velocity based on the subject.
        if subject_speed > self.subject_velocity_min_feedforward:
            api.movement.set_desired_vel_nav(subject_velocity, weight=0.1)

    def update(self, api):
        if self.downsampler.ready(api.utime):
            # update the phone at least once a second, in case it missed a change.
            self.set_needs_layout()

        # update ui when we change follow status
        following = api.subject.has_subject_track()
        if self.was_following != following:
            self.was_following = following
            self.set_needs_layout()

        self.compute_azimuth(api)

        # Copy the phone's settings for range and elevation
        api.phone.copy_az_el_range_settings(api.focus.settings)

        if following and self.get_value_for_user_setting('pitch_lock'):
            api.phone.disable_movement_commands()
            # Image space requirements, to keep from camera from looking down...
            # ... unless the subject is going to leave the frame.
            api.focus.set_image_space(weight=1.0, dead_zone_x=0.0, dead_zone_y=1.0)
            api.focus.settings.image_space.centering_aggressiveness = 0.0

            # Kill the heading rate, if any.
            api.movement.set_heading_rate(0, weight=0.0)

            # Enforce a flat pitch.
            api.movement.set_gimbal_pitch(pitch_radians=0, weight=1.0)
        else:
            api.phone.enable_movement_commands()
