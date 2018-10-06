from __future__ import absolute_import
from __future__ import print_function

from euler import Quaternion, Vector3
from math import pi, cos, sin
from shared.util.common.math import clamp, mod_2_pi
from shared.util.time_manager import time_manager as tm

from vehicle.skills_sdk.skills import Skill
from vehicle.skills_sdk.util.ar import Prism
from shared.util.body_shared.trans import Trans
from vehicle.skills_sdk.util.ui import UiButton
from vehicle.skills_sdk.util.ui import UiRadioGroup
from vehicle.skills_sdk.util.ui import UiRadioOption
from vehicle.skills_sdk.util.ui import UiSlider

from . import grid

M_2PI = 2 * pi


class Tetris(Skill):
    """
    Tetris
    """

    def __init__(self):
        """ Constructor for the Skill. Called whenever the user switches the active skill. """
        super(Tetris, self).__init__()
        # whether we are executing the polygon motion, or waiting for user control input.
        self.publish_downsampler = tm.DownSampler(0.5)

        self.grid = grid.Grid()

        self.nav_T_grid = None
        self.running = False

    def button_pressed(self, api, button_id):
        """ Called by the sdk whenever the user presses a button """
        print("user pressed {}".format(button_id))
        if button_id == 'start':
            self.running = True
        elif button_id == 'pause':
            self.running = False
        elif self.running and button_id in ('left', 'right'):
            self.grid.handle_action(button_id)

    def setting_changed(self, api, setting_id):
        """ Called by the sdk whenever the user adjusts a setting """
        pass

    def get_onscreen_controls(self, api):
        """ Add buttons and titles to the skydio app based on current skill state. """
        controls = dict()
        controls['height_slider_enabled'] = True
        controls['arrows_enabled'] = True
        controls['steering_enabled'] = True
        controls['drag_enabled'] = True
        if self.running:

            controls['title'] = ''
            # Show the red STOP button
            #controls['show_stop'] = True

            # Hide the manual controls and buttons
            controls['buttons'] = [UiButton(identifier='left', label='Left'),
                                  UiButton(identifier='right', label='Right'),
                                  UiButton(identifier='pause', label='Pause'),
                                  ]
            controls['promoted_control'] = 'pause'

        else:
            # Confirm the number of sides in the polygon with a title
            controls['title'] = 'Paused'

            # Enable manual controls and a Start Button
            #controls['height_slider_enabled'] = True
            controls['buttons'] = [UiButton(identifier='start', label='Start')]

            controls['promoted_control'] = ''
            # Hide the stop button
            #controls['show_stop'] = False

        return controls

    def update_ar_scene(self, api):
        """Draw prisms at our destination."""
        api.scene.clear_all_objects()
        if self.running:
            if not self.grid.update():
                self.grid = grid.Grid()

        grid_size = .5
        scale = .8
        cell_size = grid_size * scale
        for x, y in self.grid.visible_cells():
            p = Prism()
            center_rot = Quaternion.from_rpy(0, 0, 0)
            grid_T_cell = Trans(orientation=center_rot, position=Vector3(0, -x * grid_size + cell_size/2, y * grid_size - cell_size/2))
            nav_T_cell = (self.nav_T_grid * grid_T_cell)
            p = Prism()
            p.nav_T_center = nav_T_cell.get_lcm_msg()
            p.size.data = (cell_size, cell_size, cell_size)
            api.scene.add_prism(p)

    def update(self, api):
        """ Called by the sdk multiple times a second. """
        api.phone.enable_movement_commands()

        # Stop tracking any subjects
        api.subject.request_no_subject(api.utime)

        if self.nav_T_grid is None:
            self.nav_T_grid = api.vehicle.get_camera_trans()
            self.nav_T_grid.position = self.nav_T_grid * Vector3(10, 0, -2)

        if self.publish_downsampler.ready(api.utime):
            self.update_ar_scene(api)
