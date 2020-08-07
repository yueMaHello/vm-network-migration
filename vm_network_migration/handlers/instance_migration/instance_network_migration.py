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

""" This script is used to migrate a GCP instance from its legacy network to a
subnetwork mode network.

"""
import warnings
from enum import IntEnum

from googleapiclient.http import HttpError
from vm_network_migration.errors import *
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.modules.instance_modules.instance import (
    Instance,
    InstanceStatus,
)
from vm_network_migration.utils import initializer


class InstanceNetworkMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, zone, original_instance_name,
                 network_name,
                 subnetwork_name, preserve_external_ip):
        """ Initialize a InstanceNetworkMigration object

        Args:
            project: project ID
            zone: zone of the instance
        """
        super(InstanceNetworkMigration, self).__init__()
        self.region = self.get_region()
        self.instance = Instance(self.compute, self.project,
                                 self.original_instance_name,
                                 self.region,
                                 self.zone, self.network_name,
                                 self.subnetwork_name,
                                 preserve_instance_ip=self.preserve_external_ip)
        self.migration_status = MigrationStatus(0)

    def get_region(self) -> dict:
        """ Get region information

            Returns:
                region name of the self.zone

            Raises:
                googleapiclient.errors.HttpError: invalid request
        """
        return self.compute.zones().get(
            project=self.project,
            zone=self.zone).execute()['region'].split('regions/')[1]

    def get_instance_selfLink(self):
        """  Get the selfLink of the instance

        Returns: URL string

        """
        if self.instance != None:
            return self.instance.selfLink

    def network_migration(self, force=False):
        """ The main method of the instance network migration process

        Args:
            original_instance_name: original instance's name
            network_name: target network name
            subnetwork_name: target subnetwork name
            preserve_external_ip: True/False

        Returns: None

        """
        self.migration_status = MigrationStatus(0)
        print('Migrating the VM: %s.' % (self.original_instance_name))
        if self.instance.compare_original_network_and_target_network():
            print('The VM %s is currently using the target subnet.' % (
                self.original_instance_name))
            return

        referrer_links = self.instance.get_referrer_selfLinks()
        if len(referrer_links) > 1 or (len(referrer_links) > 0 and not force):
            raise AmbiguousTargetResource(
                'The VM (%s) is a member of (%s), please detach the instance from its referrer and try again. '
                'Or you can try to migrate its referrer directly.' % (
                    self.original_instance_name, ','.join(referrer_links)))

        try:
            print('Checking the external IP address of %s.' % (
                self.original_instance_name))
            self.instance.address_object.preserve_ip_addresses_handler(
                self.preserve_external_ip)
            self.migration_status = MigrationStatus(1)
            print('Stopping: %s.' % (self.original_instance_name))
            self.instance.stop_instance()
            self.migration_status = MigrationStatus(2)

            print('Detaching the disks.')
            self.instance.detach_disks()
            self.migration_status = MigrationStatus(3)

            print('Deleting: %s.' % (self.original_instance_name))
            self.instance.delete_instance()
            self.migration_status = MigrationStatus(4)

            print('Creating the new VM in the target subnet: %s.' % (
                self.original_instance_name))
            self.instance.create_instance(self.instance.new_instance_configs)
            self.migration_status = MigrationStatus(5)
            print('The VM migration is successful.')


        except Exception as e:
            warnings.warn(str(e), Warning)
            self.rollback()
            raise MigrationFailed('Rollback to the original instance %s.' % (
                self.original_instance_name))

    def rollback(self):
        """ Rollback to the original VM. Reattach the disks to the
        original instance and restart it.
        """
        warnings.warn(
            'Rolling back: %s.' % (
                self.original_instance_name),
            Warning)
        if self.migration_status == 5:
            # The migration has been finished, but force to rollback
            print(
                'Stopping: %s.' % (
                    self.original_instance_name))
            self.instance.stop_instance()
            print('Detaching the disks.')
            self.instance.detach_disks()
            print('Deleting the instance (%s) in the target subnet.' % (
                self.original_instance_name))
            self.instance.delete_instance()
            self.migration_status = MigrationStatus(4)

        if self.migration_status == 4:
            print(
                'Recreating the original instance (%s) in the legacy network.' % (
                    self.original_instance_name))
            try:
                self.instance.create_instance(
                    self.instance.original_instance_configs)
            except:
                self.instance.create_instance_with_ephemeral_external_ip(
                    self.instance.original_instance_configs)
            self.migration_status = MigrationStatus(1)

        if self.migration_status == 2 or self.migration_status == 3:
            # All or part of the disks have already been detached
            print('Attaching disks back to the original VM: %s.' % (
                self.original_instance_name))
            try:
                self.instance.attach_disks()
            except HttpError as e:
                if 'already has a boot disk' in e._get_reason():
                    pass
                else:
                    raise e
            self.migration_status = MigrationStatus(2)

        if self.migration_status > 0 \
                and self.instance.get_instance_status() != self.instance.original_status:
            try:
                if self.instance.original_status == InstanceStatus.TERMINATED:
                    print(
                        'Restarting the original VM: %s' % (
                            self.original_instance_name))
                    self.instance.start_instance()
                else:
                    print(
                        'Stopping: %s.' % (
                            self.original_instance_name))
                    self.instance.stop_instance()
                self.migration_status = MigrationStatus(0)
            except:
                # Unable to set to the original status, but the rollback finished
                pass


class MigrationStatus(IntEnum):
    NOT_START = 0
    MIGRATING = 1
    STOPPED = 2
    DISK_DETACHED = 3
    ORIGINAL_DELETED = 4
    NEW_CREATED = 5
