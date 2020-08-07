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

""" This script is used to migrate a global backend service
(external/internal-self-managed) from its legacy network to
a subnetwork mode network.

"""

from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor
from vm_network_migration.modules.backend_service_modules.global_backend_service import \
    GlobalBackendService
from vm_network_migration.utils import initializer
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration


class GlobalBackendServiceNetworkMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, backend_service_name, network,
                 subnetwork,
                 preserve_instance_external_ip, region, backend_service):
        """ Initialization

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
        super(GlobalBackendServiceNetworkMigration, self).__init__()
        self.backend_migration_handlers = []

        if backend_service == None:
            self.backend_service = GlobalBackendService(self.compute,
                                                        self.project,
                                                        self.backend_service_name,
                                                        self.network,
                                                        self.subnetwork,
                                                        self.preserve_instance_external_ip)

    def migrate_backends(self):
        """ Migrate the backends of the backend service one by one
        without deleting or recreating the backend service

        Args:
            backend_service_configs: the configs of the backend service

        """

        if 'backends' not in self.backend_service.backend_service_configs:
            return None
        backends = self.backend_service.backend_service_configs['backends']
        for backend in backends:
            migration_helper = SelfLinkExecutor(self.compute, backend['group'],
                                                self.network,
                                                self.subnetwork,
                                                self.preserve_instance_external_ip)
            backend_migration_handler = migration_helper.build_instance_group_migration_handler()
            # The backend type is not an instance group, then just ignore
            if backend_migration_handler == None:
                continue
            self.backend_migration_handlers.append(backend_migration_handler)
            print('Detaching: %s' % (backend['group']))
            self.backend_service.detach_a_backend(backend['group'])
            print('Migrating: %s' % (backend['group']))
            backend_migration_handler.network_migration()
            print('Reattaching: %s' % (backend['group']))
            self.backend_service.reattach_all_backends()

    def network_migration(self):
        """ Migrate the network of an external backend service.
        """
        print('Migrating an global backend service: %s' % (
            self.backend_service.backend_service_name))
        self.migrate_backends()

    def rollback(self):
        """ Rollback

        Returns:

        """
        if self.backend_service == None:
            print('Unable to fetch the backend service.')
            return
        # Rollback the instance group backends one by one
        for backend_migration_handler in self.backend_migration_handlers:
            if backend_migration_handler != None and backend_migration_handler.instance_group != None:
                print('Detaching: %s' % (
                    backend_migration_handler.instance_group.selfLink))
                self.backend_service.detach_a_backend(
                    backend_migration_handler.instance_group.selfLink)
                backend_migration_handler.rollback()
                print('Reattaching (%s) to (%s)' % (
                backend_migration_handler.instance_group.selfLink,
                self.backend_service_name))
                self.backend_service.reattach_all_backends()


