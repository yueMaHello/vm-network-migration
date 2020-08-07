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
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.module_helpers.forwarding_rule_helper import ForwardingRuleHelper
from vm_network_migration.modules.forwarding_rule_modules.external_regional_forwarding_rule import ExternalRegionalForwardingRule
from vm_network_migration.modules.forwarding_rule_modules.external_global_forwarding_rule import ExternalGlobalForwardingRule
from vm_network_migration.modules.forwarding_rule_modules.internal_regional_forwarding_rule import InternalRegionalForwardingRule
from vm_network_migration.utils import initializer
from vm_network_migration.handlers.forwarding_rule_migration.external_forwarding_rule_migration import ExternalForwardingRuleMigration
from vm_network_migration.handlers.forwarding_rule_migration.internal_forwarding_rule_migration import InternalForwardingRuleMigration


class ForwardingRuleMigration(ComputeEngineResourceMigration):
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
        super(ForwardingRuleMigration, self).__init__()
        self.forwarding_rule = self.build_forwarding_rule()
        self.forwarding_rule_migration_handler = self.build_forwarding_rule_migration_handler()

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

    def build_forwarding_rule_migration_handler(self):
        """ Build forwarding rule migration handler based on its forwarding rule type

        Returns:

        """
        if isinstance(self.forwarding_rule,
                      InternalRegionalForwardingRule):
            self.forwarding_rule_migration_handler = InternalForwardingRuleMigration(
                self.compute, self.project, self.forwarding_rule_name,
                self.network_name, self.subnetwork_name,
                self.preserve_instance_external_ip, self.region)

        elif isinstance(self.forwarding_rule, ExternalGlobalForwardingRule) \
                or isinstance(self.forwarding_rule,
                              ExternalRegionalForwardingRule):
            self.forwarding_rule_migration_handler = ExternalForwardingRuleMigration(
                self.compute, self.project, self.forwarding_rule_name,
                self.network_name, self.subnetwork_name,
                self.preserve_instance_external_ip, self.region)
        else:
            raise UnsupportedForwardingRule

        return self.forwarding_rule_migration_handler

    def network_migration(self):
        """ Select correct network migration functions based on the type of the
        forwarding rule.

        Returns:

        """
        print('Migrating the forwarding rule: %s' % (self.forwarding_rule_name))
        if self.forwarding_rule.compare_original_network_and_target_network():
            print('The backend service %s is already using target subnet.' % (
                self.forwarding_rule_name))
            return

        if self.forwarding_rule_migration_handler == None:
            warnings.warn('Unable to fetch the forwarding rule resource.')
            return
        try:
            self.forwarding_rule_migration_handler.network_migration()
        except Exception as e:
            warnings.warn(e, Warning)
            self.rollback()
            raise MigrationFailed('Rollback finished.')

    def rollback(self):
        """ Error happens. Rollback to the original status.

        """
        warnings.warn('Rolling back: %s.' % (self.forwarding_rule_name),
                      Warning)

        self.forwarding_rule_migration_handler.rollback()
        print('Rollback finished.')
