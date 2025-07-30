
<div align="center">

<img alt="Codecov" src="https://img.shields.io/codecov/c/github/maldwg/BICEP?style=for-the-badge">
<img alt="GitHub branch status" src="https://img.shields.io/github/checks-status/maldwg/BICEP/main?style=for-the-badge&label=Tests">


</div>
<br>
<div align="center">
<a href="https://bicep.readthedocs.io/en/latest/"><i><u>View Docs</i></u></a>
<br>
<br>



![](./assets/Biceps_logo.gif)


</div>

## About The Project

BICEP presents an evaluation platform to benchmark arbitrary IDS solutions like Suricata, Snort, Zeek or Slips, in order to achieve comparability amongst IDS tools and novel apporaches. Practically every (D)IDS or (C)IDS can be added to the system via its plugin capability. 

Currently only Suricata and Slips modules are implemented and supported in terms of setup, configuration, lifecycle management and benchmarking.

The project is still under development and breaking changes are likely to occur. 

## Supported Systems 

Currently we are supporting Linux based systems, but we are actively trying to support MacOS as well.
For The setup process for Macs' differ, consult the documentation at (https://bicep.readthedocs.io/en/latest/usage/start.html#mac-support)

## Initialize The Project
In order to be able to start the project you will need to initialize it first. Do this by running:

```
git submodule update --init --recursive
```
This fetches the newest version of the submodule for the backend code and is necessary for the application to work seamlessly.


## Start The Project

> [!IMPORTANT]
> In order for the framework to work out of the box, the host where you want to deploy containers needs to be prepared as mentioned [here](https://bicep.readthedocs.io/en/latest/usage/start.html#distributed-setup)

The project can be started by running running ```docker compose --env-file environments/dev up```. This will spin up all containers in development mode. To run the stack in production mode, simply use the production env file like so: ```docker compose --env-file environments/prod up```


## Use The Framework
![BICEP-USAGE](./assets/bicep-demo.gif)

## Documentation

Documentation for setup, configuration, usage and contribution is available under [BICEP-read-the-docs](https://bicep.readthedocs.io/en/latest/)