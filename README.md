
<div align="center">

<img alt="Codecov" src="https://img.shields.io/codecov/c/github/maldwg/BICEP?style=for-the-badge">
<img alt="GitHub branch status" src="https://img.shields.io/github/checks-status/maldwg/BICEP/main?style=for-the-badge&label=Tests">


</div>
<br>
<div align="center">
<a href="https://bicep.readthedocs.io/en/latest/"><i><u>View Docs</i></u></a>
<br>
<br>



![](./assets/Biceps_logo.png)


</div>

## About The Project

BICEP presents an evaluation platform to benchmark arbitrary IDS solutions like Suricata, Snort, Zeek or Slips, in order to achieve comparability amongst IDS tools and novel apporaches. Practically every (D)IDS or (C)IDS can be added to the system via its plugin capability. 

Currently Suricata, Snort, and Slips modules are featured IDS.

We presented this framework at the 9th CSNet. If you are interested, take a look at our paper [here](https://doi.org/10.1109/CSNet64211.2024.10851475)!

## Supported Systems 

Currently, we are supporting Linux based systems, but we are actively trying to support MacOS as well.
For The setup process for Macs' differ, consult the documentation at [mac-support](https://bicep.readthedocs.io/en/latest/usage/start.html#mac-support)

## Initialize The Project
In order to be able to start the project you will need to initialize it first. Do this by running:

```
git submodule update --init --recursive
```
This fetches the newest version of the submodule for the backend code and is necessary for the application to work seamlessly.


## Start The Project

> [!IMPORTANT]
> In order for the framework to work out of the box, the host where you want to deploy containers needs to be prepared as mentioned [here](https://bicep.readthedocs.io/en/latest/usage/start.html#core-configuration)

The project can be started by running 
```
PRODUCTION=TRUE CORE_HOST_IP=127.0.0.1 docker compose up -d
```
. This will spin up all containers. To run the stack in dev mode, simply set `PRODUCTION` to `FALSE`. 


## Use The Framework
![BICEP-USAGE](./assets/bicep-demo.gif)

## Documentation

Documentation for setup, configuration, usage and contribution is available under [BICEP-read-the-docs](https://bicep.readthedocs.io/en/latest/)
