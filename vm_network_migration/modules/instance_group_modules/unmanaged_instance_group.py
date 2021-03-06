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
"""
UnmanagedInstanceGroup: describes an unmanaged instance group
"""
import warnings
from copy import deepcopy

from googleapiclient.errors import HttpError
from vm_network_migration.errors import *
from vm_network_migration.module_helpers.subnet_network_helper import SubnetNetworkHelper
from vm_network_migration.modules.instance_group_modules.instance_group import InstanceGroup
from vm_network_migration.modules.other_modules.subnet_network import SubnetNetwork
from vm_network_migration.modules.other_modules.operations import Operations
from vm_network_migration.utils import is_equal_or_contians


class UnmanagedInstanceGroup(InstanceGroup):
    def __init__(self, compute, project, instance_group_name, network_name,
                 subnetwork_name, preserve_instance_ip, zone):
        """ Initialize an unmanaged instance group object

        Args:
            compute: google compute engine
            project: project name
            network_name: target network
            subnetwork_name: target subnet
            instance_group_name: instance group's name
            preserve_instance_ip: whether to preserve instances external IPs
            zone: zone name of the instance group
        """
        super(UnmanagedInstanceGroup, self).__init__(compute, project,
                                                     instance_group_name,
                                                     network_name,
                                                     subnetwork_name,
                                                     preserve_instance_ip)
        self.zone = zone
        self.instance_selfLinks = self.list_instances()
        self.network = self.get_network()
        self.original_instance_group_configs = self.get_instance_group_configs()
        self.new_instance_group_configs = self.get_new_instance_group_configs_using_new_network(
            self.original_instance_group_configs)
        self.operation = Operations(self.compute, self.project, self.zone, None)
        self.selfLink = self.get_selfLink(self.original_instance_group_configs)
        self.log()

    def get_network(self) -> SubnetNetwork:
        """ Get a SubnetNetwork object

        Returns:

        """
        print('Checking the target network information.')
        subnetwork_factory = SubnetNetworkHelper(self.compute, self.project,
                                                 self.zone)
        network = subnetwork_factory.generate_network(
            self.network_name,
            self.subnetwork_name)
        return network

    def get_instance_group_configs(self) -> dict:
        """ Get instance group's configurations

        Returns: instance group's configurations

        """
        return self.compute.instanceGroups().get(project=self.project,
                                                 zone=self.zone,
                                                 instanceGroup=self.instance_group_name).execute()

    def list_instances(self) -> list:
        """Retrieve all the instances in this instance group,

        Returns: a list of the instances' selfLinks

        """
        instance_selfLinks = []
        request = self.compute.instanceGroups().listInstances(
            project=self.project, zone=self.zone,
            instanceGroup=self.instance_group_name)
        while request is not None:
            response = request.execute()
            # no instances in the instance group
            if 'items' not in response:
                break
            for instance_with_named_ports in response['items']:
                print(instance_with_named_ports)
                instance_selfLinks.append(
                    instance_with_named_ports['instance'])
            request = self.compute.instanceGroups().listInstances_next(
                previous_request=request, previous_response=response)
        return instance_selfLinks

    def delete_instance_group(self) -> dict:
        """ Delete the instance group

        Returns:  a deserialized object of the response

        """

        delete_instance_group_operation = self.compute.instanceGroups().delete(
            project=self.project,
            zone=self.zone,
            instanceGroup=self.instance_group_name).execute()
        self.operation.wait_for_zone_operation(
            delete_instance_group_operation['name'])
        return delete_instance_group_operation

    def create_instance_group(self, configs) -> dict:
        """ Create the instance group

        Returns: a deserialized object of the response

        """
        create_instance_group_operation = self.compute.instanceGroups().insert(
            project=self.project,
            zone=self.zone,
            body=configs).execute()
        self.operation.wait_for_zone_operation(
            create_instance_group_operation['name'])
        return create_instance_group_operation

    def add_an_instance(self, instance_selfLink):
        """ Add an instance into the instance group

        Args:
            instance_selflink: the instance's selfLink

        Returns: a deserialized object of the response
        Raises: HttpError

        """
        try:
            add_instance_operation = self.compute.instanceGroups().addInstances(
                project=self.project,
                zone=self.zone,
                instanceGroup=self.instance_group_name,
                body={
                    'instances': [{
                        'instance': instance_selfLink}]}).execute()
            self.operation.wait_for_zone_operation(
                add_instance_operation['name'])
            return add_instance_operation
        except HttpError as e:
            error_reason = e._get_reason()
            if 'already a member of' in error_reason:
                warnings.warn(error_reason, Warning)
            else:
                raise e

    def remove_an_instance(self, instance_selfLink):
        """ Remove an instance from the instance group

         Args:
             instance_selflink: the instance to be removed

         Returns: a deserialized object of the response
         Raises: HttpError

         """
        try:
            add_instance_operation = self.compute.instanceGroups().removeInstances(
                project=self.project,
                zone=self.zone,
                instanceGroup=self.instance_group_name,
                body={
                    'instances': [{
                        'instance': instance_selfLink}]}).execute()
            self.operation.wait_for_zone_operation(
                add_instance_operation['name'])
            return add_instance_operation
        except HttpError as e:
            error_reason = e._get_reason()
            if 'is not a member of' in error_reason:
                warnings.warn(error_reason, Warning)
            else:
                raise e

    def add_all_instances(self):
        """ Add all the instances in instances to the current instance group

        """
        for instance_selfLink in self.instance_selfLinks:
            try:
                self.add_an_instance(instance_selfLink)
            except HttpError:
                raise AddInstanceToInstanceGroupError(
                    'Failed to add all instances to the instance group.')

    def get_new_instance_group_configs_using_new_network(self,
                                                         instance_group_configs):
        """ Modify the instance group configs with self.network

        Args:
            instance_group_configs: configs of the instance group

        Returns:

        """
        new_instance_group_configs = deepcopy(instance_group_configs)
        new_instance_group_configs['network'] = self.network.network_link
        new_instance_group_configs['subnetwork'] = self.network.subnetwork_link
        return new_instance_group_configs

    def compare_original_network_and_target_network(self) -> bool:
        """ check if the original network is the
        same as the target subnet

        Returns: True/False
        """
        if 'subnetwork' not in self.original_instance_group_configs:
            return False
        elif is_equal_or_contians(
                self.original_instance_group_configs['subnetwork'],
                self.network.subnetwork_link):
            return True
        else:
            return False
