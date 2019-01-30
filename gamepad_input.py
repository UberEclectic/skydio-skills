# prep for python 3.0
from __future__ import absolute_import
from __future__ import print_function
from collections import defaultdict

try:
    from inputs import get_gamepad
except ImportError:
    print('Unable to import the `inputs` module. See https://pypi.org/project/inputs/')
    get_gamepad = lambda: []

def clamp(val, tol=0.05):
    if abs(val) < tol:
        val = 0.0
    return val


class GamePad(object):
    """
    Track the state of the gamepad
    """
    def __init__(self):
        self.codes = defaultdict(int)

    def update(self):
        """
        Process events from the gamepad.
        This blocks until there is an event.
        """

        # TODO(matt): how to make this non-blocking?
        events = get_gamepad()

        for event in events:
            # Uncomment to print the values of the events for debugging.
            # print(event.ev_type, event.code, event.state)

            if event.ev_type == 'Sync':
                continue
            self.codes[event.code] = event.state

    def get_command(self):
        """ Return a vx, vy, vz, yaw_rate tuple. """

        # NOTE: these values come from testing with a Logitech Gamepad F310.
        # Other gamepads may have different layouts and maximums.
        max_hat = 32768.0

        # Vehicle +X (pitch) is out the front, and corresponds to up on the right stick.
        vx = -1.0 * self.codes['ABS_RY'] / max_hat

        # Vehicle +Y (roll) is out the left, and corresponds to left on the right stick.
        vy = -1.0 * self.codes['ABS_RX'] / max_hat

        # Vehicle +Z (altitude) is out the top, and corresponds to up on the left stick.
        vz = -1.0 * self.codes['ABS_Y'] / max_hat

        # Vehicle +yaw is counter-clockwise, and corresponds to left on the left stick.
        yaw_rate = -1.0 * self.codes['ABS_X'] / max_hat

        return (clamp(vx), clamp(vy), clamp(vz), clamp(yaw_rate))
