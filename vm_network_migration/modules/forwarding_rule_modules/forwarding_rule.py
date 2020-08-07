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
"""  ForwardingRule class: describes a forwarding rule

"""
import logging
from vm_network_migration.errors import *
from vm_network_migration.utils import *
from vm_network_migration.handler_helper.selfLink_executor import SelfLinkExecutor


class ForwardingRule(object):
    @initializer
    def __init__(self, compute, project, forwarding_rule_name, network,
                 subnetwork):
        """ Initialization

        Args:
            compute: Google Compute Engine
            project: Project ID
            forwarding_rule_name: name of the forwarding rule
            network: target network
            subnetwork: target subnet

        """
        self.forwarding_rule_configs = None
        self.operations = None
        self.backends_selfLinks = None

    def log(self):
        """ Log the configuration

        Returns:

        """
        logging.basicConfig(filename='backup.log', level=logging.INFO)
        logging.info(
            '-------Forwarding Rule: %s-----' % (self.forwarding_rule_name))
        logging.info(self.forwarding_rule_configs)
        logging.info('--------------------------')

    def get_forwarding_rule_configs(self):
        """ Get the configs of a forwarding rule

        Returns:

        """
        pass

    def check_forwarding_rule_exists(self):
        """ Check if the forwarding rule exists

        Returns:

        """
        pass

    def get_target_proxy_type(self) -> str:
        """ Get the type of the target proxy

        Returns: type of the target proxy

        """
        if 'target' in self.forwarding_rule_configs:
            return self.forwarding_rule_configs['target'].split('/')[-2]

    def get_target_proxy_name(self) -> str:
        """ Get the name of the target proxy

        Returns: name of the target proxy

        """
        if 'target' in self.forwarding_rule_configs:
            return self.forwarding_rule_configs['target'].split('/')[-1]

    def get_target_proxy_configs(self, target_proxy_type, target_proxy_name,
                                 region=None):
        """ Get the target proxy configs

        Args:
            target_proxy_type: type of the target proxy
            target_proxy_name: name of the target proxy

        Returns:

        """
        proxy_type_to_compute_api = {
            'targetHttpProxies': self.compute.targetHttpProxies(),
            'targetHttpsProxies': self.compute.targetHttpsProxies(),
            'targetTcpProxies': self.compute.targetTcpProxies(),
            'targetSslProxies': self.compute.targetSslProxies()
        }
        regional_proxy_type_to_compute_api = {
            'targetHttpProxies': self.compute.regionTargetHttpProxies(),
            'targetHttpsProxies': self.compute.regionTargetHttpsProxies(),
        }
        proxy_type_to_proxy_keyword = {
            'targetHttpProxies': 'targetHttpProxy',
            'targetHttpsProxies': 'targetHttpsProxy',
            'targetTcpProxies': 'targetTcpProxy',
            'targetSslProxies': 'targetSslProxy'
        }

        if target_proxy_type in proxy_type_to_compute_api:
            if region == None:
                compute_engine_api = proxy_type_to_compute_api[
                    target_proxy_type]
            else:
                compute_engine_api = regional_proxy_type_to_compute_api[
                    target_proxy_type]

        else:
            raise TargetTypeError(
                'The forwarding rule\'s target proxy type is not supported.')
        args = {
            'project': self.project,
            proxy_type_to_proxy_keyword[
                target_proxy_type]: target_proxy_name
        }
        if region != None:
            args['region'] = region

        return compute_engine_api.get(**args).execute()

    def get_backend_service_selfLinks_from_target_proxy_configs(self,
                                                                target_proxy_configs) -> list:
        """ Get all the backend services which are serving the forwarding rule

        Returns: a list pf backend service selfLink

        """
        if 'service' in target_proxy_configs:
            return [target_proxy_configs['service']]
        elif 'urlMap' in target_proxy_configs:
            backend_services_selfLinks = set()
            url_selfLink = target_proxy_configs['urlMap']
            self_link_executor = SelfLinkExecutor(self.compute, url_selfLink,
                                                  self.network, self.subnetwork)
            urlMap_name = target_proxy_configs['urlMap'].split('/')[-1]
            if self_link_executor.region == None:
                urlMap_configs = self.compute.urlMaps().get(
                    project=self.project,
                    urlMap=urlMap_name).execute()
            else:
                urlMap_configs = self.compute.regionUrlMaps().get(
                    project=self.project,
                    urlMap=urlMap_name,
                    region=self_link_executor.region).execute()
            find_all_matching_strings_from_a_dict(urlMap_configs,
                                                  "compute/v1/projects/",
                                                  backend_services_selfLinks)
            return list(backend_services_selfLinks)
        return []

    def get_backends_selfLinks(self) -> list:
        """ Get all backends of this forwarding rule. The backends list can
        contain backend service, or a target pool, or a target instance

        Returns: a list of GCE resource selfLinks

        """
        backends_selfLinks = []
        if self.forwarding_rule_configs != None and 'target' in self.forwarding_rule_configs:
            target_selfLink = self.forwarding_rule_configs['target']
            print(target_selfLink)
            self_link_executor = SelfLinkExecutor(self.compute, target_selfLink,
                                                  self.network, self.subnetwork)
            # it can be a target instance, target pool or a backend service
            if self_link_executor.is_a_supported_resource():
                backends_selfLinks.append(target_selfLink)
            # it is a target proxy
            else:
                target_proxy_type = self.get_target_proxy_type()
                target_proxy_name = self.get_target_proxy_name()
                target_proxy_configs = self.get_target_proxy_configs(
                    target_proxy_type, target_proxy_name,
                    self_link_executor.region)
                backends_selfLinks.extend(self.get_backend_service_selfLinks_from_target_proxy_configs(
                    target_proxy_configs))
        if 'backendService' in self.forwarding_rule_configs:
            backends_selfLinks.append(self.forwarding_rule_configs['backendService'])
        return list(set(backends_selfLinks))

    def compare_original_network_and_target_network(self):
        return False