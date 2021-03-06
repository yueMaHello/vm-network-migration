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
""" Helper class for creating an InstanceGroup object.
"""

from vm_network_migration.modules.instance_group_modules.regional_managed_instance_group import RegionalManagedInstanceGroup
from vm_network_migration.modules.instance_group_modules.unmanaged_instance_group import UnmanagedInstanceGroup
from vm_network_migration.modules.instance_group_modules.zonal_managed_instance_group import ZonalManagedInstanceGroup
from vm_network_migration.modules.instance_group_modules.instance_group import InstanceGroup
from vm_network_migration.utils import initializer


class InstanceGroupHelper:
    @initializer
    def __init__(self, compute, project, instance_group_name,
                 region, zone, network, subnetwork, preserve_instance_ip=False):
        """ Initialize an instance group helper object

        Args:
            compute: google compute engine
            project: project ID
            instance_group_name: name of the instance group
            region: region of the instance group
            zone: zone of the instance group
            preserve_instance_ip: only valid for an unmanaged instance group
        """

    def build_instance_group(self) -> InstanceGroup:
        """ Build an object which is an instance of the InstanceGroup's subclass
        """
        # try to build a zonal instance group
        try:
            instance_group_configs = self.get_instance_group_in_zone()
        except Exception:
            # It is not a single zone instance group
            pass
        else:
            if 'Instance Group Manager' not in instance_group_configs[
                'description']:
                return UnmanagedInstanceGroup(self.compute, self.project,
                                              self.instance_group_name,
                                              self.network,
                                              self.subnetwork,
                                              self.preserve_instance_ip,
                                              self.zone)
            else:
                return ZonalManagedInstanceGroup(self.compute,
                                                 self.project,
                                                 self.instance_group_name,
                                                 self.network,
                                                 self.subnetwork,
                                                 self.preserve_instance_ip,
                                                 self.zone)
        # try to build a regional instance group
        try:
            self.get_instance_group_in_region()
        except Exception as e:
            raise e
        else:
            return RegionalManagedInstanceGroup(self.compute, self.project,
                                                self.instance_group_name,
                                                self.network,
                                                self.subnetwork,
                                                self.preserve_instance_ip,
                                                self.region)

    def get_instance_group_in_zone(self) -> dict:
        """ Get a zonal instance group's configurations

        Returns: instance group's configurations

        """
        return self.compute.instanceGroups().get(
            project=self.project,
            zone=self.zone,
            instanceGroup=self.instance_group_name).execute()

    def get_instance_group_in_region(self) -> dict:
        """ Get a regional instance group's configurations

        Returns: instance group's configurations

        """
        return self.compute.regionInstanceGroups().get(
            project=self.project,
            region=self.region,
            instanceGroup=self.instance_group_name).execute()
