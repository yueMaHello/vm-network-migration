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
from enum import IntEnum

class InternalForwardingRuleMigration(ComputeEngineResourceMigration):
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
        super(InternalForwardingRuleMigration, self).__init__()
        self.forwarding_rule = self.build_forwarding_rule()
        self.backends_migration_handlers = []
        self.migration_status = MigrationStatus(0)

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
        """ Network migration for an internal forwarding rule.
         The forwarding rule will be deleted first.
         Then, the tool will migrate the backend service.
         Finally, recreate the forwarding rule in the target subnet.

         Returns:

         """
        if self.forwarding_rule.compare_original_network_and_target_network():
            print('The backend service %s is already using target subnet.' % (
                self.forwarding_rule_name))
            return

        backends_selfLinks = self.forwarding_rule.backends_selfLinks
        for backends_selfLink in backends_selfLinks:
            selfLink_executor = SelfLinkExecutor(self.compute,
                                                 backends_selfLink,
                                                 self.network_name,
                                                 self.subnetwork_name,
                                                 self.preserve_instance_external_ip)
            # the backends can be a target instance or an internal backend service
            try:
                backends_migration_handler = selfLink_executor.build_migration_handler()
            except UnsupportedBackendService:
                warnings.warn(
                    'The load balancing scheme of (%s) is not supported. '
                    'Continue migrating other backends.' % (backends_selfLink))
                continue
            if backends_migration_handler != None:
                self.backends_migration_handlers.append(
                    backends_migration_handler)
                if isinstance(backends_migration_handler,
                              BackendServiceMigration):
                    backend_service = backends_migration_handler.backend_service
                    if backend_service != None and backend_service.count_forwarding_rules() > 1:
                        print(
                            'The backend service is associated with two or more forwarding rules, \n'
                            'so it can not be migrated. \n'
                            'Terminating. ')
                        return
        self.migration_status = MigrationStatus(1)
        print('Deleting: %s.' % (self.forwarding_rule_name))
        self.forwarding_rule.delete_forwarding_rule()
        self.migration_status = MigrationStatus(2)

        print('Migrating the backends of %s.' %(self.forwarding_rule_name))
        for backends_migration_handler in self.backends_migration_handlers:
            backends_migration_handler.network_migration()
        self.migration_status = MigrationStatus(3)

        print('Recreating the forwarding rule (%s) in the target subnet.' % (
            self.forwarding_rule_name))
        self.forwarding_rule.insert_forwarding_rule(
            self.forwarding_rule.new_forwarding_rule_configs)
        self.migration_status = MigrationStatus(4)

    def rollback(self):
        """ Rollback an internal forwarding rule

        Returns:

        """
        if self.migration_status == 4:
            print('Deleting: %s.' %(self.forwarding_rule_name))
            self.forwarding_rule.delete_forwarding_rule()
            self.migration_status = MigrationStatus(3)

        if self.migration_status == 3:
            for backend_service_migration_handler in self.backends_migration_handlers:
                backend_service_migration_handler.rollback()
            self.migration_status = MigrationStatus(2)

        if self.migration_status == 2:
            self.forwarding_rule.insert_forwarding_rule(
                self.forwarding_rule.forwarding_rule_configs)
            self.migration_status = MigrationStatus(0)


class MigrationStatus(IntEnum):
    NOT_START = 0
    MIGRATING = 1
    ORIGINAL_FORWARDING_RULE_DELETED = 2
    BACKENDS_MIGRATED = 3
    NEW_FORWARDING_RULE_CREATED = 4