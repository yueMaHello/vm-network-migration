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
""" Create a subclass instance of the ForwardingRuleMigration class

"""
from vm_network_migration.modules.external_regional_forwarding_rule import ExternalRegionalForwardingRule
from vm_network_migration.modules.forwarding_rule import ForwardingRule
from vm_network_migration.modules.global_forwarding_rule import GlobalForwardingRule
from vm_network_migration.modules.internal_regional_forwarding_rule import InternalRegionalForwardingRule
from vm_network_migration.errors import *


class ForwardingRuleHelper:
    def __init__(self, compute, project, forwarding_rule_name, network,
                 subnetwork,
                 region=None):
        """ Initialization

        Args:
            compute: Google Compute Engine
            project: Project ID
            forwarding_rule_name: name of the forwarding rule
            network: target network
            subnetwork: target subnet
            region: region of the forwarding rule. It is None for a global one
        """
        self.compute = compute
        self.project = project
        self.forwarding_rule_name = forwarding_rule_name
        self.network = network
        self.subnetwork = subnetwork
        self.region = region

    def build_a_forwarding_rule(self) -> ForwardingRule:
        """ Build a forwarding rule with a specific type according to the attributes

        Returns: a subclass object of ForwardingRule

        """
        if self.region == None:
            return self.build_a_global_forwarding_rule()

        else:
            load_balancing_schema = self.get_load_balancing_schema()
            if load_balancing_schema == 'EXTERNAL':
                return self.build_an_external_regional_forwarding_rule()
            elif load_balancing_schema == 'INTERNAL':
                return self.build_an_internal_regional_forwarding_rule()
            else:

                raise UnsupportedForwardingRule(
                    'Unsupported type of the forwarding rule. It can not be '
                    'migrated. Terminating.')

    def build_a_global_forwarding_rule(self) -> GlobalForwardingRule:
        """ Build a global forwarding rule

        Returns: a GlobalForwardingRule object

        """
        return GlobalForwardingRule(self.compute, self.project,
                                    self.forwarding_rule_name, self.network,
                                    self.subnetwork)

    def build_an_external_regional_forwarding_rule(
            self) -> ExternalRegionalForwardingRule:
        """ Build an external regional forwarding rule

        Returns: an ExternalRegionalForwardingRule object

        """
        return ExternalRegionalForwardingRule(self.compute, self.project,
                                              self.forwarding_rule_name,
                                              self.network,
                                              self.subnetwork, self.region)

    def build_an_internal_regional_forwarding_rule(
            self) -> InternalRegionalForwardingRule:
        """ Build an internal regional forwarding rule object

        Returns: an InternalRegionalForwardingRule object

        """
        return InternalRegionalForwardingRule(self.compute, self.project,
                                              self.forwarding_rule_name,
                                              self.network,
                                              self.subnetwork, self.region)

    def get_regional_forwarding_rule_configs(self):
        """ Get the configs of the forwarding rule

        Returns: configs

        """
        return self.compute.forwardingRules().get(
            project=self.project,
            region=self.region,
            forwardingRule=self.forwarding_rule_name).execute()

    def get_load_balancing_schema(self) -> str:
        """ Decide the load balancing schema is External/Internal

        Returns: 'External' or 'Internal'

        """
        configs = self.get_regional_forwarding_rule_configs()
        return configs['loadBalancingScheme']