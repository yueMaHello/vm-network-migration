# Instance Group Network Migration
## Limitations:
1. For a managed instance group, after the migration, the VM instances of this group will be recreated with new disks and new IP addresses. A new instance template will be inserted without deleting the original instance template.
2. IP preservation feature is only for an unmanaged instance group. 
3. If the instance group is the backends of other services, the migration will not start or will rollback.
4. The original instance group will be deleted and recreated using modified network configuration

## Examples:

