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

""" This script is used to migrate a GCP instance group from its legacy network to a
subnetwork mode network.

Ihe Google API python client module is imported to manage the GCP Compute Engine
 resources.
"""

import warnings
from warnings import warn

from vm_network_migration.errors import *
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.handlers.instance_group_migration.managed_instance_group_migration import ManagedInstanceGroupMigration
from vm_network_migration.handlers.instance_group_migration.unmanaged_instance_group_migration import UnmanagedInstanceGroupMigration
from vm_network_migration.module_helpers.instance_group_helper import InstanceGroupHelper
from vm_network_migration.modules.instance_group_modules.unmanaged_instance_group import UnmanagedInstanceGroup
from vm_network_migration.utils import initializer


class InstanceGroupNetworkMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project,
                 network_name,
                 subnetwork_name, preserve_external_ip, zone, region,
                 instance_group_name):
        """ Initialize a InstanceNetworkMigration object

        Args:
            project: project ID
            zone: zone of the instance group
            region:
        """
        super(InstanceGroupNetworkMigration, self).__init__()
        self.instance_group = self.build_instance_group()
        self.instance_group_migration_handler = self.build_instance_group_handler()

    def build_instance_group(self) -> object:
        """ Create an InstanceGroup object.

        Args:
            instance_group_name: the name of the instance group

        Returns: an InstanceGroup object

        """
        instance_group_helper = InstanceGroupHelper(self.compute,
                                                    self.project,
                                                    self.instance_group_name,
                                                    self.region,
                                                    self.zone,
                                                    self.network_name,
                                                    self.subnetwork_name,
                                                    self.preserve_external_ip)
        instance_group = instance_group_helper.build_instance_group()
        return instance_group

    def build_instance_group_handler(self):
        """ Build instance group handler based on the type of the instance group

        Returns:

        """
        if self.instance_group == None:
            self.instance_group = self.build_instance_group()

        if isinstance(self.instance_group, UnmanagedInstanceGroup):
            print('Migrating the unmanaged instance group: %s.' % (
                self.instance_group_name))
            self.instance_group_migration_handler = UnmanagedInstanceGroupMigration(
                self.compute, self.project,
                self.network_name,
                self.subnetwork_name, self.preserve_external_ip, self.zone,
                self.region,
                self.instance_group_name
            )
        else:
            print('Migrating the managed instance group: %s.' % (
                self.instance_group_name))
            self.instance_group_migration_handler = ManagedInstanceGroupMigration(
                self.compute, self.project,
                self.network_name,
                self.subnetwork_name, self.preserve_external_ip, self.zone,
                self.region,
                self.instance_group_name)
        return self.instance_group_migration_handler

    def network_migration(self):
        """ The main method of the instance network migration process

        Args:
            network_name: target network name
            subnetwork_name: target subnetwork name
            preserve_external_ip: preserve the external IP of the instances
            in an unmanaged instance group

        Returns: None

        """


        if self.instance_group_migration_handler == None:
            warnings.warn('Unable to get the instance group resource.')
            return
        try:
            self.instance_group_migration_handler.network_migration()

        except Exception as e:
            warn(e, Warning)
            print(
                'The migration was failed. Rolling back to the original network.')
            self.rollback()
            raise MigrationFailed('Rollback finished.')

    def rollback(self):
        """ Rollback to the original instance group

        """
        warnings.warn('Rolling back: %s.' % (self.instance_group_name), Warning)

        if self.instance_group == None or self.instance_group_migration_handler == None:
            print('Unable to fetch the instance group: %s.' % (
                self.instance_group_name))
            return
        else:
            self.instance_group_migration_handler.rollback()
            self.instance_group.migrated = False
