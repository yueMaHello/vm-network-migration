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

""" The script takes the arguments and run the forwarding rule migration handler.

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
     python3 forwarding_rule_migration.py --project_id=test-project
     --forwarding_rule_name=forwarding-rule-legacy --network=test-network
     --subnetwork=test-network --preserve_instance_external_ip=False
     --region=us-central1

"""
import warnings
import os
import argparse
import google.auth
from googleapiclient import discovery
from vm_network_migration.handlers.forwarding_rule_migration.forwarding_rule_migration import ForwardingRuleMigration

if __name__ == '__main__':
    if os.path.exists('./backup.log'):
        os.remove('./backup.log')
    # google credential setup
    credentials, default_project = google.auth.default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project_id',
                        help='The project ID of the forwarding rule.')

    parser.add_argument('--region', default=None,
                        help='The region of the forwarding rule.')
    parser.add_argument('--forwarding_rule_name',
                        help='The name of the forwarding rule.')
    parser.add_argument('--network', help='The name of the target network.')
    parser.add_argument(
        '--subnetwork',
        default=None,
        help='The name of target subnetwork. For auto mode networks,'
             ' this field is optional')
    parser.add_argument(
        '--preserve_instance_external_ip',
        default=False,
        help='Preserve the external IP addresses of the instances serving this forwarding rule')

    args = parser.parse_args()

    if args.preserve_instance_external_ip == 'True':
        args.preserve_instance_external_ip = True
    else:
        args.preserve_instance_external_ip = False

    if args.preserve_instance_external_ip:

        warnings.warn(
            'You choose to preserve the external IPs of the instances serving '
            'the target pool. If the instance is within an managed instance '
            'group, its external IP can not be preserved. For other instances with '
            'an ephemeral IP, its external IP will be reserved as a static '
            'external IP after the execution.',
            Warning)
        continue_execution = input(
            'Do you still want to preserve the external IP? y/n: ')
        if continue_execution == 'n':
            args.preserve_instance_external_ip = False

    forwarding_rule_migration = ForwardingRuleMigration(compute,
                                                        args.project_id,
                                                        args.forwarding_rule_name,
                                                        args.network,
                                                        args.subnetwork,
                                                        args.preserve_instance_external_ip,
                                                        args.region)
    forwarding_rule_migration.network_migration()
