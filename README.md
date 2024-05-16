# BICEP
BICEP - Benchmarking IDS in a Comparative Evaluation Platform 


## Initialize project

In order to be able to start the project you will need to initialize it first. Do this by running:

```
git submodule init
git submodule update
```
This fetches the newest version of the submodule for the backend code and is necessary for the application to work seamlessly.

## Start the project

The project is comprised of several modules which can be started by running ```docker compose up```.

<!-- 
# start
# suricata-update
# suricata -c /usr/local/etc/suricata/suricata.yaml -l /usr/local/var/log/suricata  -i eth0  
# insead of interface: -r pathtofile
# -s /usr/local/var/lib/suricata/rules/suricata.rules for additional ruels
# logfiles: /usr/local/var/log/suricata/special.json -->