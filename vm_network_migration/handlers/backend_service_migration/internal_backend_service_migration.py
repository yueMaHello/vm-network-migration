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

""" This script is used to migrate an internal backend service
from its legacy network to a subnetwork mode network.

"""

from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor
from vm_network_migration.modules.backend_service_modules.internal_backend_service import \
    InternalBackendService
from vm_network_migration.utils import initializer
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from enum import IntEnum


class InternalBackendServiceNetworkMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, backend_service_name, network,
                 subnetwork,
                 preserve_instance_external_ip, region, backend_service):
        """ Initialize a InstanceNetworkMigration object

        Args:
            project: project ID
            backend_service_name: name of the backend service
            network: target network
            subnetwork: target subnet
            preserve_instance_external_ip: whether preserve the external IP
            of the instances which serves this load balancer
            region: region of the internal load balancer
            backend_service: an InternalBackEndService object
        """
        super(InternalBackendServiceNetworkMigration, self).__init__()
        self.backend_migration_handlers = []

        if self.backend_service == None:
            self.backend_service = InternalBackendService(self.compute,
                                                          self.project,
                                                          self.backend_service_name,
                                                          self.network,
                                                          self.subnetwork,
                                                          self.preserve_instance_external_ip,
                                                          self.region)
        self.migration_status = MigrationStatus(0)

    def migrate_backends(self):
        """ Migrate the backends of the backend service one by one

        Args:
            backend_service_configs: the configs of the backend service

        """
        if 'backends' not in self.backend_service.backend_service_configs:
            return None
        backends = self.backend_service.backend_service_configs['backends']
        for backend in backends:
            selfLink_executor = SelfLinkExecutor(self.compute, backend['group'],
                                                 self.network,
                                                 self.subnetwork,
                                                 self.preserve_instance_external_ip)
            backend_migration_handler = selfLink_executor.build_migration_handler()
            if backend_migration_handler != None:
                backend_migration_handler.network_migration()
                self.backend_migration_handlers.append(
                    backend_migration_handler)

    def network_migration(self):
        """ Migrate the network of an internal backend service.
        If there is a forwarding rule serving the backend service,
        the forwarding rule needs to be deleted and recreated.
        """
        self.migration_status = MigrationStatus(0)
        count_forwarding_rules = self.backend_service.count_forwarding_rules()
        if count_forwarding_rules == 1:
            print(
                'The backend service is in use by a forwarding rule. Please try the forwarding rule migration method instead.')
        elif count_forwarding_rules > 1:
            print(
                'The backend service is in use by two or more forwarding rules. It cannot be migrated. Terminating.')
        else:
            self.migration_status = MigrationStatus(1)
            print('Deleting: %s.' % (self.backend_service_name))
            self.migration_status = MigrationStatus(2)
            self.backend_service.delete_backend_service()
            print('Migrating the backends of %s one by one.' % (
                self.backend_service_name))
            self.migrate_backends()
            self.migration_status = MigrationStatus(3)
            print('Creating the backend service (%s) in the target subnet' % (
                self.backend_service_name))
            self.backend_service.insert_backend_service(
                self.backend_service.new_backend_service_configs)
            self.migration_status = MigrationStatus(4)

    def rollback(self):
        """ Rollback

        Returns:

        """
        if self.backend_service == None:
            print('Unable to fetch the backend service: %s.' % (
                self.backend_service_name))
            return
        if self.migration_status == 4:
            print('Deleting %s from the target subnet.' % (
                self.backend_service_name))
            self.backend_service.delete_backend_service()
            self.migration_status = MigrationStatus(3)
        if self.migration_status >= 2:
            print('Rolling back all the backends of %s' %(self.backend_service_name))
            for backend_migration_handler in self.backend_migration_handlers:
                backend_migration_handler.rollback()
            self.migration_status = MigrationStatus(2)
        if self.migration_status == 2:
            print('Recreating %s in the original network' % (
                self.backend_service_name))
            self.backend_service.insert_backend_service(
                self.backend_service.backend_service_configs)
            self.migration_status = 0


class MigrationStatus(IntEnum):
    NOT_START = 0
    MIGRATING = 1
    ORIGINAL_BACKEND_SERVICE_DELETED = 2
    BACKENDS_MIGRATED = 3
    NEW_BACKEND_SERVICE_CREATED = 4

