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
""" RegionalForwardingRule: it describes a regional forwarding rule and has
some google API interface functions.
"""
import warnings

from googleapiclient.http import HttpError
from vm_network_migration.modules.forwarding_rule_modules.forwarding_rule import ForwardingRule
from vm_network_migration.modules.other_modules.operations import Operations


class RegionalForwardingRule(ForwardingRule):
    def __init__(self, compute, project, forwarding_rule_name, network,
                 subnetwork, region):
        """ Initialization

        Args:
            compute: google compute engine
            project: project id
            forwarding_rule_name: the name of the forwarding rule
            network: target network
            subnetwork: target subnet
            preserve_instance_external_ip: whether to preserve the IPs of
                the instances serving the backend service
            region: region of the forwarding rule
        """
        super(RegionalForwardingRule, self).__init__(compute, project,
                                                     forwarding_rule_name,
                                                     network, subnetwork)
        self.region = region
        self.forwarding_rule_configs = self.get_forwarding_rule_configs()
        self.operations = Operations(self.compute, self.project, None,
                                     self.region)
        self.log()

    def get_forwarding_rule_configs(self):
        """ Get the configs of the forwarding rule

        Returns: configs

        """
        return self.compute.forwardingRules().get(
            project=self.project,
            region=self.region,
            forwardingRule=self.forwarding_rule_name).execute()

    def check_forwarding_rule_exists(self) -> bool:
        """ Check if the forwarding rule exists

        Returns: True or False

        """
        try:
            self.get_forwarding_rule_configs()
        except:
            return False
        else:
            return True

    def delete_forwarding_rule(self) -> dict:
        """ Delete the forwarding rule

             Returns: a deserialized python object of the response

        """
        delete_forwarding_rule_operation = self.compute.forwardingRules().delete(
            project=self.project,
            region=self.region,
            forwardingRule=self.forwarding_rule_name).execute()
        self.operations.wait_for_region_operation(
            delete_forwarding_rule_operation['name'])
        return delete_forwarding_rule_operation

    def insert_forwarding_rule(self, forwarding_rule_config):
        """ Insert the forwarding rule

             Returns: a deserialized python object of the response

        """
        try:
            insert_forwarding_rule_operation = self.compute.forwardingRules().insert(
                project=self.project,
                region=self.region,
                body=forwarding_rule_config).execute()
            self.operations.wait_for_region_operation(
                insert_forwarding_rule_operation['name'])


        except HttpError as e:
            error_reason = e._get_reason()
            if 'internal IP is outside' in error_reason:
                warnings.warn('The original IP address of the forwarding rule was an ' \
                    'ephemeral one. After the migration, a new IP address is ' \
                    'assigned to the forwarding rule.', Warning)
            else:
                warnings.warn(error_reason, Warning)
                # Set the IPAddress to ephemeral
            if 'IPAddress' in forwarding_rule_config:
                del forwarding_rule_config['IPAddress']
            insert_forwarding_rule_operation = self.compute.forwardingRules().insert(
                project=self.project,
                region=self.region,
                body=forwarding_rule_config).execute()
            self.operations.wait_for_region_operation(
                insert_forwarding_rule_operation['name'])

        return insert_forwarding_rule_operation
