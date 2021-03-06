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
""" Instance class: describe an instance
    InstanceStatus class: describe an instance's current status
"""
import logging
from copy import deepcopy
from enum import Enum

from googleapiclient.errors import HttpError
from vm_network_migration.errors import *
from vm_network_migration.module_helpers.address_helper import AddressHelper
from vm_network_migration.module_helpers.subnet_network_helper import SubnetNetworkHelper
from vm_network_migration.modules.other_modules.operations import Operations
from vm_network_migration.utils import (
    initializer,
    is_equal_or_contians,
)


class Instance(object):
    @initializer
    def __init__(self, compute, project, name, zone, network,
                 subnetwork, preserve_instance_ip=False,
                 instance_configs=None):
        """ Initialize an instance object

        Args:
            compute: google compute engine
            project: project ID
            name: name of the instance
            region: region of the instance
            zone: zone of the instance
            instance_configs: the instance config
        """

        self.original_instance_configs = instance_configs or self.retrieve_instance_configs()
        self.network_object = self.get_network()
        self.address_object = self.get_address()
        self.new_instance_configs = self.get_new_instance_configs()
        self.original_status = self.get_instance_status()
        self.operations = Operations(compute, project, zone)
        self.selfLink = self.get_selfLink(self.original_instance_configs)
        self.log()

    def log(self):
        logging.basicConfig(filename='backup.log', level=logging.INFO)
        logging.info('-------Instance: %s-----' % (self.name))
        logging.info(self.original_instance_configs)
        logging.info('--------------------------')

    def retrieve_instance_configs(self) -> dict:
        """ Get the instance config.

        Returns:
            config of the instance

        Raises:
            googleapiclient.errors.HttpError: invalid request
        """
        instance_configs = self.compute.instances().get(
            project=self.project,
            zone=self.zone,
            instance=self.name).execute()

        return instance_configs

    def get_address(self):
        """ Generate the address object

        Returns: Address object

        """
        if self.original_instance_configs == None:
            self.original_instance_configs = self.retrieve_instance_configs()
        address_factory = AddressHelper(self.compute, self.project,
                                        self.zone)
        address = address_factory.generate_address(
            self.original_instance_configs)
        return address

    def get_network(self):
        """ Generate the network object

        Returns: Network object

        """
        subnetwork_factory = SubnetNetworkHelper(self.compute, self.project,
                                                 self.zone)
        network = subnetwork_factory.generate_network(
            self.network,
            self.subnetwork)
        return network

    def get_selfLink(self, instance_configs) -> str:
        """ Get the instance selfLink from its configs

        Args:
            instance_configs: instance configurations

        Returns: string of a URL link

        """
        if 'selfLink' in instance_configs:
            return instance_configs['selfLink']

    def start_instance(self) -> dict:
        """ Start the instance.

        Returns:
            a deserialized object of the response

        Raises:
            googleapiclient.errors.HttpError: invalid request
        """
        start_instance_operation = self.compute.instances().start(
            project=self.project,
            zone=self.zone,
            instance=self.name).execute()
        self.operations.wait_for_zone_operation(
            start_instance_operation['name'])
        return start_instance_operation

    def stop_instance(self) -> dict:
        """ Stop the instance.

        Returns:
            a deserialized object of the response

        Raises:
            googleapiclient.errors.HttpError: invalid request
        """
        stop_instance_operation = self.compute.instances().stop(
            project=self.project,
            zone=self.zone,
            instance=self.name).execute()
        self.operations.wait_for_zone_operation(stop_instance_operation['name'])
        return stop_instance_operation

    def get_disks_info_from_instance_configs(self) -> list:
        """ Get disks' info from the instance config.

        Returns:
            a list of disks' info

        Raises:
            AttributeNotExistError: No disks on the VM
        """
        if 'disks' not in self.original_instance_configs:
            raise AttributeNotExistError('No disks are attached on the VM')
        return self.original_instance_configs['disks']

    def detach_disk(self, disk) -> dict:
        """ Detach a disk from the instance

        Args:
            disk: name of the disk

        Returns:
            a deserialized object of the response

        Raises:
            googleapiclient.errors.HttpError: invalid request
        """

        detach_disk_operation = self.compute.instances().detachDisk(
            project=self.project,
            zone=self.zone,
            instance=self.name,
            deviceName=disk).execute()
        self.operations.wait_for_zone_operation(detach_disk_operation['name'])
        return detach_disk_operation

    def detach_disks(self):
        """ Detach all the disks retrieved from self.instance_configs

        Returns: None

        """
        disks = self.get_disks_info_from_instance_configs()
        for diskInfo in disks:
            self.detach_disk(diskInfo['deviceName'])

    def attach_disk(self, diskInfo):
        """Attach a disk to the instance

        Args:
            disk: deserialized info of the disk

        Returns:
            a deserialized object of the response

        Raises:
            googleapiclient.errors.HttpError: invalid request
        """
        attach_disk_operation = self.compute.instances().attachDisk(
            project=self.project,
            zone=self.zone,
            instance=self.name,
            forceAttach=True,
            body=diskInfo).execute()
        self.operations.wait_for_zone_operation(attach_disk_operation['name'])
        return attach_disk_operation

    def attach_disks(self):
        """ Attach all the disks retrieved from self.instance_configs

        Returns: None
        """
        disks = self.get_disks_info_from_instance_configs()
        for diskInfo in disks:
            self.attach_disk(diskInfo)

    def modify_instance_configs_with_new_network(self, new_network_link,
                                                 new_subnetwork_link,
                                                 instance_configs,
                                                 add_network_metadata=True):
        """ Modify the instance config with the new network links

            Args:
                new_network_link: the selflink of the network
                new_subnetwork_link: the selflink of the subnetwork

            Returns:
                modified instance config
        """
        instance_configs['networkInterfaces'][0][
            'network'] = new_network_link
        instance_configs['networkInterfaces'][0][
            'subnetwork'] = new_subnetwork_link
        # For testing
        # if add_network_metadata:
        #     if 'items' not in instance_configs['metadata']:
        #         instance_configs['metadata']['items'] = []
        #
        #     for item in instance_configs['metadata']['items']:
        #         if item['key'] == 'network':
        #             item['value'] = new_subnetwork_link
        #             return
        #
        #     instance_configs['metadata']['items'].append({
        #         'key': 'network',
        #         'value': new_subnetwork_link})

    def modify_instance_configs_with_external_ip(self, external_ip,
                                                 instance_configs):
        """ Modify the instance config with the given external IP address

        Args:
            external_ip: external IP address, such as "123.213.213.123"

        Returns: modified instance config

        """
        if external_ip == None:
            if 'accessConfigs' in instance_configs['networkInterfaces'][
                0]:
                if 'natIP' in instance_configs['networkInterfaces'][0][
                    'accessConfigs'][0]:
                    del \
                        instance_configs['networkInterfaces'][0][
                            'accessConfigs'][
                            0]['natIP']

        else:
            if 'accessConfigs' not in \
                    instance_configs['networkInterfaces'][0]:
                instance_configs['networkInterfaces'][0][
                    'accessConfigs'] = [{}]
            instance_configs['networkInterfaces'][0]['accessConfigs'][0][
                'natIP'] = external_ip

        if 'networkIP' in instance_configs['networkInterfaces'][0]:
            del instance_configs['networkInterfaces'][0]['networkIP']

    def get_new_instance_configs(self):
        """ Update the instance config with current attributes

        Returns: None

        """
        new_instance_configs = deepcopy(self.original_instance_configs)
        if self.address_object == None or self.network == None:
            raise AttributeNotExistError('Missing address or network object.')
        if not self.preserve_instance_ip:
            self.modify_instance_configs_with_external_ip(
                None, new_instance_configs)
        else:
            self.modify_instance_configs_with_external_ip(
                self.address_object.external_ip, new_instance_configs)
        self.modify_instance_configs_with_new_network(
            self.network_object.network_link,
            self.network_object.subnetwork_link,
            new_instance_configs)
        return new_instance_configs

    def create_instance(self, instance_configs) -> dict:
        """ Create the instance using self.instance_configs

            Returns:
                a deserialized object of the response

            Raises:
                googleapiclient.errors.HttpError: invalid request
        """
        create_instance_operation = self.compute.instances().insert(
            project=self.project,
            zone=self.zone,
            body=instance_configs).execute()
        self.operations.wait_for_zone_operation(
            create_instance_operation['name'])
        return create_instance_operation

    def delete_instance(self) -> dict:
        """ Delete the instance

            Returns:
                a deserialized object of the response

            Raises:
                googleapiclient.errors.HttpError: invalid request
        """
        delete_instance_operation = self.compute.instances().delete(
            project=self.project,
            zone=self.zone,
            instance=self.name).execute()
        self.operations.wait_for_zone_operation(
            delete_instance_operation['name'])
        return delete_instance_operation

    def get_instance_status(self):
        """ Get current instance's status.

        Returns: an InstanceStatus object
        Raises: HttpError for incorrect response
        """
        try:
            instance_configs = self.retrieve_instance_configs()
        except HttpError as e:
            error_reason = e._get_reason()
            print(error_reason)
            # if instance is not found, it has a NOTEXISTS status
            if 'not found' in error_reason:
                return InstanceStatus.NOTEXISTS
            else:
                raise e
        return InstanceStatus(instance_configs['status'])

    def create_instance_with_ephemeral_external_ip(self, configs) -> dict:
        """ Create instance using configs, but without static external IP.

        Args:
            configs: configs of the instance

        """
        cur_configs = deepcopy(configs)
        self.modify_instance_configs_with_external_ip(None, cur_configs)
        print('Modified VM configuration:', cur_configs)
        return self.create_instance(cur_configs)

    def get_referrer_selfLinks(self) -> list:
        """ Get all this instance's referrer's selfLinks

        Returns:a list of instance group selfLinks

        """
        referrer_selfLinks = []
        request = self.compute.instances().listReferrers(
            project=self.project,
            zone=self.zone,
            instance=self.name)
        while request is not None:
            response = request.execute()
            if 'items' not in response:
                break

            for reference in response['items']:
                if 'MEMBER_OF' in reference['referenceType']:
                    referrer_selfLinks.append(reference['referrer'])

            request = self.compute.instances().listReferrers_next(
                previous_request=request, previous_response=response)
        return referrer_selfLinks

    def compare_original_network_and_target_network(self):
        """ Check if the original network is the
        same as the target subnet

        Returns: True for the same
        """
        if self.network_object == None or self.network_object.subnetwork_link == None:
            raise InvalidTargetNetworkError

        if 'subnetwork' not in \
                self.original_instance_configs['networkInterfaces'][0]:
            return False
        elif is_equal_or_contians(
                self.original_instance_configs['networkInterfaces'][0][
                    'subnetwork'],
                self.network_object.subnetwork_link):
            return True
        else:
            return False


class InstanceStatus(Enum):
    """
    An Enum class for instance's status
    """
    NOTEXISTS = None
    RUNNING = 'RUNNING'
    STOPPING = 'STOPPING'
    TERMINATED = 'TERMINATED'

    def __eq__(self, other):
        """ Override __eq__ function
        Args:
            other: another InstanceStatus object
        Returns: True/False
        """
        return self.value == other.value
