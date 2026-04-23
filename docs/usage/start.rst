Start
=====

You can start the framework by running:

.. code-block:: console

    PRODUCTION=FALSE CORE_HOST_IP=127.0.0.1 docker compose up

Alternatively you can start the framework in production mode by running:

.. code-block:: console

   PRODUCTION=TRUE CORE_HOST_IP=127.0.0.1 docker compose up

The framework can then be accessed via ``http://localhost:8080`` on development mode or ``http://<your-ip-ord-dns>:8080``

.. warning::
    If you plan to switch between the modes, make sure to build the angular container from scratch using the respective env file
    For instance run: 
    ``PRODUCTION=TRUE CORE_HOST_IP=127.0.0.1 docker compose build angular``

.. warning::
    For a multinode setup it is required that you are setting the CORE_HOST_IP to the IP of the machine hosting the framework, otherwise the IDS and metric services won't be able to reach the core and the app won't work!

Differences Between Production and Development Mode
---------------------------------------------------

The main difference between the two modes is how the Frontend connects to the backend. In development mode, it tries to reach out via "localhost". 
In Production mode, it uses the host name property to reach out to the services. This allows an user to connect to the frontend remotely i.e. BICEP can be deployed on a remote machine.
If Production mode has not been enabled in such a setup, the frontend tries to reach the backend services on the localhost of the client, which is false. The development mode is assumed as default.

.. warning::
    The production mode currently does not support a distributed setup of the (core) system, i.e. the different services of BICEP NEED to run on the same machine.


.. _distributed_setup:

Distributed Setup
-----------------

If you want to run your IDS and ensembles, you will need to configure a node. For a small setup, this will be the machine that hosts the framework as well. However, you can configure any machine to host IDS containers by following these steps:

You will need to adapt the docker configuration on the node you would like to add.
In your docker config in ``/etc/systemd/system/docker.service.d/docker.conf`` add the following lines:

.. code-block:: bash

    [Service]
    ExecStart=
    ExecStart=/usr/bin/dockerd -H tcp://0.0.0.0:2375 -H unix:///var/run/docker.sock


.. warning::
    0.0.0.0 allows access from any IP, which is used here for simplicity and reproducibility reasons. You should make sure to only allow trusted IPs to access the docker daemon remotely.




This will allow external services like the core to access the Docker daemon remotely. Afterwards run:

.. code-block:: bash

    sudo systemctl daemon-reload
    sudo systemctl restart docker.service

This refreshs the daemon for docker. You can now use the web GUI to add the new node to the framework by following the instructions on the `Docker Hosts` tab. 
per default, the localhost (the machine where the framework is running), is already added and can be used. Any other node needs to be added via the GUI or DB.

.. _mac_support:

Mac Support
-----------
If you are using an apple device, you might want to configure the docker deamon in the toolbox, by adding 

.. code-block:: 

    {
        "hosts": [
            "tcp://0.0.0.0:2375"
            "unix:///var/run/docker.sock"
        ]
    }

.. warning::
    0.0.0.0 allows access from any IP, which is used here for simplicity and reproducibility reasons. You should make sure to only allow trusted IPs to access the docker daemon remotely.


In your engine configuration or docker.json

Deactivating Containerd
~~~~~~~~~~~~~~~~~~~~~~~~~
Containerd needs to be deactivated, otherwise the Docker-based observability components may run into issues later on. 
To do so, go into the docker desktop ``settings > general`` and deactivate ``Use containerd for pulling and storing images``.
