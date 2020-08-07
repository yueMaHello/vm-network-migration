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

""" This class is used to build a migration handler
according to the given resource's selfLink.

"""
import re

from vm_network_migration.utils import initializer


class SelfLinkExecutor:
    @initializer
    def __init__(self, compute, selfLink, network, subnetwork,
                 preserve_instance_external_ip=False):
        """ Initialization

        Args:
            selfLink: selfLink of the compute engine resource
            network: target network
            subnetwork: target subnet
            preserve_instance_external_ip: whether to preserve the external ip
            of the instances in this resource
        """
        self.project = self.extract_project()
        self.zone = self.extract_zone()
        self.region = self.extract_region()
        self.instance = self.extract_instance()
        self.instance_group = self.extract_instance_group()
        self.backend_service = self.extract_backend_service()
        self.target_pool = self.extract_target_pool()
        self.forwarding_rule = self.extract_forwarding_rule()
        self.target_instance = self.extract_target_instance()

    def extract_project(self) -> str:
        """ Extract project id

        Returns: project id

        """
        project_match = re.search(r'\/projects\/(.*)\/', self.selfLink) \
                        or re.search(r'^projects\/(.*)\/', self.selfLink)
        if project_match != None:
            return project_match[1].split('/')[0]

    def extract_zone(self) -> str:
        """ Extract zone

        Returns: zone name

        """
        zone_match = re.search(r'\/zones\/(.*)\/', self.selfLink)
        if zone_match != None:
            return zone_match[1].split('/')[0]

    def extract_region(self) -> str:
        """ Extract region

        Returns: region name

        """
        region_match = re.search(r'\/regions\/(.*)\/',
                                 self.selfLink)
        if region_match != None:
            return region_match[1].split('/')[0]

    def extract_instance(self) -> str:
        """ Extract instance

        Returns: instance name

        """
        instance_match = re.search(r'\/instances\/(.*)',
                                   self.selfLink)

        if instance_match != None:
            return instance_match[1]

    def extract_instance_group(self) -> str:
        """ Extract instance group name

        Returns: instance group name

        """
        instance_group_match = re.search(r'\/instanceGroups\/(.*)',
                                         self.selfLink)
        if instance_group_match != None:
            return instance_group_match[1]
        instance_group_manager_match = re.search(
            r'\/instanceGroupManagers\/(.*)', self.selfLink)
        if instance_group_manager_match != None:
            return instance_group_manager_match[1]

    def extract_backend_service(self) -> str:
        """ Extract backend service name from the selfLink

        Returns: name of the backend service

        """
        backend_service_match = re.search(r'\/backendServices\/(.*)',
                                          self.selfLink)
        if backend_service_match != None:
            return backend_service_match[1]

    def extract_target_pool(self) -> str:
        """ Extract target pool name from the selfLink

        Returns: name of the target pool

        """

        target_pool_match = re.search(r'\/targetPools\/(.*)',
                                      self.selfLink)
        if target_pool_match != None:
            return target_pool_match[1]

    def extract_forwarding_rule(self) -> str:
        """ Extract the forwarding rule name from the selfLink

        Returns: name of the forwarding rule

        """
        forwarding_rule_match = re.search(r'\/forwardingRules\/(.*)',
                                          self.selfLink)
        if forwarding_rule_match != None:
            return forwarding_rule_match[1]

    def extract_target_instance(self) -> str:
        """ Extract target instance name from the selfLink

          Returns: name of the target pool

          """

        target_instance_match = re.search(r'\/targetInstances\/(.*)',
                                          self.selfLink)
        if target_instance_match != None:
            return target_instance_match[1]

    def is_a_supported_resource(self) -> bool:
        """ Check if the selfLink is a supported GCE resource

        Returns: True/False

        """
        if self.instance != None \
                or self.instance_group != None \
                or self.backend_service != None \
                or self.target_pool != None \
                or self.forwarding_rule != None \
                or self.target_instance != None:
            return True
        return False

    def build_migration_handler(self) -> object:
        """ Build a migration handler

        Returns: a migration handler

        """
        if self.instance != None:
            return self.build_instance_migration_handler()
        elif self.instance_group != None:
            return self.build_instance_group_migration_handler()
        elif self.backend_service != None:
            return self.build_backend_service_migration_handler()
        elif self.target_pool != None:
            return self.build_target_pool_migration_handler()
        elif self.forwarding_rule != None:
            return self.build_forwarding_rule_migration_handler()
        elif self.target_instance != None:
            return self.build_target_instance_migration_handler()
        else:
            return None

    def build_instance_group_migration_handler(self):
        """ Build an instance group migration handler

        Returns: InstanceGroupNetworkMigration

        """
        from vm_network_migration.handlers.instance_group_migration.instance_group_network_migration import InstanceGroupNetworkMigration
        if self.instance_group != None:
            instance_group_migration_handler = InstanceGroupNetworkMigration(
                self.compute,
                self.project,
                self.network,
                self.subnetwork,
                self.preserve_instance_external_ip,
                self.zone,
                self.region,
                self.instance_group)
            return instance_group_migration_handler

    def build_instance_migration_handler(self):
        """ Build an instance migration handler

        Returns: InstanceNetworkMigration

        """
        from vm_network_migration.handlers.instance_migration.instance_network_migration import InstanceNetworkMigration

        if self.instance != None:
            instance_migration_handler = InstanceNetworkMigration(self.compute,
                                                                  self.project,
                                                                  self.zone,
                                                                  self.instance,
                                                                  self.network,
                                                                  self.subnetwork,
                                                                  self.preserve_instance_external_ip
                                                                  )
            return instance_migration_handler

    def build_backend_service_migration_handler(self):
        """ Build a backend service migration handler

        Returns: BackendServiceMigration

        """
        from vm_network_migration.handlers.backend_service_migration.backend_service_migration import BackendServiceMigration
        if self.backend_service != None:
            backend_service_migration_handler = BackendServiceMigration(
                self.compute,
                self.project,
                self.backend_service,
                self.network,
                self.subnetwork,
                self.preserve_instance_external_ip,
                self.region
            )
            return backend_service_migration_handler

    def build_forwarding_rule_migration_handler(self):
        """ Build a forwarding rule migration handler

        Returns: ForwardingRuleMigration

        """
        from vm_network_migration.handlers.forwarding_rule_migration.forwarding_rule_migration import ForwardingRuleMigration
        if self.forwarding_rule != None:
            forwarding_rule_migration_handler = ForwardingRuleMigration(
                self.compute,
                self.project, self.forwarding_rule,
                self.network, self.subnetwork,
                self.preserve_instance_external_ip, self.region)
            return forwarding_rule_migration_handler

    def build_an_instance(self):
        """ Build an Instance object from the selfLink
        Args:
            compute: google compute engine
        Returns: an Instance object
        """
        from vm_network_migration.modules.instance_modules.instance import Instance
        if self.instance != None:
            instance = Instance(self.compute, self.project, self.instance,
                                self.region, self.zone, self.network,
                                self.subnetwork,
                                self.preserve_instance_external_ip)
            return instance

    def build_an_instance_group(self):
        """ Build an InstanceGroup object from the selfLink
        Args:
            compute: google compute engine
        Returns: an InstanceGroup object
        """
        from vm_network_migration.module_helpers.instance_group_helper import InstanceGroupHelper
        if self.instance_group != None:
            instance_group_helper = InstanceGroupHelper(self.compute,
                                                        self.project,
                                                        self.instance_group,
                                                        self.region,
                                                        self.zone, self.network,
                                                        self.subnetwork,
                                                        self.preserve_instance_external_ip)
            instance_group = instance_group_helper.build_instance_group()
            return instance_group

    def build_target_instance_migration_handler(self):
        """ Build a target instance migration handler

        Returns: TargetInstanceMigration

        """
        from vm_network_migration.handlers.instance_migration.target_instance_migration import TargetInstanceMigration
        if self.target_instance != None:
            target_instance_handler = TargetInstanceMigration(self.compute,
                                                              self.project,
                                                              self.target_instance,
                                                              self.network,
                                                              self.subnetwork,
                                                              self.preserve_instance_external_ip,
                                                              self.zone)

            return target_instance_handler

    def build_target_pool_migration_handler(self):
        """Build a target pool migration handler

        Returns: TargetPoolMigration

        """
        from vm_network_migration.handlers.target_pool_migration.target_pool_migration import TargetPoolMigration
        if self.target_pool != None:
            target_pool_migration_handler = TargetPoolMigration(self.compute,
                                                                self.project,
                                                                self.target_pool,
                                                                self.network,
                                                                self.subnetwork,
                                                                self.preserve_instance_external_ip,
                                                                self.region
                                                                )
            return target_pool_migration_handler
