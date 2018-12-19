from __future__ import absolute_import
from __future__ import print_function

# Math helpers
from vehicle.skills.util import core
from shared.util.error_reporter import error_reporter as er

# The base class for all Skills
from vehicle.skills.skills import Skill


class Horizon(Skill):
    """
    Lock the gimbal pitch to the horizon while following
    """

    def __init__(self):
        """ Constructor for the Skill. Called whenever the user switches the active skill. """
        super(Horizon, self).__init__()

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

    def update(self, api):
        """ Called by the sdk multiple times a second. """
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
            er.REPORT_STATUS("no positions")
            return

        # Image space requirements, to keep from looking down.
        # Ideally this would work, but it doesn't.
        api.focus.set_image_space(weight=1.0, dead_zone_x=0.0, dead_zone_y=1.0)
        api.focus.settings.image_space.centering_aggressiveness = 0.0

        # Command a specific heading so vehicle continues yawing to maintain centered subject in X.
        delta = subject - vehicle
        heading = core.azimuth(delta)
        api.movement.set_heading(heading, weight=1.0)

        # Kill the heading rate, in case that is doing something.
        api.movement.set_heading_rate(0, weight=0.0)

        # Enforce a particular pitch.
        pitch = 0
        api.movement.set_gimbal_pitch(pitch, weight=1.0)
