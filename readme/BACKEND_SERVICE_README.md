# Backend Service Network Migration
## Limitations:
1. Supported type: ‘EXTERNAL’, ‘INTERNAL’ and ‘INTERAL_SELF_MANAGED’.
2. If an internal backend service is serving a frontend, the migration will not start. The user should detach this backend service from the frontend, or directly migrate its frontend instead. 
3. If an external backend service is serving a frontend, the migration is legal. 
4. If a backend service is serving multiple frontends at the same time, the migration can still succeed, but it is not recommended.
5. For external or an internal-self-managed backend service, it will not be deleted. For an internal backend service, it will be deleted and recreated using the new network configuration.


          
