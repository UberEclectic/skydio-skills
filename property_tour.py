import enum
import math

from euler import Quaternion, Vector3
from lcmtypes.ptree import subject_focus_state_enum_p  # XXX
from shared.util.body_shared.trans import Trans
from shared.util.error_reporter import error_reporter as er
from shared.util.time_manager import time_manager as tm
from vehicle.skills.skills import Skill
from vehicle.skills.util import core
from vehicle.skills.util.motions import CableMotion
from vehicle.skills.util.motions import OrbitMotion
from vehicle.skills.util.motions import LookatMotion
from vehicle.skills.util.ui import UiSlider
from vehicle.skills.util.ui import UiButton


class TourState(enum.Enum):
    # Wait for the user to start the tour
    SETUP = 0

    # Execute the tour
    GOTO = 1

    # Tapped STOP, quit the tour
    STOP = 5


class PropertyTour(Skill):
    """
    Create a simple tour based on the front door of a house
    and some basic size settings.
    """

    USER_SETTINGS = (
        UiSlider(
            identifier='speed',
            label='Speed',  # NOTE(matt): this text will update with the movement style.
            detail="Maximum R1 speed during motion.",
            units='m/s',
            min_value=0.1,
            max_value=8.0,
            value=6.0,
        ),
        UiSlider(
            identifier='width',
            label='Width',
            detail="The width of the house, assuming R1 is centered.",
            units='m',
            min_value=5,
            max_value=25,
            value=10,
        ),
        UiSlider(
            identifier='depth',
            label='Depth',
            detail="The depth of the house, assuming R1 is at one end.",
            units='m',
            min_value=0,
            max_value=50,
            value=15,
        ),
        UiSlider(
            identifier='height',
            label='Height',
            detail="Max altitude to fly.",
            units='m',
            min_value=5,
            max_value=30,
            value=15,
        ),
        UiSlider(
            identifier='radius',
            label='Radius',
            detail="Orbit radius",
            units='m',
            min_value=5,
            max_value=40,
            value=15,
        ),
    )

    def __init__(self):
        super(PropertyTour, self).__init__()
        self.state = TourState.SETUP
        self.has_subject = False

        self.start_point = None  # A point
        self.end_point = None  # B point
        self._goal_point_name = None
        self.publish_downsampler = tm.DownSampler(0.5)
        self._first_launch = True

        self.window_size = (0, 0)

        # AR cache
        self.ar_frames = []  # list of Trans for each cube in the frame(s)
        self._ar_needs_update = True

        self.params = core.AttrDict()
        self.params.speed = 4.0
        self.params.min_turn_rate = 1  # [rad/update]
        self.params.max_turn_rate = 20  # [rad/update]
        self.params.distance_margin = 0.5  # [m]
        self.params.angle_margin = math.radians(0.75)  # [rad]
        self.params.giveup_time = tm.seconds_to_utime(3)  # [s]
        self.params.giveup_speed = 0.1  # [m/s]

        self.motions = []
        self.motion_index = None

    def allow_manual_control(self):
        return self.state in (TourState.STOP, TourState.SETUP)

    @property
    def goal_point_name(self):
        return self._goal_point_name

    @property
    def goal_point_trans(self):
        if self.goal_point_name == 'A':
            return self.start_point
        elif self.goal_point_name == 'B':
            return self.end_point
        return None

    def button_pressed(self, api, button_id_pressed):
        if button_id_pressed == 'go':
            self.state = TourState.GOTO

            # Remember the current location.
            nav_T_cam = api.vehicle.get_camera_trans()

            roll, pitch, yaw = nav_T_cam.get_euler_angles()
            nav_T_cam_flat = nav_T_cam.copy()
            nav_T_cam_flat.orientation = Quaternion.from_rpy(0, 0, yaw)

            width = self.get_value_for_user_setting('width')
            depth = self.get_value_for_user_setting('depth')
            height = self.get_value_for_user_setting('height')
            radius = self.get_value_for_user_setting('radius')

            # The first point is the home point.
            nav_T_start = nav_T_cam.copy()

            # Fly backward
            nav_T_back = nav_T_cam_flat.copy()
            nav_T_back.position = nav_T_cam_flat * Vector3(-radius/2, 0, 0)

            # Fly Up
            nav_T_up = nav_T_cam_flat.copy()
            nav_T_up.position = nav_T_cam_flat * Vector3(-radius, 0, height)
            nav_T_up.orientation = Quaternion.from_rpy(0, math.radians(30), yaw)

            # Fly over the house
            nav_T_over = nav_T_cam_flat.copy()
            nav_T_over.position = nav_T_over * Vector3(depth, 0, height / 2)

            # Crane down
            nav_T_down = nav_T_cam_flat.copy()
            nav_T_down.position = nav_T_down * Vector3(-radius/4, 0, height)
            nav_T_down.orientation = Quaternion.from_rpy(0, math.radians(88), yaw)

            # Go left
            nav_T_left = nav_T_cam_flat.copy()
            nav_T_left.position = nav_T_left * Vector3(-5, width/2, 0)

            # Go Right
            nav_T_right = nav_T_cam_flat.copy()
            nav_T_right.position = nav_T_right * Vector3(-5, -width/2, 0)

            # The center of the house
            nav_T_lookat = nav_T_cam_flat.copy()
            nav_T_lookat.position = nav_T_cam_flat * Vector3(depth / 2, 0, 0)

            self.motions = [
                # Cable backward as far as possible
                CableMotion(nav_T_start, nav_T_up, self.params),

                # Move while looking at the house
                LookatMotion(
                    start_point=nav_T_up * Vector3(0, width, 0),
                    end_point=nav_T_up * Vector3(0, -width, 0),
                    lookat_point=nav_T_lookat.position,
                    params=self.params,
                ),

                # Orbit the center
                OrbitMotion(nav_T_lookat, radius, height, 1, self.params),

                # Fly down to the ground
                CableMotion(nav_T_up, nav_T_back, self.params),

                # Fly over the roof
                CableMotion(nav_T_back, nav_T_over, self.params),

                # Fly back and look down
                CableMotion(nav_T_over, nav_T_down, self.params),

                # Crane down to front door
                CableMotion(nav_T_down, nav_T_start, self.params),

                # Fly left
                CableMotion(nav_T_start, nav_T_left, self.params),

                # Fly right
                CableMotion(nav_T_left, nav_T_right, self.params),

                # Back to start
                CableMotion(nav_T_right, nav_T_start, self.params),

                # TODO:
                # Various panoramas in different spots
            ]
            self.motion_index = 0
            self._goal_point_name = 'A'
            er.REPORT_STATUS("go pressed")

        elif button_id_pressed == 'skip':
            er.REPORT_STATUS("skip")
            self.motion_index += 1
            if self.motion_index >= len(self.motions):
                self.motion_index = 0

        if button_id_pressed == 'goto_cable':
            self.state = TourState.GOTO

        if button_id_pressed == 'stop':
            er.REPORT_STATUS('stopped')
            api.subject.cancel_if_following(api.utime)
            self.state = TourState.STOP

    def get_motion(self):
        if self.motion_index is None or self.motion_index >= len(self.motions):
            return None
        return self.motions[self.motion_index]

    # XXX: I think this can be deleted
    def update_ui(self, api):
        if self.allow_manual_control():
            er.REPORT_QUIET("allowing update_ui")
            super(PropertyTour, self).update_ui(api)

    def update(self, api):
        # Stop following
        if self._first_launch:
            api.subject.cancel_if_following(api.utime)
            self._first_launch = False

        # Update the speed dynamically, in case the user changes it
        self.params.speed = self.get_value_for_user_setting('speed')

        if self.allow_manual_control():
            api.phone.enable_movement_commands()
        else:
            api.phone.disable_movement_commands()

        if api.planner.is_landing():
            er.REPORT_STATUS("Exiting due to planner landing")
            api.skills.request_skill(api.utime, 'Basic')

        # Check if the planner is ready for commands.
        # XXX: get rid of this?
        valid_subject_focus = api.subject.get_focus_state() in (
            subject_focus_state_enum_p.NO_SUBJECT,
            subject_focus_state_enum_p.FOLLOW,
            subject_focus_state_enum_p.SPOOFED_FOLLOW)

        self.has_subject = api.subject.is_following_subject(api.utime)

        # Execute the current motion.
        if api.vehicle.get_pose() and valid_subject_focus:
            if self.state == TourState.GOTO:
                motion = self.get_motion()
                if motion:
                    motion.update(api)
                    api.focus.ready = True
                    if motion.done:
                        motion.reset(api)
                        er.REPORT_STATUS("motion done, index ++ {}", self.motion_index)
                        self.motion_index += 1
                    else:
                        er.REPORT_STATUS("motion in progress")
                else:
                    er.REPORT_STATUS("No more motions")
                    self.state = TourState.STOP
            else:
                er.REPORT_QUIET("Not active")
        else:
            er.REPORT_QUIET("Vehicle not ready")

        # Update the ui periodically
        if self.publish_downsampler.ready(api.utime):
            self._layout_needs_update = True

    def get_onscreen_controls(self, api):
        title = ''
        detail_text = ''
        buttons = []
        show_stop = True
        controls_enabled = False
        targets_enabled = False
        show_slider = False
        progress = 0
        promoted_control_id = ''
        battery_low_land = api.health_monitor.is_battery_critically_low()

        if battery_low_land:
            title = 'Low Battery'
            detail_text = 'Cable Cam disabled'
            controls_enabled = True

        elif self.state == TourState.SETUP:
            title = 'Press Go to Start Tour'
            detail_text = 'R1 will automatically film the area.'
            controls_enabled = True
            show_stop = False
            targets_enabled = False
            buttons.append(UiButton('go', 'Go', style='PRIMARY'))
            promoted_control_id = 'go'

        elif self.state == TourState.GOTO:
            title = 'Running'
            detail_text = "index = {}".format(self.motion_index)
            show_slider = True
            targets_enabled = False
            buttons.append(UiButton('skip', label='Skip'))

        elif self.state == TourState.STOP:
            title = 'Press Go to Start Tour'
            controls_enabled = True
            show_stop = False
            targets_enabled = False
            buttons.append(UiButton('go', 'Go', style='PRIMARY'))
            promoted_control_id = 'go'

        else:
            er.REPORT_WARNING('Unknown state "{}"'.format(self.state))

        return dict(
            # state
            title=title,
            detail=detail_text,
            progress_ratio=progress,

            # movement controls
            arrows_enabled=controls_enabled,
            height_slider_enabled=controls_enabled,
            zoom_slider_enabled=controls_enabled and self.has_subject,
            steering_enabled=controls_enabled and not self.has_subject,
            tap_targets_enabled=targets_enabled,
            double_tap_enabled=controls_enabled,
            drag_enabled=controls_enabled,
            show_stop=show_stop,
            promoted_control='speed' if show_slider else promoted_control_id,
            buttons=buttons,
        )

