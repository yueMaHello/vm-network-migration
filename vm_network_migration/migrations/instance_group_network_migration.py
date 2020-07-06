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

""" This script is used to migrate a GCP instance from its legacy network to a
subnetwork mode network.

Ihe Google API python client module is imported to manage the GCP Compute Engine
 resources.

Before running:
    1. If not already done, enable the Compute Engine API
       and check the quota for your project at
       https://console.developers.google.com/apis/api/compute
    2. This sample uses Application Default Credentials for authentication.
       If not already done, install the gcloud CLI from
       https://cloud.google.com/sdk and run
       `gcloud beta auth application-default login`.
       For more information, see
       https://developers.google.com/identity/protocols/application-default-credentials
    3. Install the Python client library for Google APIs by running
       `pip install --upgrade google-api-python-client`

Run the script by terminal, for example:
     python3 vm_network_migration.py --project_id=test-project
     --zone=us-central1-a --original_instance_name=instance-legacy
     --network=tests-network
     --subnetwork=tests-network --preserve_internal_ip=False
     --preserve_external_ip = False --preserve_alias_ip_ranges=False

"""
import copy
import warnings

import google.auth
from googleapiclient import discovery

from vm_network_migration.modules.unmanaged_instance_group import UnmanagedInstanceGroup
from vm_network_migration.modules.single_zone_managed_instance_group import SingleZoneManagedInstanceGroup
from vm_network_migration.modules.region_managed_instance_group import RegionManagedInstanceGroup
from vm_network_migration.modules.instance_template import InstanceTemplate
from vm_network_migration.modules.subnet_network import SubnetNetworkFactory
from googleapiclient.http import HttpError
from vm_network_migration.modules.instance_group import InstanceGroupFactory, \
    InstanceGroupStatus
from vm_network_migration.migrations.instance_network_migration import InstanceNetworkMigration
from copy import deepcopy


class InstanceGroupNetworkMigration:
    def __init__(self, project, region, zone, instance_group_name):
        """ Initialize a InstanceNetworkMigration object

        Args:
            project: project ID
            zone: zone of the instance
        """
        self.compute = self.set_compute_engine()
        self.project = project
        self.zone = zone
        self.region = region
        self.instance_group_name = instance_group_name
        self.instance_group = self.build_instance_group()

    def build_instance_group(self):
        instance_group_factory = InstanceGroupFactory(self.compute,
                                                      self.project, self.region,
                                                      self.zone,
                                                      self.instance_group_name)
        instance_group = instance_group_factory.build_instance_group()
        return instance_group

    def set_compute_engine(self):
        """ Credential setup

        Returns:google compute engine

        """
        credentials, default_project = google.auth.default()
        return discovery.build('compute', 'v1', credentials=credentials)

    def network_migration(self,
                          network_name,
                          subnetwork_name, preserve_external_ip):
        """ The main method of the instance network migration process

        Args:
            network_name: target network name
            subnetwork_name: target subnetwork name
            preserve_external_ip: preserve the external IP of the instances
            in an unmanaged instance group

        Returns: None

        """
        if isinstance(self.instance_group, UnmanagedInstanceGroup):
            self.migrate_unmanaged_instance_group(network_name, subnetwork_name,
                                                  preserve_external_ip)
        elif isinstance(self.instance_group, SingleZoneManagedInstanceGroup):
            self.migrate_single_zone_managed_instance_group(network_name,
                                                            subnetwork_name)
        else:
            self.migrate_region_managed_instance_group(network_name,
                                                       subnetwork_name)

    def migrate_unmanaged_instance_group(self, network_name, subnetwork_name,
                                         preserve_external_ip):
        subnetwork_factory = SubnetNetworkFactory(self.compute, self.project,
                                                  self.zone, self.region)
        self.instance_group.network = subnetwork_factory.generate_network(
            network_name,
            subnetwork_name)
        instance_network_migration = InstanceNetworkMigration(self.project,
                                                              self.zone)
        print(
            "Migrating all the instances in the instance group to the new network.")
        for instance in self.instance_group.instances:
            instance_network_migration.instance = instance
            instance_network_migration.network_migration(None, network_name,
                                                         subnetwork_name,
                                                         preserve_external_ip)
        self.instance_group.update_new_instance_group_configs()
        print("Deleting the original instance group.")
        self.instance_group.delete_instance_group()
        print("Creating a new instance group in the new network.")
        self.instance_group.create_instance_group(
            self.instance_group.new_instance_group_configs)
        print("Adding the instances back to the new instance group")
        self.instance_group.add_all_instances()

    def migrate_single_zone_managed_instance_group(self, network_name,
                                                   subnetwork_name):
        subnetwork_factory = SubnetNetworkFactory(self.compute, self.project,
                                                  self.zone, self.region)
        subnet_network = subnetwork_factory.generate_network(
            network_name,
            subnetwork_name)
        instance_template_name = self.instance_group.retrieve_instance_template_name()
        original_instance_template = InstanceTemplate(self.compute,
                                                      self.project,
                                                      instance_template_name)
        new_instance_template = InstanceTemplate(self.compute, self.project,
                                                 instance_template_name,
                                                 deepcopy(
                                                     original_instance_template.instance_template_body))
        new_instance_template.modify_instance_template_with_new_network(
            subnet_network.network_link, subnet_network.subnetwork_link)
        new_instance_template.random_change_name()
        new_instance_template.insert()
        new_instance_template_link = new_instance_template.get_selfLink()
        self.instance_group.modify_instance_group_configs_with_instance_template(
            self.instance_group.new_instance_group_configs,
            new_instance_template_link)
        self.instance_group.create_instance_group(
            self.instance_group.new_instance_group_configs)

    def rollback_original_instance_group(self):
        """ Roll back to the original VM. Reattach the disks to the
        original instance and restart it.

            Raises:
                googleapiclient.errors.HttpError: invalid request
        """

    def rollback_unmanaged_instance_group(self):
        """ Rollback an unmanaged instance group

        Returns:

        """
        if self.instance_group.migrated:
            self.instance_group.delete_instance_group()
        # Some of its instances are running on the new network.
        # These instances should be moved back to the legacy network,
        # and should be added back to the instance group.
        for instance in self.instance_group.instances:
            if instance.migrated:
                instance.delete_instance()
                instance.create_instance(instance.original_instance_template)
        instance_group_status = self.instance_group.get_status()
        if instance_group_status == InstanceGroupStatus.NOTEXISTS:
            self.instance_group.create_instance_group(
                self.instance_group.original_instance_group_configs)
        self.instance_group.add_all_instances()