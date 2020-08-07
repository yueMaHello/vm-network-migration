# Forwarding Rule Network Migration
## Limitations:
1. Supported type: ‘EXTERNAL’, ‘INTERNAL’ and ‘INTERAL_MANAGED’.
2. All the backend service, target pools, or target instances serving the forwarding rule will be migrated to the VPC subnet.
3. If any of its backends is serving multiple resources, the migration will fail and rollback to the original network.
4. For an internal or internal-managed forwarding rule, it will be deleted and recreated using the new network configuration. For an external forwarding rule, it will not be deleted.
