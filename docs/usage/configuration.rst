Configuration
=============

This section explains how to handle the configurations of the framework, in particular: how to add a configuration, rule set, and dataset


Default Configurations
-----------------------
For the already integrated and supported IDS, sample configurations and a small test dataset from the CIC-IDS-2017 dataset is already integrated. These configurations will get you started pretty fast but are not meant to be used in production. You should provide your own configuartions, ruleset and datasets.


Upload
-------
Any configuration can be uploaded using the web GUI's ``Uploads`` tab. There, the currently available configurations are displayed and further configurations can be added.
This includes also rulesets and datasetst. 

Datasets
---------
At the moment, only datasets that fulfill the below requirements are supported. If your dataset differs, you can create a new ``dataset type`` to be featured in the framework. More details on that can be found in section :ref:`How to add a new dataset type <add_new_dataset>`

1. It needs to be split into a pcap file containing the requests and a CSV file containing labels for each request

2. The requests from the pcap need to be assignable to the CSV rows, therefor the following needs to be assured:
    - In the CSV file, there must be a column named "Label" or "Class". which contains the keyowrd "benign" for each benign request. Malicious requests might be labled as desired
    - The following Columns need to be present as well
        - Time/Timestamp: containing a timestamp as exact as possible which corresponds to the one in the pcap file for the request
        - Source IP: Source IP of the request
        - Source Port: Source Port of the request
        - Destination IP: Destination IP of the request
        - Destination Port: Destination port of the request

Host Configurations
---------------------
If you want to add an IDS you might need adaptations to the host for your system to work properly.
As of now, we do not intend to support a feature where you can make adaptations to the host machines
via BICEP. If you desire such a functionality, feel free to open an issiue!


.. _cids_scaling:

CIDS Service Scaling
---------------------
When deploying a CIDS via Docker Compose, BICEP supports scaling individual services
by specifying a replica count per service in the setup UI.

**Docker Compose Convention**

Scalable services should use the ``deploy.replicas`` directive with an environment
variable that defaults to ``1``:

.. code-block:: yaml

    services:
      my-sensor:
        image: my-ids/sensor:latest
        deploy:
          mode: "replicated"
          replicas: ${MY_SENSOR_SCALE:-1}

The variable naming convention is ``${SERVICE_NAME_SCALE:-1}`` where
``SERVICE_NAME`` is the service name in uppercase with hyphens replaced by
underscores.

**How It Works**

When deploying, BICEP collects the replica count for each service from the
assignment table and passes them as ``--scale service=N`` flags to
``docker compose up``. Services with a count of 1 use the default and are
not explicitly scaled.

.. note::
   The ``container_name`` directive must be removed from services that should
   be scalable, as Docker does not allow multiple containers with the same name.


.. _cids_config_injection:

CIDS Configuration Injection
------------------------------
Unlike NIDS/HIDS deployments where configuration files are injected into a running
container, CIDS services receive their configuration as a **volume mount at startup**.

**Docker Compose Convention**

Services that require the user-selected configuration file must declare a
``bicep.config.mount`` label specifying the container path where the config
should be mounted:

.. code-block:: yaml

    services:
      my-processor:
        image: my-ids/processor:latest
        labels:
          bicep.config.mount: /app/config.yaml

When BICEP deploys the CIDS, it:

1. Writes the user-selected configuration file to the deployment working directory
2. Scans all services for the ``bicep.config.mount`` label
3. Adds a volume mount (``./bicep_config:/app/config.yaml``) to each labelled service
4. Any existing volume mount targeting the same container path is automatically replaced

.. note::
   Do **not** include a hardcoded volume mount for the config file in your compose
   file. Use only the label — BICEP handles the mount automatically.

**Environment Variables**

Required environment variables for a CIDS can be defined per IDS tool in BICEP
(comma-separated in the ``required_env_vars`` field). These are displayed to the
user during setup and must be filled in before deployment. Users may also add
custom variables. All variables are injected into ``docker compose up`` via the
process environment.