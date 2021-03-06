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
""" SubnetNetwork class: describes a subnetwork and its relate API calls.

"""
from vm_network_migration.errors import *
from vm_network_migration.utils import initializer


class SubnetNetwork(object):
    @initializer
    def __init__(self, compute, project, zone, region, network,
                 subnetwork=None, only_check_network_info=False):
        """ Initialize a SubnetNetwork object.
            If the network is auto, then the subnetwork name is optional;
            otherwise, it should be specified
        Args:
            compute: google compute engine
            project: project ID
            zone: zone name
            region: region name
            network: network name
            subnetwork: subnetwork name
            only_check_network_info: True means ignoring the subnetwork info
        """

        self.network_link = None
        self.subnetwork_link = None

    def subnetwork_validation(self):
        """ Check if the current subnetwork is a potential valid subnetwork

        Raises:
            MissingSubnetworkError: The subnetwork is not specified and
            the network is in a custom mode.
        """
        if self.only_check_network_info:
            pass
        if self.subnetwork != None:
            pass
        automode_status = self.check_network_auto_mode()
        if self.subnetwork is None:
            if not automode_status:
                raise MissingSubnetworkError('No specified subnetwork')
            else:
                # the network is in auto mode, the default subnetwork name is the
                # same as the network name
                self.subnetwork = self.network

    def get_network(self) -> dict:
        """ Get the network config.

            Returns:
                a deserialized object of the network information

            Raises:
                googleapiclient.errors.HttpError: invalid request
        """
        return self.compute.networks().get(
            project=self.project,
            network=self.network).execute()

    def generate_new_network_info(self):
        """ Generate self.network_link and self.subnetwork_link

        Returns:

        """
        network_parameters = self.get_network()
        self.network_link = network_parameters['selfLink']
        if self.only_check_network_info:
            return
        subnetwork_link = 'regions/' + self.region + '/subnetworks/' + self.subnetwork
        if 'subnetworks' not in network_parameters:
            self.subnetwork_link = None
            raise SubnetworkNotExists(
                'No subnetwork was found in the target network.')
        for subnetwork in network_parameters['subnetworks']:
            if subnetwork_link in subnetwork:
                self.subnetwork_link = subnetwork_link
                return

        raise SubnetworkNotExists('Invalid target subnetwork.')

    def check_network_auto_mode(self) -> bool:
        """ Check if the network is in auto mode

        Returns:
            True for automode network

        Raises:
            InvalidTargetNetworkError: if the network is not a subnetwork mode network
        """
        network_info = self.get_network()
        if 'autoCreateSubnetworks' not in network_info:
            raise InvalidTargetNetworkError(
                'The target network is not a subnetwork mode network')
        auto_mode_status = network_info['autoCreateSubnetworks']
        return auto_mode_status
