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

""" ForwardingRuleMigration class: It is the handler to migrate
a forwarding rule based on the type of it.

"""
import warnings

from vm_network_migration.errors import *
from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor
from vm_network_migration.module_helpers.forwarding_rule_helper import ForwardingRuleHelper
from vm_network_migration.utils import initializer
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.handlers.backend_service_migration.backend_service_migration import BackendServiceMigration


class ExternalForwardingRuleMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, forwarding_rule_name,
                 network_name, subnetwork_name,
                 preserve_instance_external_ip, region=None):
        """ Initialize a InstanceNetworkMigration object

        Args:
            project: project ID
            forwarding_rule_name: name of the forwarding rule
            network: target network
            subnetwork: target subnet
            preserve_instance_external_ip: whether preserve the external IP
            of the instances which serves this load balancer
            region: region of the internal load balancer
        """
        super(ExternalForwardingRuleMigration, self).__init__()
        self.forwarding_rule = self.build_forwarding_rule()
        self.backends_migration_handlers = []

    def build_forwarding_rule(self):
        """ Use a helper class to create a ForwardingRule object

        Returns: a ForwardingRule object

        """
        forwarding_rule_helper = ForwardingRuleHelper(self.compute,
                                                      self.project,
                                                      self.forwarding_rule_name,
                                                      self.network_name,
                                                      self.subnetwork_name,
                                                      self.region)
        return forwarding_rule_helper.build_a_forwarding_rule()



    def network_migration(self):
        """ Network migration for a external forwarding rule.
        The tool will migrate its backend services one by one.
        The forwarding rule will not be deleted or recreated.

        """
        if self.forwarding_rule.compare_original_network_and_target_network():
            print('The backend service %s is already using target subnet.' % (
                self.forwarding_rule_name))
            return

        backends_selfLinks = self.forwarding_rule.backends_selfLinks
        if backends_selfLinks == []:
            print(
                'No backend service needs to be migrated. Terminating the migration.')
            return

        for backends_selfLink in backends_selfLinks:
            selfLink_executor = SelfLinkExecutor(self.compute,
                                                 backends_selfLink,
                                                 self.network_name,
                                                 self.subnetwork_name,
                                                 self.preserve_instance_external_ip)
            try:
                backends_migration_handler = selfLink_executor.build_migration_handler()
            except UnsupportedBackendService:
                warnings.warn(
                    'The load balancing scheme of (%s) is not supported. '
                    'Continue migrating other backends.' % (backends_selfLink))
                continue            # Save handlers for rollback purpose
            if backends_migration_handler != None:
                if isinstance(backends_migration_handler,
                              BackendServiceMigration):
                    backend_service = backends_migration_handler.backend_service
                    if backend_service != None and backend_service.count_forwarding_rules() > 1:
                        print(
                            'The backend service is associated with two or more forwarding rules, \n'
                            'so it can not be migrated. \n'
                            'Terminating. ')
                        # this backend service will be ignored and will continue migrate other backend services
                        continue
                self.backends_migration_handlers.append(
                    backends_migration_handler)
                backends_migration_handler.network_migration()


    def rollback(self):
        """ Error happens. Rollback to the original status.

        """
        for backend_service_migration_handler in self.backends_migration_handlers:
            backend_service_migration_handler.rollback()