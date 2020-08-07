# VM Network Migration
**This is not an officially supported Google product.**
## Description

This Python library is used to migrate GCE resources from its legacy network to a
subnetwork with downtime. The project uses Google APIs Python client library (Compute Engine APIs) to manage the 
Compute Engine resources. 

## Supported GCE Resrouces:
    1. VM instance (with IP preservation)
    2. Instance group
        (1)Unmanaged  (with IP preservation)
        (2)Managed 
    3. Target pool
    4. Backend service
        (1)Internal
        (2)External
        (3)Internal-self-managed
    5. Forwarding rule 
        (1)Internal 
        (2)External (with IP preservation)
        (3)Internal-managed 


## Requirements:
1. Support migration from a legacy network to a subnetwork, or from one VPC network to another VPC network. Migration from any network to a legacy network is not allowed.
2. After the migration, only the network configuration will change, and all other configurations including project, zone and region will remain unchanged.
3. For a VM, which is not in a managed instance group, after the migration, its external IP can remain unchanged.
4. Rollback mechanism is needed to protect the failure
5. The users need to take care of the firewalls by themselves. 

## Limitations
### General Limitations:
1. The users should not change any GCE resources during the migration. Otherwise, there might be some errors, such as resources can not be found or out of quota issues. 
2. Downtime is required.
3. The rollback can also fail due to network issue or quota limitation issue. In this scenario, the user can refer to the ‘backup.log’ file to recreate the lost resources by themselves. 
### Specific Limitations:
#### [Limitations of VM migration.](readme/VM_INSTANCE_README.md)
#### [Limitations of instance group migration.](readme/INSTANCE_GROUP_README.md)
#### [Limitations of target pool migration.](readme/TARGET_POOL_README.md)
#### [Limitations of backend service migration.](readme/BACKEND_SERVICE_README.md)
#### [Limitations of forwarding rule migration.](readme/FORWARDING_RULE_README.md)

## Before Running
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
       `pip3 install --upgrade google-api-python-client`
## Set Up
    cd vm_network_migration
    pip3 install .
## Run
#### Migrate by selfLink.
A GCE resources can be referred by its selfLink.
A legal selfLink's format can be 'https://www.googleapis.com/compute/v1/projects/project/zones/zone/instances/instance'
or 'projects/project/zones/zone/instances/instance'

     python3 migrate_by_selfLink.py --selfLink=selfLink-of-target-resource  \
     --region=us-central1 --network=my-network  --subnetwork=my-network-subnet \
     --preserve_instance_external_ip=False
     
#### Single VM network migration. [See more examples.](readme/VM_INSTANCE_README.md)
     python3 instance_network_migration.py  --project=my-project \
     --zone=us-central1-a  --original_instance=my-original-instance  \
     --network=my-network  --subnetwork=my-network-subnet1 \
     --preserve_external_ip=False 
     
#### Instance group network migration. [See more examples.](readme/INSTANCE_GROUP_README.md)
     python3  instance_group_migration.py  --project=my-project \
     --instance_group=my-original-instance-group  --region=us-central \
     --zone=None --network=my-network  --subnetwork=my-network-subnet1 \
     --preserve_external_ip=False
     (Note: either --region or --zone must be specified.)
  
#### Target pool network migration. [See more examples.](readme/TARGET_POOL_README.md)
    python3 target_pool_migration.py  --project=my-project \
    --target_pool_name=my-target-pool --region=us-central1 \
    --network=my-network  --subnetwork=my-network-subnet \
    --preserve_instance_external_ip=False

#### Backend service migration. [See more examples.](readme/BACKEND_SERVICE_README.md)
    python3 target_pool_migration.py  --project=my-project \
    --target_pool_name=my-target-pool --region=us-central1 \
    --network=my-network  --subnetwork=my-network-subnet \
    --preserve_instance_external_ip=False
    
#### Forwarding rule migration. [See more examples.](readme/FORWARDING_RULE_README.md)
    python3 forwarding_rule_migration.py  --project=my-project \
    --forwarding_rule_name=my-forwarding-rule  --region=us-central1 \
    --network=my-network  --subnetwork=my-network-subnet1 \
    --preserve_instance_external_ip=False

## Source Code Headers

Every file containing source code must include copyright and license
information. This includes any JS/CSS files that you might be serving out to
browsers. (This is to help well-intentioned people avoid accidental copying that
doesn't comply with the license.)

Apache header:

    Copyright 2020 Google LLC

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
