from __future__ import absolute_import
from __future__ import print_function

from math import pi, cos, sin
from euler import Vector3
from shared.util.common.math import clamp, mod_2_pi

from vehicle.skills_sdk.skills import Skill
from vehicle.skills_sdk.util.ui import UiButton
from vehicle.skills_sdk.util.ui import UiRadioGroup
from vehicle.skills_sdk.util.ui import UiRadioOption
from vehicle.skills_sdk.util.ui import UiSlider


M_2PI = 2 * pi


class PolygonPath(Skill):
    """
    Fly in the shape of a polygon with a user-defined number of sides.
    """

    # These are custom settings that will appear during flight as adjustable UI in the Skydio app.
    USER_SETTINGS = (
        UiSlider(
            identifier="num_sides",
            label="Sides",
            detail="The number of sides for this polygon.",
            min_value=3,
            max_value=8,
            value=4,
            units="",
        ),
        UiSlider(
            identifier="radius",
            label="Radius",
            detail="The distance from the center of the polygon to one of its vertices.",
            min_value=1,
            max_value=20,
            value=4,
            units="m",
        ),
        UiRadioGroup(
            identifier='direction',
            label='Direction',
            detail='',
            options=[
                UiRadioOption(
                    identifier='normal',
                    label='Clockwise',
                    detail='',
                ),
                UiRadioOption(
                    identifier='invert',
                    label='Counter-Clockwise',
                    detail='',
                ),
            ],
            selected_option=0,
        ),
    )

    def __init__(self):
        """ Constructor for the Skill. Called whenever the user switches the active skill. """
        super(PolygonPath, self).__init__()
        self.center = None
        self.desired_position = None
        self.index = 0
        self.running = False

    def button_pressed(self, api, button_id):
        """ Called by the sdk whenever the user presses a button """
        if button_id == 'start':
            self.running = True
        elif button_id == 'stop':
            self.running = False

    def setting_changed(self, api, setting_id):
        """ Called by the sdk whenever the user adjusts a setting """
        self.desired_position = None
        if setting_id == 'num_sides':
            self.index = 0

    def get_onscreen_controls(self, api):
        """ Add buttons and titles to the skydio app based on current skill state. """
        num_sides = int(self.get_value_for_user_setting('num_sides'))
        controls = dict()
        if self.running:
            controls['show_stop'] = True
            controls['buttons'] = []

            # Show a title based on the current index.
            current = int(self.index + 1)
            controls['title'] = 'Vertex {}/{}'.format(current, num_sides)

        else:
            controls['show_stop'] = False
            controls['buttons'] = [UiButton(identifier='start', label='Start')]
            controls['title'] = '{}-Sided Polygon'.format(num_sides)
        return controls

    def update(self, api):
        """ Called by the sdk multiple times a second. """
        if not self.running:
            # Re-enable manual control
            api.phone.enable_movement_commands()
            self.center = None
            return

        # Disable manual control during autonomous motion.
        api.phone.disable_movement_commands()

        # Get latest setting values
        num_sides = float(self.get_value_for_user_setting('num_sides'))
        radius = self.get_value_for_user_setting('radius')
        direction = -1 if self.get_value_for_user_setting('direction') == 'normal' else 1

        if self.center is None:
            self.center = api.vehicle.get_position()
            print("new center {}".format(self.center))

        if self.desired_position is None:
            desired_angle = self.index / num_sides * M_2PI
            self.desired_position = self.center + radius * Vector3(cos(desired_angle), sin(desired_angle), 0)
            print("new desired position {}".format(self.desired_position))

        # Compute the distance between our goal and the vehicle
        delta = self.desired_position - api.vehicle.get_position()

        # Are we close enough?
        if delta.magnitude() < 0.5:
            # Clear state here so it gets set again on the next call to update()
            self.desired_position = None
            self.index = (self.index + direction) % num_sides
            self.set_needs_layout()
            print("close enough, advancing to {}".format(self.index))

        else:
            # move to the desired position
            api.movement.set_desired_pos_nav(self.desired_position)
            # look in the horizontal direction of the desired position
            api.movement.set_heading(delta.azimuth())
