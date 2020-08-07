# Target Pool Network Migration
## Limitations:
1. The target pool can have single VMs and managed instance groups in it. 
2. If there is an VM instance which belongs to an unmanaged instance group, it is an ambiguous situation. This unmanaged instance group may have other instances which are not serving this instance group, so it is not proper to infer the user wants to migrate the whole group. In this scenario, the migration will not start. The user should detach these instances first, and then migrate this target pool.
3. If the target pool shares the same backends with another backend service or another target pool, the migration will fail and rollback to the original network.
4. The target pool will not be deleted.

