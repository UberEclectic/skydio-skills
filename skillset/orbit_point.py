import enum
import numpy as np

from lcmtypes.skills import ui_variable_keys_t as keys
from shared.util.error_reporter import error_reporter as er
from vehicle.skills.skills.base import Skill
from vehicle.skills.util import ar
from vehicle.skills.util import ui


# TODO(matt): fix the phone API
def safe_get_key(phone_api, key):
    # This queries the variables without mutating it if the key is not set
    # This appears to be a problem because movement_t complains about None values.
    return phone_api.variables.vars.get(key)


# TODO(matt): add this to the phone API
def get_tap_ray(api):
    start = api.phone.ray_tracer._ray_start
    end = api.phone.ray_tracer._ray_end
    if start is None or end is None:
        return None
    ray = end - start
    length = np.linalg.norm(ray)
    return ray / length


# NOTE(matt): this just returns the result of a typical double tap and is limited to 7 meters.
def get_focus_position(api):
    return api.phone.ray_tracer._focus_position


class State(enum.Enum):
    # The vehicle is not moving itself, but the user can manual move it or double-tap
    STOPPED = 0
    APPROACHING = 1
    ORBITING = 2


# How far ahead of the vehicle should we look for voxels.
TEST_DEPTH = 5.0

# Offset lines draw from the vehicle's perspective so that they render better
VERTICAL_DRAWING_OFFSET = np.array([0, 0, -1.0])


class OrbitPoint(Skill):
    """
    Double tap on the screen to start orbiting a point
    """

    USER_SETTINGS = tuple([
        ui.UiSlider(
            identifier='max_distance',
            label='Max Search Distance',
            detail='The maximum distance the vehicle will travel during a double-tap',
            min_value=3,
            max_value=100,
            value=20,
            units='m'
        ),
        ui.UiSlider(
            identifier='orbit_range',
            label='Range',
            detail='The radius of the orbit',
            min_value=2,
            max_value=20,
            value=10,
            units='m'
        ),
    ])

    def __init__(self):
        self._state = State.STOPPED

        # The vehicle's location at the start of a double tap
        self.tap_start = None

        # The direction of the tap.
        self.tap_ray = None

        # Set once we have depth at the tap point.
        self.orbit_point = None

    @property
    def state(self):
        return self._state

    def set_state(self, new_state):
        er.REPORT_STATUS_NOW('State changed: {} -> {}', self._state, new_state)
        self._state = new_state

    def wait_for_tap(self, api):
        """
        Hold until we detect that the user double-tapped the image.
        """
        self.tap_ray = get_tap_ray(api)
        if self.tap_ray is not None:
            self.tap_start = api.vehicle.get_position()
            self.set_state(State.APPROACHING)

    def approach_point(self, api):
        """
        Move in the direction of the tap until we know the surface that the user tapped on.
        """
        # Don't let the phone control movement of the vehicle.
        assert self.tap_ray is not None

        start = api.vehicle.get_position()
        end = start + TEST_DEPTH * self.tap_ray

        # Use AR to draw the prism
        ray_prism = ar.make_cable_prism(start + VERTICAL_DRAWING_OFFSET, end)
        api.scene.clear_all_objects()
        api.scene.add_prism(ray_prism)

        # Get the distance from the start point to the nearest obstacle along the ray, or None.
        depth = api.obstacle_map.depth_test(start, end)
        if depth is not None and depth < TEST_DEPTH:
            # We've found a voxel, start orbiting.
            self.orbit_point = start + (depth * self.tap_ray)
            self.set_state(State.ORBITING)
            return

        # Check if we've exceeded the safety limit.
        # This prevents the vehicle from flying away if you tap on the sky.
        distance_traveled = np.linalg.norm(self.tap_start - api.vehicle.get_position())
        if distance_traveled > self.get_value_for_user_setting('max_distance'):
            self.set_state(State.STOPPED)
            return

        # Otherwise, keep moving along the ray.
        api.movement.set_desired_pos_nav(end)

    def perform_orbit(self, api):
        """
        Orbit the tap location until the user press stop or taps again.
        """
        api.focus.set_custom_subject(self.orbit_point)
        api.focus.set_azimuth_rate(0.5, weight=1.0)
        api.focus.set_range(self.get_value_for_user_setting('orbit_range'), weight=0.5)
        api.focus.set_keep_subject_in_sight(False)

        # Use AR to draw the point
        api.scene.clear_all_objects()
        ray_prism = ar.make_cable_prism(self.orbit_point, self.orbit_point + np.array([0, 0, 1.0]))
        api.scene.add_prism(ray_prism)

    def button_pressed(self, api, button_id):
        """
        React to the user pressing the stop button
        """
        if button_id == 'stop':
            self.set_state(State.STOPPED)
            self.orbit_point = None
            self.tap_ray = None

    def get_onscreen_controls(self, api):
        """
        Determine what messaging to show and controls to enable based on state.
        """
        controls = {}
        controls['drag_enabled'] = True
        controls['tap_targets_enabled'] = False
        controls['double_tap_enabled'] = True
        controls['title'] = self.state.name
        if self.state == State.STOPPED:
            controls['show_stop'] = False
            controls['height_slider_enabled'] = True
        else:
            controls['show_stop'] = True
            controls['height_slider_enabled'] = False

        if self.state == State.ORBITING:
            controls['promoted_control'] = 'orbit_range'
        else:
            controls['promoted_control'] = None

        return controls

    def update(self, api):
        """
        Periodically update the state machine based on api changes.
        """
        if self.state == State.STOPPED:
            # Allow the user to move the vehicle manually
            api.phone.enable_movement_commands()

            # Check for the double-tap.
            self.wait_for_tap(api)
        else:
            # Disable movement commands if we aren't stopped
            api.phone.disable_movement_commands()

        if self.state == State.APPROACHING:
            self.approach_point(api)

        if self.state == State.ORBITING:
            self.perform_orbit(api)

        # Force the screen to redraw.
        self.set_needs_layout()
