"""
Roof Scan
"""
from __future__ import absolute_import
import enum
import json
import numpy as np

from shared.util.error_reporter import error_reporter as er
from shared.util.time_manager import time_manager as tm
from vehicle.skills.skills import Skill
from vehicle.skills.util import scanning_patterns
from vehicle.skills.util.ar import Prism
from vehicle.skills.util.motions.motion import Motion
from vehicle.skills.util.transform import trans_to_msg  # XXX
from vehicle.skills.util.transform import Transform
from vehicle.skills.util.ui import UiButton
from vehicle.skills.util.ui import UiSlider


class MissionStatus(enum.Enum):
  # System awaiting mission parameters.
  CONFIG_REQUIRED = 0

  # Auto-init the gps
  CALIBRATING = 1

  # The mission is running.
  IN_PROGRESS = 2

  # The mission finished successfully.
  COMPLETED = 3

  # User aborted the mission.
  ABORTED = 4

  # There was a code problem.
  ERROR = 5


class RoofInspection(Skill):
    """
    Capture a roof by flying around it.

    Waits for a valid gps_polygon to be available and creates a series of waypoints.
    Each waypoint has a 'waypoint' used to visualize the lookat point,
    and these are sent to the phone for AR rendering.

    Once the user starts the mission, the drone will keep moving toward the next waypoint.
    If the drone is unable to make progress, it will move on to the following waypoint.
    """

    # Add some settings so this app is useable from the Skydio App too

    USER_SETTINGS = (
        UiSlider(
            identifier='length',
            label='Roof Length',
            detail="Length of the roof in front of R1",
            units='m',
            min_value=5,
            max_value=50,
            value=10.0,
        ),
        UiSlider(
            identifier='width',
            label='Roof Width',
            detail="Width of the roof, assuming takeoff location in centered.",
            units='m',
            min_value=5,
            max_value=50,
            value=10.0,
        ),
        UiSlider(
            identifier='min_height',
            label='Roof Height',
            detail="The estimated height of the roof",
            units='m',
            min_value=0,
            max_value=20,
            value=4.0,
        ),
        UiSlider(
            identifier='max_height',
            label='Max Altitude',
            detail="Maximum height above takeoff location which R1 will fly",
            units='m',
            min_value=5,
            max_value=40,
            value=10.0,
        ),
        UiSlider(
            identifier='speed',
            label='Speed',
            detail="Maximum R1 speed during motion.",
            units='m/s',
            min_value=0.1,
            max_value=8.0,
            value=3.0,
        ),
    )

    def __init__(self):
        super(RoofInspection, self).__init__()
        self.global_waypoints = []
        self.current_waypoint_index = None
        self.waypoint_start_utime = None
        self.status_code = MissionStatus.CONFIG_REQUIRED
        self.status_message = {}
        self.speed = 3.0
        self.publish_downsampler = tm.DownSampler(1.0)
        self.paused = False
        self._auto_init_start_utime = None
        self.pending_request = None

    def scan_abort(self, api):
        """
        Cancel the inspection in progress and reset state.
        """
        self.global_waypoints = []
        self.current_waypoint_index = None
        self.waypoint_start_utime = None
        api.scene.clear_all_objects()
        self.status_code = MissionStatus.ABORTED
        self.paused = False
        self._auto_init_start_utime = None
        self.pending_request = None
        return {}

    def handle_rpc(self, api, message):
        """
        Process incoming messages from the custom app, if any.
        """
        request = json.loads(message)
        rpc_type = request.get('@type')

        # Default response is an error.
        response = None

        if rpc_type == 'SCAN_REQUEST':
            self.process_scan_request(api, request)
            response = dict(paused=self.paused)

        elif rpc_type == 'SKIP_WAYPOINT':
            response = self.skip_waypoint(api)

        elif rpc_type == 'RETURN_TO_HOME':
            # TODO
            response = dict(paused=self.paused)

        elif rpc_type == 'SCAN_ABORT':
            response = self.scan_abort(api)

        elif rpc_type == 'PAUSE':
            if self.paused:
                er.REPORT_STATUS("resuming")
                self.paused = False
            else:
                er.REPORT_STATUS("pausing")
                self.paused = True
            response = dict(paused=self.paused)

        elif rpc_type == 'PING':
            return json.dumps(dict(data='PONG'))

        elif rpc_type == 'ECHO':
            return json.dumps(dict(echo=request.get('data')))

        else:
            er.REPORT_STATUS("Unhandled rpc type {}", rpc_type)

        if response is not None:
            response['status_code'] = self.status_code.name
            return json.dumps(response)
        else:
            return None

    def skip_waypoint(self, api):
        """
        Advance to the next waypoint immediately.
        """
        er.REPORT_STATUS("Skipping waypoint {}", self.current_waypoint_index)
        self.current_waypoint_index += 1
        self.waypoint_start_utime = api.utime
        response = {
            'current_waypoint_index': self.current_waypoint_index,
        }
        self.set_needs_layout()
        return response

    def button_pressed(self, api, button_id_pressed):
        """
        Handle UI button press events sent from the Skydio app.
        """
        if button_id_pressed == 'start':
            self.create_default_scan_request(api)
        elif button_id_pressed == 'stop':
            self.paused = True
        elif button_id_pressed == 'resume':
            self.paused = False
        elif button_id_pressed == 'abort':
            self.scan_abort(api)
        elif button_id_pressed == 'skip':
            self.skip_waypoint(api)
        else:
            er.REPORT_STATUS("button id {}", button_id_pressed)

    def create_default_scan_request(self, api):
        """
        Use the current location of the vehicle and user settings to create a scan.
        """

        nav_T_vehicle = api.vehicle.get_camera_trans()
        # Create a polygon with the vehicle at the center
        length = self.get_value_for_user_setting('length')
        width = self.get_value_for_user_setting('width')
        forward = length
        backward = 0.0
        left = width / 2.0
        right = width / 2.0
        nav_points = [
            nav_T_vehicle * np.array([-backward, left, 0]),
            nav_T_vehicle * np.array([forward, left, 0]),
            nav_T_vehicle * np.array([forward, -right, 0]),
            nav_T_vehicle * np.array([-backward, -right, 0]),
        ]
        request = {
            'min_height': self.get_value_for_user_setting('min_height'),
            'max_height': self.get_value_for_user_setting('max_height'),
            'speed': self.get_value_for_user_setting('speed'),
            'scan_patterns': ['PERIMETER', 'ROOFTOP'],
            'home_point_nav': nav_T_vehicle.position,
        }
        request['nav_polygon'] = nav_points
        self.pending_request = request

    def process_scan_request(self, api, request):
        """
        Create the scan from a json request.
        """
        if self.status_code == MissionStatus.IN_PROGRESS:
            return {
                'success': False,
                'error': 'scan in progress, request dropped',
            }

        gps_polygon = []
        for x, y in request['points']:
            point = np.array([float(x), float(y)])
            gps_polygon.append(point)

        defaults = {
            'min_height': 10.0,
            'max_height': 60.0,
            'speed': 3.0,
            'scan_patterns': ['PERIMETER', 'ROOFTOP'],
            'home_point': [None, None],
        }
        kwargs = dict(defaults, **{k: v for k, v in request.items() if k in defaults})
        kwargs['gps_polygon'] = gps_polygon
        self.pending_request = kwargs

    def manual_control_enabled(self):
        """
        Whether the user can manually move the drone.
        """
        if self.paused:
            return True
        return self.status_code not in (MissionStatus.CALIBRATING, MissionStatus.IN_PROGRESS)

    def get_onscreen_controls(self, api):
        """
        Populate the ui elements that should appear on the phone based on the mission status code.
        """

        buttons = []
        promoted_control_id = None
        if self.paused:
            title = 'Paused'
            detail = ''
            resume_btn = UiButton('resume', 'Resume')
            buttons.append(resume_btn)
            if self.status_code == MissionStatus.IN_PROGRESS:
                abort_btn = UiButton('abort', 'Abort', style='DANGER')
                buttons.append(abort_btn)

        elif self.status_code == MissionStatus.CONFIG_REQUIRED:
            title = 'Ready to Inspect'
            detail = 'Adjust settings then press start'
            start_btn = UiButton('start', 'Start', style='PRIMARY')
            buttons.append(start_btn)
            promoted_control_id = 'start'

        elif self.status_code == MissionStatus.CALIBRATING:
            title = 'Calibrating GPS'
            if self._auto_init_start_utime:
                delta = int(tm.utime_to_seconds(api.utime - self._auto_init_start_utime))
                detail = "t = {}".format(delta)
            else:
                detail = ''

        elif self.status_code == MissionStatus.IN_PROGRESS:
            title = 'Inspection in Progress'
            detail = "Waypoint {}/{}".format(self.current_waypoint_index, len(self.global_waypoints))
            skip_btn = UiButton('skip', 'Skip')
            buttons.append(skip_btn)
            promoted_control_id = 'skip'

        elif self.status_code == MissionStatus.COMPLETED:
            title = 'Inspection Complete'
            detail = 'Press start to scan again'
            start_btn = UiButton('start', 'Start', style='PRIMARY')
            buttons.append(start_btn)
            promoted_control_id = 'start'

        elif self.status_code == MissionStatus.ABORTED:
            title = 'Inspection Aborted'
            detail = 'Press start to scan again'
            start_btn = UiButton('start', 'Start', style='PRIMARY')
            buttons.append(start_btn)
            promoted_control_id = 'start'

        elif self.status_code == MissionStatus.ERROR:
            title = 'Error'
            detail = 'mission failure'

        controls = dict(
            title=title,
            detail=detail,
            show_stop=not self.manual_control_enabled(),
            height_slider_enabled=self.manual_control_enabled(),
            arrows_enabled=self.manual_control_enabled(),
            buttons=buttons,
            promoted_control=promoted_control_id or '',
        )

        return controls

    def update(self, api):
        """
        The main loop of the skill. This gets called at 8Hz.
        """

        # Stop tracking subjects.
        api.subject.cancel_if_following(api.utime)

        # Handle autonomous or manual control
        if self.manual_control_enabled():
            api.phone.enable_movement_commands()
            api.health_monitor.obey_lost_phone_connection_behavior()
        else:
            api.phone.disable_movement_commands()
            if self.status_code == MissionStatus.IN_PROGRESS:
                api.health_monitor.ignore_lost_phone_connection()

        if self.mission_in_progress(api):
            try:
                self.advance_mission(api)
            except Exception:
                er.REPORT_EXCEPTION_NOW("scan error")
                self.status_code = MissionStatus.ERROR

        if self.publish_downsampler.ready(api.utime):
            self.update_ar_scene(api)

            # Publish json status.
            status = dict(
                paused=self.paused,
                status_code=self.status_code.name,
                **self.status_message)
            if self.current_waypoint_index >= 0:
                status['current_waypoint_index'] = self.current_waypoint_index
            api.custom_comms.publish_status(json.dumps(status))

    def update_ar_scene(self, api):
        """
        Populate the augmented scene with the latest waypoints.
        """
        # Reset
        api.scene.clear_all_objects()

        # Add new prisms for each waypoint
        if self.global_waypoints:

            # Send up to 30 patches (waypoint nav trans) to the phone
            count = 30
            for i, waypoint_id in enumerate(self.global_waypoints):
                if (i + 2) < self.current_waypoint_index:
                    # This waypoint was already looked at some time ago, dont bother rendering.
                    continue
                if count < 0:
                    # Reached the max number of waypoints to send at once.
                    break
                count -= 1
                p = Prism()
                nav_T_center = api.waypoints.get_waypoint_in_nav(waypoint_id)


                # XXX: remove any lcm references
                if nav_T_center is not None:
                    # adjust the position forward so it appears better in the view.
                    nav_T_center.position = nav_T_center * np.array([2.0, 0, 0])
                    p.nav_T_center = trans_to_msg(nav_T_center)
                p.size.data = tuple((0.1, 1.0, 1.0))
                api.scene.add_prism(p)

    def create_mission(self, api, gps_polygon=None, nav_polygon=None,
                       home_point=(None, None),
                       home_point_nav=None,
                       min_height=3.0,
                       max_height=10.0,
                       speed=3.0,
                       scan_patterns=('PERIMETER', 'ROOFTOP')):
        """
        Build a series of global waypoints from the given nav or gps polygon and settings.
        """
        assert api.waypoints.ready_for_waypoints(), 'waypoint api not ready'

        self.current_waypoint_index = None
        self.speed = speed

        if home_point_nav is None:
            lat, lon = home_point
            if lat is not None and lon is not None:
                er.REPORT_STATUS("using home point {} {}", lat, lon)
                home_point_nav = api.waypoints.gps_to_nav(float(lat), float(lon))
                home_point_nav[2] = min_height
            else:
                er.REPORT_STATUS("using vehicle position, no home point set")
                home_point_nav = api.vehicle.get_position()

        if nav_polygon:
            nav_points = nav_polygon
        elif gps_polygon:
            # Convert the gps polygon to nav points, using the current altitude of the vehicle.
            nav_points = [api.waypoints.gps_to_nav(lat, lon) for lat, lon in gps_polygon]
        else:
            raise ValueError('must have nav or gps polygon')

        # Elevation will be incorrect - correct to current vehicle z
        for ind in range(len(nav_points)):
            if nav_points[ind] is not None:
                nav_points[ind][2] = min_height

        # The waypoint trans are computed in nav but we want record them in global.
        # This allows them to stay consistent as VIO drifts.
        nav_poses = []

        # Determine which patterns we are peforming.
        pattern_enums = tuple(scanning_patterns.ScanPattern[name] for name in scan_patterns)

        if scanning_patterns.ScanPattern.ORBIT in pattern_enums:
            er.REPORT_STATUS("adding ORBIT scan")
            orbit = scanning_patterns.orbit_prism(
                nav_points,
                height=max_height,
            )
            nav_poses += orbit

        if scanning_patterns.ScanPattern.PERIMETER in pattern_enums:
            er.REPORT_STATUS("adding PERIMETER scan")
            perimeter = scanning_patterns.perimeter_scan(
                nav_points,
                height=max_height,
                lookat_height=0.0,
                # Or look at the zero position of the opposite point? so, halfway up? max_height/2
            )
            nav_poses += perimeter

        if scanning_patterns.ScanPattern.PERIMETER_B in pattern_enums:
            er.REPORT_STATUS("adding PERIMETER_B scan")
            perimeter = scanning_patterns.perimeter_scan_b(
                nav_points,
                height=min_height,
                lookat_height=0.0,
                # Or look at the zero position of the opposite point? so, halfway up? max_height/2
            )
            nav_poses += perimeter

        # How far ahead should the lookat boxes be?
        lookat_range = 2.5

        # Then do an up-close scan of each face
        mid_height = 0.5 * (max_height + min_height)
        lawnmower = scanning_patterns.scan_prism(
            nav_points,
            height_limits=(2.0, mid_height),
            range_to_surface=lookat_range,
            scan_patterns=pattern_enums,
        )
        nav_poses += lawnmower

        # Go back to the home point when done.
        nav_poses += [Transform(position=home_point_nav)]

        # Record the lookat waypoints in global, so they are also robust to VIO drift.
        global_waypoints = [
            api.waypoints.save_nav_location(nav_T_vehicle * np.array([lookat_range, 0, 0]),
                                            orientation=nav_T_vehicle.rotation,
                                            waypoint_id=ind)
            for ind, nav_T_vehicle in enumerate(nav_poses)
        ]

        # Record the waypoints as gps coordinates, since these are visualized on a map
        # Orientation is lost, but it is later recovered from the associated waypoint
        waypoints = [list(api.waypoints.nav_to_gps(nav_T_vehicle.position))
                     for nav_T_vehicle in nav_poses]

        # Update state machine and the user-facing status
        self.status_code = MissionStatus.IN_PROGRESS
        self.waypoint_start_utime = api.utime
        self.current_waypoint_index = 0
        er.REPORT_STATUS("Starting mission with {} waypoints", len(waypoints))

        self.global_waypoints = global_waypoints
        self.status_message = {'waypoints': waypoints, 'debug_text': 'mission created'}

    def mission_in_progress(self, api):
        """
        Prep for the requested mission, if any, and return True if ready.
        """
        if not self.pending_request and not self.global_waypoints:
            return False

        # Fly backward until the gps initializes, or we exceed max distance
        ready = api.waypoints.ready_for_waypoints()
        if not ready:
            if self._auto_init_start_utime is None:
                self._auto_init_start_utime = api.utime

            # Abort if the calibration takes longer than 15 seconds.
            elapsed = tm.utime_to_seconds(api.utime - self._auto_init_start_utime)
            if elapsed > 15.0:
                self.scan_abort(api)
                self.set_needs_layout()
                return False

            # Fly forward until waypoints are available
            self.status_code = MissionStatus.CALIBRATING
            if not self.paused:
                api.phone.disable_movement_commands()
                api.movement.set_desired_vel_body(np.array([2.0, 0.0, 2.0]))
            else:
                api.phone.enable_movement_commands()

            self.set_needs_layout()
            return False

        elif ready and self.status_code == MissionStatus.CALIBRATING:
            self.status_code = MissionStatus.CONFIG_REQUIRED
            self.set_needs_layout()

        if self.pending_request is not None:
            self.create_mission(api, **self.pending_request)
            self.pending_request = None

        if not self.global_waypoints:
            # Can't process until a valid request has been made.
            return False

        if self.status_code != MissionStatus.IN_PROGRESS:
            # The mission is not active
            return False

        else:
            # This mission is actively running
            assert self.status_code == MissionStatus.IN_PROGRESS
            assert self.global_waypoints
            assert self.current_waypoint_index >= 0
            return True

    def advance_mission(self, api):
        """
        Continue working on the current mission.
        """
        if self.current_waypoint_index >= len(self.global_waypoints):
            if self.status_code != MissionStatus.COMPLETED:
                er.REPORT_STATUS("Mission Completed")
                self.status_code = MissionStatus.COMPLETED
                self.set_needs_layout()
            return

        if api.health_monitor.is_battery_low():
            er.REPORT_STATUS("battery low")

        waypoint_id = self.global_waypoints[self.current_waypoint_index]
        nav_T_waypoint = api.waypoints.get_waypoint_in_nav(waypoint_id)
        if nav_T_waypoint is None:
            raise ValueError('Referring to nonexistent waypoint')

        if self.paused:
            er.REPORT_QUIET("paused")
            return

        goal_position = nav_T_waypoint.position.copy()
        nav_t_vehicle = api.vehicle.get_position()
        distance = np.linalg.norm(nav_t_vehicle - goal_position)
        speed = self.speed

        if distance > 15.0:
            # Move faster if the waypoint is further away
            speed = 1.5 * speed

        time_elapsed = tm.utime_to_seconds(api.utime - self.waypoint_start_utime)

        is_stuck = bool(api.vehicle.get_speed() < 0.2)
        is_too_slow = is_stuck and time_elapsed > 3.0
        done = Motion.move_to_waypoint(api, waypoint_id, desired_speed=speed)

        max_time = 20.0
        if done:
            er.REPORT_STATUS("Completed waypoint {}", self.current_waypoint_index)
        elif is_too_slow:
            er.REPORT_STATUS("Too slow! Abandoning waypoint {}", self.current_waypoint_index)
        elif time_elapsed > max_time:
            er.REPORT_STATUS("Timed out! Abandoning waypoint {}", self.current_waypoint_index)
        else:
            # Keep working on the current waypoint
            return

        # Advance to the next waypoint
        self.current_waypoint_index += 1
        self.waypoint_start_utime = api.utime
        self.set_needs_layout()
