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

from enum import IntEnum

from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.module_helpers.instance_group_helper import InstanceGroupHelper
from vm_network_migration.utils import initializer


class UnmanagedInstanceGroupMigration(ComputeEngineResourceMigration):
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
        super(UnmanagedInstanceGroupMigration, self).__init__()
        self.instance_group = self.build_instance_group()
        self.instance_migration_handlers = []
        self.migration_status = MigrationStatus(0)

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

    def network_migration(self):
        """ Migrate the network of an unmanaged instance group.
          The instances belonging to this instance group will
          be migrated one by one.
          """
        self.migration_status = 0
        if self.instance_group.compare_original_network_and_target_network():
            print(
                'The instance group %s is already using the target subnet.' % (
                    self.instance_group_name))
            return
        self.migration_status = 1
        for instance_selfLink in self.instance_group.instance_selfLinks:
            selfLink_executor = SelfLinkExecutor(self.compute,
                                                 instance_selfLink,
                                                 self.network_name,
                                                 self.subnetwork_name,
                                                 self.preserve_external_ip)
            instance_migration_handler = selfLink_executor.build_migration_handler()

            if instance_migration_handler != None:
                self.instance_migration_handlers.append(
                    instance_migration_handler)
                # print('Detaching the instance %s.' %(instance_selfLink))
                # self.instance_group.remove_an_instance(instance_selfLink)
                instance_migration_handler.network_migration(force=True)
        self.migration_status = 2

        print('Deleting: %s.' % (
            self.instance_group_name))
        self.instance_group.delete_instance_group()
        self.migration_status = 3

        print(
            'Recreating the instance group using the same configuration in the new network.')
        self.instance_group.create_instance_group(
            self.instance_group.new_instance_group_configs)
        self.migration_status = 4
        print('Adding the instances back to the instance group: %s.' % (
            self.instance_group_name))
        self.instance_group.add_all_instances()
        self.migration_status = 5

    def rollback(self):
        """ Rollback an unmanaged instance group

        Returns:

        """
        if self.migration_status >= 4:
            # New instance group has been created, so it needs to be deleted
            self.instance_group.delete_instance_group()
            self.migration_status = MigrationStatus(4)

        if self.migration_status >= 3:
            # The original instance group has been deleted, it needs to be recreated.
            self.instance_group.create_instance_group(
                self.instance_group.original_instance_group_configs)
            self.migration_status = MigrationStatus(2)

        if self.migration_status >= 1:
            # Force to rollback all the instances to the original network
            print('Force to rollback all the instances in the group: %s.' % (
                self.instance_group_name))
            for instance_migration_handler in self.instance_migration_handlers:
                instance_migration_handler.rollback()
            print('Adding all instances back to the instance group: %s.' % (
                self.instance_group_name))
            self.instance_group.add_all_instances()
            self.migration_status = MigrationStatus(0)


class MigrationStatus(IntEnum):
    NOT_START = 0
    MIGRATING_INSTANCES = 1
    MIGRATED_ALL_INSTANCES = 2
    ORIGINAL_GROUP_DELETED = 3
    NEW_GROUP_RECREATED = 4
    FINISH = 5
