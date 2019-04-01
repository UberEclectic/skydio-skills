import math
import numpy as np

import shared.util.common.math as ac_math
from vehicle.skills.skills.base import Skill


class SubjectRelativeAzimuth(Skill):
    """ Stay a relative angle from the subject's motion. """

    def button_pressed(self, api, button_id):
        """ Called by the sdk whenever the user presses a button """
        print("user pressed {}".format(button_id))
        if button_id == 'stop':
            api.subject.cancel_subject_tracking(api.utime)

    def __init__(self):
        super(SubjectRelativeAzimuth, self).__init__()

        # You may want to expose these values as UiSliders
        self.elevation = 0.1  # [rad]
        self.range = 5.0  # [m]

        # Aggressiveness to apply to movement command matching velocity with subject
        self.subject_velocity_match_weight = 0.1

        # Minimum speed at which to use feedforward subject velocity, to prevent wobbling in hover.
        self.subject_velocity_min_feedforward = 2.0  # [m]

    def get_relative_azimuth_desired(self, api):
        raise NotImplementedError('subclass me')

    def get_onscreen_controls(self, api):
        """
        Disable most onscreen controls.
        """
        controls = {}
        controls['tap_targets_enabled'] = True
        controls['double_tap_enabled'] = True
        controls['drag_enabled'] = True

        has_subject = api.subject.has_subject_track()
        controls['height_slider_enabled'] = not has_subject
        controls['show_stop'] = has_subject
        return controls

    def update(self, api):
        self.set_needs_layout()

        has_subject = api.subject.has_subject_track()
        if not has_subject:
            api.phone.enable_movement_commands()
            return
        else:
            api.phone.disable_movement_commands()

        # Enforce a particular elevation with max weight
        api.focus.set_elevation(self.elevation, weight=1.0)

        # Lower the weight on range so that the vehicle prefers to keep elevation instead.
        api.focus.set_range(self.range, weight=0.5)

        # Compute the azimuth if possible.
        subject_azimuth = api.subject.get_azimuth()
        relative_azimuth_desired = self.get_relative_azimuth_desired(api)
        vehicle_azimuth = api.vehicle.get_azimuth(reference_point=api.subject.get_position())
        if not ((subject_azimuth is None)
                or (relative_azimuth_desired is None)
                or (vehicle_azimuth is None)):
            desired_azimuth = ac_math.mod_2_pi(subject_azimuth + relative_azimuth_desired)
            api.focus.set_azimuth(desired_azimuth, weight=1.0)
        else:
            api.focus.set_azimuth(weight=0)

        # Also apply a feed-forward velocity if the subject is moving.
        subject_velocity = api.subject.get_velocity()
        if (subject_velocity is not None
                and np.linalg.norm(subject_velocity) > self.subject_velocity_min_feedforward):
            api.movement.set_desired_vel_nav(subject_velocity,
                                             weight=self.subject_velocity_match_weight)


class Lead(SubjectRelativeAzimuth):
    """ Fly in front of the subject. """
    """ whether we are tracking, or waiting for user control input. """

    def get_relative_azimuth_desired(self, api):
        return 0.0


class Side(SubjectRelativeAzimuth):
    """ Go to the closest side of the subject. """

    def __init__(self):
        super(Side, self).__init__()
        self.relative_azimuth  = math.pi / 2.0

    def get_relative_azimuth_desired(self, api):
        subject_azimuth = api.subject.get_azimuth()
        vehicle_azimuth = api.vehicle.get_azimuth(reference_point=api.subject.get_position())

        if (vehicle_azimuth is not None) and (subject_azimuth is not None):
            # Whichever side is closest will determine the sign
            azimuth_diff_sign = np.sign(ac_math.angle_difference(vehicle_azimuth, subject_azimuth))
            relative_azimuth = azimuth_diff_sign * self.relative_azimuth
            return relative_azimuth
        else:
            return None
