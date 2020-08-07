# Single VM Network Migration
## Limitations:
1. If the original VM uses a Ephemeral external IP, and the customer chooses to preserve it, it will become a static external IP after the migration.
2. Support migrating a VM from a legacy network to a subnetwork, or from one VPC network to another. Within a network, a VM can also be migrated from one subnet to another. Migration from any network to a legacy network is not allowed.
3. The original VM should only have one NIC.
4. The original VM and the new VM will have the same configuration except for the network interface. Therefore, they are in the same project, same zone, and same region.
5. The original VM must not be part of any instance group before changing the network it is associated with, since VMs in an instance group have to be in the same network. 
6. The original VM is assumed to be standalone. Other cases, for example, if the original instance is served as a backend of other services are not considered in the current scope.
7. There is a possibility that the main flow runs into an error and the rollback procedure also fails. In this case, the customer may lose both the original VM and the new VM. The original VM’s configuration will be printed out as a reference.  

## Examples:
### 1. Migrate an instance without preserving the external IP address:
     python3 instance_network_migration.py  --project=my-project \
        --zone=us-central1-a  --original_instance=my-original-instance  \
        --network=my-network  --subnetwork=my-network-subnet1 \
        --preserve_external_ip=False 
### 2. Migrate an instance with preserving the external IP address:
Note: No matter whether its external IP address is a static one or a ephemeral one, 
it will be reserved as a static IP after the migration. The preserving action is not reversible. 

     python3 instance_network_migration.py  --project=my-project \
         --zone=us-central1-a  --original_instance=my-original-instance  \
         --network=my-network  --subnetwork=my-network-subnet1 \
         --preserve_external_ip=True
          
