# Prepare for Python3 conversion
from __future__ import absolute_import
from __future__ import print_function

from vehicle.skills.skills import Skill


class Voxels(Skill):

    def update(self, api):
        api.phone.copy_az_el_range_settings(api.focus.settings)
