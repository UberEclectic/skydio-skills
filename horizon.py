from __future__ import absolute_import
from __future__ import print_function

from shared.util.time_manager import time_manager as tm

# The base class for all Skills
from vehicle.skills.skills import Skill



class Horizon(Skill):
    """
    Lock the gimbal pitch to the horizon while following
    """

    def __init__(self):
        """ Constructor for the Skill. Called whenever the user switches the active skill. """
        super(Horizon, self).__init__()
        self.downsampler = tm.DownSampler(1.0)

    def get_onscreen_controls(self, api):
        """ Add buttons and titles to the skydio app based on current skill state. """
        controls = {}
        controls['height_slider_enabled'] = True
        controls['arrows_enabled'] = True
        if api.subject.has_subject_track():
            controls['show_stop'] = True
            controls['zoom_slider_enabled'] = True
            controls['steering_enabled'] = False
            controls['double_tap_enabled'] = False
            controls['drag_enabled'] = False
            controls['tap_targets_enabled'] = False
        else:
            controls['show_stop'] = False
            controls['zoom_slider_enabled'] = False
            controls['steering_enabled'] = True
            controls['double_tap_enabled'] = True
            controls['drag_enabled'] = True
            controls['tap_targets_enabled'] = True
        return controls

    def button_pressed(self, api, button_id):
        if button_id == 'stop':
            api.subject.cancel_subject_tracking(api.utime)

    def update(self, api):
        """ Called by the sdk multiple times a second. """
        if self.downsampler.ready(api.utime):
            # update the phone at least once a second, in case it missed a change.
            self.set_needs_layout()

        api.phone.copy_az_el_range_settings(api.focus.settings)

        if not api.subject.has_subject_track():
            # Re-enable manual control
            api.phone.enable_movement_commands()
            return

        # Disable manual control during autonomous motion.
        api.phone.disable_movement_commands()

        subject = api.subject.get_position()
        vehicle = api.vehicle.get_position()
        if subject is None or vehicle is None:
            return

        # Image space requirements, to keep from camera from looking down...
        # ... unless the subject is going to leave the frame.
        api.focus.set_image_space(weight=1.0, dead_zone_x=0.0, dead_zone_y=1.0)
        api.focus.settings.image_space.centering_aggressiveness = 0.0

        # Kill the heading rate, if any.
        api.movement.set_heading_rate(0, weight=0.0)

        # Enforce a flat pitch.
        api.movement.set_gimbal_pitch(pitch_radians=0, weight=1.0)
