from vehicle.skills.skills import Skill


class Joysticks(Skill):
    """
    Control the drone with standard mode-2 onscreen sticks
    """

    def update(self, api):
        api.phone.copy_az_el_range_settings(api.focus.settings)

        # Cancel any currently tracked subject.
        api.subject.cancel_if_following(api.utime)
