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
""" TargetPoolMigration class: Handle the migration of a target pool.

"""
import warnings

from vm_network_migration.errors import *
from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor
from vm_network_migration.modules.target_pool_modules.target_pool import TargetPool
from vm_network_migration.utils import initializer
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from googleapiclient.errors import HttpError


class TargetPoolMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, target_pool_name, network, subnetwork,
                 preserve_instance_external_ip, region):
        """ Initialize a BackendServiceMigration object

        Args:
            project: project ID
            backend_service_name: name of the backend service
            network: target network
            subnetwork: target subnet
            preserve_instance_external_ip: whether preserve the external IP
            of the instances which serves this load balancer
            region: region of the internal load balancer
        """
        super(TargetPoolMigration, self).__init__()
        self.target_pool = TargetPool(self.compute, self.project,
                                      self.target_pool_name, self.region,
                                      self.network,
                                      self.subnetwork,
                                      self.preserve_instance_external_ip)
        self.instance_migration_handlers = []
        self.build_instance_migration_handlers()
        self.instance_group_migration_handlers = []
        self.build_instance_group_migration_handlers()

    def build_instance_migration_handlers(self):
        """ Use instance's selfLinks to create a list of InstanceMigrationHandler

        Returns:

        """
        for selfLink in self.target_pool.attached_single_instances_selfLinks:
            executor = SelfLinkExecutor(self.compute, selfLink,
                                        self.network,
                                        self.subnetwork,
                                        self.preserve_instance_external_ip)
            try:
                instance_migration_handler = executor.build_instance_migration_handler()
                self.instance_migration_handlers.append(
                    instance_migration_handler)
            except HttpError as e:
                if 'not found' in e._get_reason():
                    continue
                else:
                    raise e

    def build_instance_group_migration_handlers(self):
        """ Use instance group's selfLinks to create a list of
        InstanceGroupMigrationHandler

        Returns:

        """
        for selfLink in self.target_pool.attached_managed_instance_groups_selfLinks:
            executor = SelfLinkExecutor(self.compute, selfLink,
                                        self.network,
                                        self.subnetwork,
                                        self.preserve_instance_external_ip)
            try:
                instance_group_migration_handler = executor.build_instance_group_migration_handler()
                if instance_group_migration_handler != None:
                    self.instance_group_migration_handlers.append(
                        instance_group_migration_handler)
            except HttpError as e:
                if 'not found' in e._get_reason():
                    continue
                else:
                    raise e

    def network_migration(self):
        """ Migrate the backends of the target pool one by one from a legacy
            network to the target subnet.

        """
        print('Migrating the target pool: %s' % (self.target_pool_name))
        try:
            for instance_migration_handler in self.instance_migration_handlers:
                print('Migrating: %s.'
                      % (instance_migration_handler.original_instance_name))
                instance_migration_handler.network_migration()
                print('Reattaching the instance to the target pool')
                self.target_pool.add_instance(
                    instance_migration_handler.get_instance_selfLink())

            for instance_group_migration_handler in self.instance_group_migration_handlers:
                print('Migrating: %s.'
                      % (instance_group_migration_handler.instance_group_name))
                instance_group_migration_handler.network_migration()

        except Exception as e:
            warnings.warn(e, Warning)
            print(
                'The target pool migration was failed. '
                'Rolling back to its original network.')
            self.rollback()
            raise MigrationFailed('Rollback finished.')

    def rollback(self):
        """ Rollback

        Returns:

        """
        warnings.warn('Rolling back: %s.' % (self.target_pool_name), Warning)
        for instance_migration_handler in self.instance_migration_handlers:
            instance_migration_handler.rollback()
            print('Reattaching the instance (%s) to the target pool' %(instance_migration_handler.original_instance_name))
            self.target_pool.add_instance(
                instance_migration_handler.get_instance_selfLink())

        for instance_group_migration_handler in self.instance_group_migration_handlers:
            instance_group_migration_handler.rollback()
            if instance_group_migration_handler.instance_group != None:
                print('Reattaching the instance group (%s) to the target pool' %(instance_group_migration_handler.instance_group_name))
                instance_group_migration_handler.instance_group.set_target_pool(
                    self.target_pool.selfLink)
