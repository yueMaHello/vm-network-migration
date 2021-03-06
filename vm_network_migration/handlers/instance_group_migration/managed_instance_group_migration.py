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

""" Migrate a managed instance group from its legacy network to a
target subnet.
"""

from enum import IntEnum
from warnings import warn

from vm_network_migration.errors import *
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.module_helpers.instance_group_helper import InstanceGroupHelper
from vm_network_migration.modules.instance_group_modules.instance_group import InstanceGroupStatus
from vm_network_migration.modules.other_modules.instance_template import InstanceTemplate
from vm_network_migration.utils import initializer


class ManagedInstanceGroupMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project,
                 network_name,
                 subnetwork_name, preserve_external_ip, zone, region,
                 instance_group_name):
        """Initialization

        Args:
            compute: google compute engine API
            project: project id
            network_name: target network
            subnetwork_name: target subnetwork
            preserve_external_ip: whether to preserve instances' external IPs
            zone: zone of a zonal instance group
            region: region of regional instance group
            instance_group_name: name
        """
        super(ManagedInstanceGroupMigration, self).__init__()
        self.instance_group = self.build_instance_group()
        self.original_instance_template = None
        self.new_instance_template = None
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
        """ Migrate the network of a managed instance group.
        The instance group will be recreated with a new
        instance template using the target subnet info.
        """
        self.migration_status = MigrationStatus(0)
        if self.preserve_external_ip:
            warn(
                'For a managed instance group, the external IP addresses '
                'of the instances can not be reserved.', Warning)
        target_pool_list = self.instance_group.get_target_pools()
        if len(target_pool_list) != 0:
            warn(
                'The instance group is serving target pools %s, ' 
                'please detach it from the target pool and then try again.' % (
                    target_pool_list), Warning)
            raise MigrationFailed('The migration didn\'t start.')

        if self.instance_group.autoscaler != None:
            warn(
                'The autoscaler serving the instance group will be deleted and recreated during the migration',
                Warning)

        print('Retrieving the instance template of %s.' % (
            self.instance_group_name))
        instance_template_name = self.instance_group.retrieve_instance_template_name(
            self.instance_group.original_instance_group_configs)
        self.original_instance_template = InstanceTemplate(
            self.compute,
            self.project,
            instance_template_name,
            self.zone,
            self.region,
            None,
            self.network_name,
            self.subnetwork_name)
        if self.original_instance_template.compare_original_network_and_target_network():
            print(
                'The instance template of %s is already using the target subnet.' % (
                    self.instance_group_name))
            return

        self.migration_status = MigrationStatus(1)
        print(
            'Generating a new instance template to use the target network information.')
        self.new_instance_template = self.original_instance_template.generating_new_instance_template_using_network_info()
        if self.new_instance_template == None:
            raise UnableToGenerateNewInstanceTemplate
        print('Inserting the new instance template %s.' % (
            self.new_instance_template.instance_template_name))
        self.new_instance_template.insert()
        self.migration_status = MigrationStatus(2)

        new_instance_template_link = self.new_instance_template.get_selfLink()
        print(
            'Modifying the instance group configs to use the new instance template')
        self.instance_group.modify_instance_group_configs_with_instance_template(
            self.instance_group.new_instance_group_configs,
            new_instance_template_link)
        print('Deleting: %s.' % (
            self.instance_group_name))
        self.instance_group.delete_instance_group()
        self.migration_status = MigrationStatus(3)
        print('Creating the instance group in the target subnet.')
        self.instance_group.create_instance_group(
            self.instance_group.new_instance_group_configs)
        self.migration_status = MigrationStatus(4)

    def rollback(self):
        """ Rollback

        """
        if self.migration_status >= 3:
            instance_group_status = self.instance_group.get_status()
            if instance_group_status != InstanceGroupStatus.NOTEXISTS:
                print('Deleting: %s.' % (self.instance_group_name))
                self.instance_group.delete_instance_group()
            self.migration_status = MigrationStatus(3)

        if self.migration_status == 3:
            print('Recreating the instance group: %s.' % (
                self.instance_group_name))
            self.instance_group.create_instance_group(
                self.instance_group.original_instance_group_configs
            )
            self.migration_status = MigrationStatus(2)

        if self.migration_status == 2:
            print('Deleting the new instance template.')
            self.new_instance_template.delete()
            self.migration_status = 0


class MigrationStatus(IntEnum):
    NOT_START = 0
    MIGRATING = 1
    NEW_INSTANCE_TEMPLATE_CREATED = 2
    ORIGINAL_GROUP_DELETED = 3
    NEW_GROUP_CREATED = 4
