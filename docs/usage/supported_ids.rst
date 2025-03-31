Supported IDS
=============

Currently the following IDS are supported and registered with the framework to be used right-away:

.. list-table:: Supported IDS Solutions
   :header-rows: 1

   * - IDS Solution
     - Docker Image
     - GitHub Repository
     - Status
   * - Slips
     - `Slips-Image <https://hub.docker.com/r/maxldwg/bicep-slips>`_
     - `Slips implementation <https://github.com/maldwg/BICEP-slips-image>`_
     - ✅ Available
   * - Suricata
     - `Suricata-Image <https://hub.docker.com/r/maxldwg/bicep-suericata>`_
     - `Suricata implementation <https://github.com/maldwg/BICEP-suricata-image>`_
     - ✅ Available
   * - Snort
     - `Snort-Image <https://hub.docker.com/r/maxldwg/bicep-snort>`_ 
     - `Snort implementation <https://github.com/maldwg/BICEP-snort-image>`_
     - ✅ Available



.. _add_new_ids:
How to add a new IDS
--------------------
If you did not find the IDS you desired to run and evaluate in the currently supported IDS, or if you want to register your own system to the framework, you can follow these steps to include it:

You will need to provide the following in a docker image:

- Your system (executable via CLI) and all its dependencies
- BICEP_Utils should be added as submodule as it contains the fastapi server for the IDS as well as class definitions on Alerts and Base classes.
- The implementation of the base classes for the AlertParser and the IDSBase from the Bicep_Utils repository.
- A main.py that starts the fastAPI server, as can be seen in the example of suricata or slips or snort . For inspiration and sample implentations, have a look at the modules for Sruciata and Slips. The modules to implement can be found in BICEPs-utils

At the current state, a new IDS needs to be introduced to the DB of BICEP. Either add id by modifying the Database or the sql script providing the default entries. A feature is planned that automatically checks for available BICEP models so that this step is not necessary anymore.
For now you will need to add a new entry in ``./database/bicep.sql`` 
Each entry should look like this:

.. code-block:: sql

  INSERT INTO ids_tool (name, ids_type, analysis_method, requires_ruleset, image_name, image_tag) VALUES ('Suricata', 'NIDS', 'Signature-based', true, 'maxldwg/bicep-suricata', 'latest');

The ``ids_type`` and ``analysis_method`` are metadata for the moment. The other values need to be filled in according to the solution you try to register.


Tests
------
As you should be testing your newly registered IDS, you can follow the testing template located in the `BICEP_Utils <https://github.com/maldwg/BICEP_Utils>`_ repository.
In the `BICEP_Utils <https://github.com/maldwg/BICEP_Utils>`_ repository under tests/ids_plugin_test_templates are some templated tests that you can build on and extend. Your resulting IDS should be able to satisfy these and provide the necessary capabilities of the Base classes IDSBase and ParserBase