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

""" Migrate a external backend service.

"""
import warnings

from vm_network_migration.errors import *
from vm_network_migration.handlers.backend_service_migration.global_backend_service_migration import GlobalBackendServiceNetworkMigration
from vm_network_migration.handlers.backend_service_migration.internal_backend_service_migration import InternalBackendServiceNetworkMigration
from vm_network_migration.module_helpers.backend_service_helper import BackendServiceHelper
from vm_network_migration.modules.backend_service_modules.backend_service import BackendService
from vm_network_migration.modules.backend_service_modules.internal_backend_service import InternalBackendService
from vm_network_migration.modules.backend_service_modules.global_backend_service import GlobalBackendService
from vm_network_migration.utils import initializer
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration

class BackendServiceMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, backend_service_name, network,
                 subnetwork,
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
        super(BackendServiceMigration, self).__init__()
        self.backend_service_migration_handler = None
        self.backend_service = self.build_backend_service()

    def build_backend_service(self) -> BackendService:
        """ Create a BackendService object.

        Returns: an BackendService object

        """
        backend_service_helper = BackendServiceHelper(
            self.compute,
            self.project,
            self.backend_service_name,
            self.network,
            self.subnetwork,
            self.preserve_instance_external_ip,
            self.region)
        backend_service = backend_service_helper.build_backend_service()
        return backend_service

    def network_migration(self):
        """ Migrate an external backend service's network
        """
        if self.backend_service.compare_original_network_and_target_network():
            print('The backend service %s is already using target subnet.' %(self.backend_service_name))
            return
        if isinstance(self.backend_service, GlobalBackendService):
            self.backend_service_migration_handler = GlobalBackendServiceNetworkMigration(
                self.compute,
                self.project, self.backend_service_name, self.network,
                self.subnetwork,
                self.preserve_instance_external_ip, self.region,
                self.backend_service)

        elif isinstance(self.backend_service, InternalBackendService):
            self.backend_service_migration_handler = InternalBackendServiceNetworkMigration(
                self.compute,
                self.project, self.backend_service_name, self.network,
                self.subnetwork,
                self.preserve_instance_external_ip, self.region,
                self.backend_service
            )
        else:
            print('Unsupported backend service. Migration stopped.')
        try:
            self.backend_service_migration_handler.network_migration()
        except Exception as e:
            warnings.warn(e, Warning)
            print(
                'The backend service migration was failed. Rolling back all the backends to its original network.')
            self.rollback()
            raise MigrationFailed('Rollback finished.')

    def rollback(self):
        """ Rollback

        Returns:

        """
        warnings.warn('Rolling back: %s.' %(self.backend_service_name), Warning)
        self.backend_service_migration_handler.rollback()
