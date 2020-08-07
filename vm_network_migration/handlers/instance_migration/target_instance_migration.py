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
""" TargetPoolMigration class: Handle the migration of a target pool.

"""

from vm_network_migration.utils import initializer
from vm_network_migration.handlers.compute_engine_resource_migration import ComputeEngineResourceMigration
from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor


class TargetInstanceMigration(ComputeEngineResourceMigration):
    @initializer
    def __init__(self, compute, project, target_instance_name, network,
                 subnetwork,preserve_instance_external_ip, zone):
        """ Initialize a BackendServiceMigration object

        Args:
            project: project ID
            target_instance_name: name of the target instance
            network: target network
            subnetwork: target subnet
            preserve_instance_external_ip: whether preserve the external IP
            zone: zone of the target instance
        """
        super(TargetInstanceMigration, self).__init__()

        self.instance_network_migration = self.create_instance_migration_handler()

    def get_instance_selfLink(self):
        return self.compute.targetInstances().get(
            project=self.project,
            zone=self.zone,
            targetInstance=self.target_instance_name).execute()['instance']

    def create_instance_migration_handler(self, instance_selfLink=None):
        if instance_selfLink == None:
            instance_selfLink = self.get_instance_selfLink()
        selfLink_executor = SelfLinkExecutor(self.compute, instance_selfLink,
                                             self.network, self.subnetwork,
                                             self.preserve_instance_external_ip)
        try:
            return selfLink_executor.build_instance_migration_handler()
        except:
            return None

    def network_migration(self):
        """ Migrate the backends of the target pool one by one from a legacy
            network to the target subnet.

        """
        print('Migrating the target instance: %s' %(self.target_instance_name))
        if self.instance_network_migration == None:
            print('The target instance is linking to a non-existing instance.')
            return
        self.instance_network_migration.network_migration()
