# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" RegionalManagedInstanceGroup: describes a multi-zone managed instance group
"""
from copy import deepcopy

from vm_network_migration.modules.managed_instance_group import ManagedInstanceGroup
from vm_network_migration.modules.operations import Operations


class RegionalManagedInstanceGroup(ManagedInstanceGroup):
    def __init__(self, compute, project, instance_group_name, region):
        """ Initialization

        Args:
            compute: compute engine
            project: project ID
            instance_group_name: name of the instance group
            region: region of the instance group
        """
        super(RegionalManagedInstanceGroup, self).__init__(compute, project,
                                                           instance_group_name)
        self.zone_or_region = region
        self.operation = Operations(self.compute, self.project, None, region)
        self.instance_group_manager_api = self.compute.regionInstanceGroupManagers()
        self.autoscaler_api = self.compute.regionAutoscalers()
        self.is_multi_zone = True
        self.original_instance_group_configs = self.get_instance_group_configs()
        self.new_instance_group_configs = deepcopy(
            self.original_instance_group_configs)
        self.autoscaler = self.get_autoscaler()
        self.autoscaler_configs = self.get_autoscaler_configs()
        self.selfLink = self.get_selfLink(self.original_instance_group_configs)
