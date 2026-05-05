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


.. _core_configuration:

Core Configuration
------------------
The docker daemon on the Core machine needs to be configured appropriately, so that containers can be deployed by it. For this you need to adjust the docker config in ``/etc/systemd/system/docker.service.d/docker.conf`` add the following lines:

.. code-block:: bash

    [Service]
    ExecStart=
    ExecStart=/usr/bin/dockerd -H tcp://172.22.0.1:2375 -H unix:///var/run/docker.sock --tls=false

This will allow external services like the core to access the Docker daemon remotely. Afterwards, run:

.. code-block:: bash

    sudo systemctl daemon-reload
    sudo systemctl restart docker.service



.. warning::
    Please note that this allows connections to the docker daemon only by the local machine via the BICEP network. If you change the network as configured in the ``docker-compose.yaml`` then you will need to adjust the daemon accordingly.
    If not configured correctly you will not be able to start any IDS container or the metric service.


Troubleshooting
~~~~~~~~~~~~~~~~

**My Docker service is not starting after changing the configuration**

The reason can be twofold: On newer versions of docker >29, the docker daemon needs to be started with the ``--tls=false`` flag to allow unencrypted connections or the daemon needs to be secured properly https://docs.docker.com/engine/security/protect-access/.
Alternatively, the docker service might refuse to start because it can't bind to the 172.22.0.1 IP address. Two mitigate this either (before changing the daemon configuration), start the BICEP application, to create the needed interface, or run the following:

.. code-block:: bash

    sudo ip link add docker-dummy0 type dummy
    sudo ip addr add 172.22.0.1/32 dev docker-dummy0
    sudo ip link set docker-dummy0 up
    sudo systemctl restart docker 
    sudo ip link delete docker-dummy0

This will create a temporary dummy interface with the required IP address, so that the docker daemon can start and create the BICEP network. After the network is created, the dummy interface can be removed again.


**After starting the application, the docker host is not becoming available**

In this case check the logs of the core. Either, your docker daemon is not configured with the proper IP bind address, or a firewall setup on your host like ufw is blocking the connection. To bypass the latter, you will need to add a rule to allow incoming connections on port 2375.



.. _distributed_setup:

Distributed Setup
-----------------

You may want a distributed setup to host the application on one machine and benchmark IDS' on another node, to avoid performance intereference. 
For this, the remote machine needs to have the docker daemon configured like the Core host, with some slight differences:

In your docker config in ``/etc/systemd/system/docker.service.d/docker.conf`` add the following lines:

.. code-block:: bash

    [Service]
    ExecStart=
    ExecStart=/usr/bin/dockerd -H tcp://x.x.x.x:2375 -H unix:///var/run/docker.sock --tls=false

Make sure that you expose a remotely available IP address that the other machine hosting the BICEP application can reach! 

.. warning::
    0.0.0.0 allows access from any IP. You should make sure to only allow trusted IPs to access the docker daemon remotely. We refer to https://docs.docker.com/engine/daemon/remote-access/ and https://docs.docker.com/engine/security/protect-access/ for a secure Docker daemon connection.



Afterwards run:

.. code-block:: bash

    sudo systemctl daemon-reload
    sudo systemctl restart docker.service

This refreshs the daemon for docker. You can now use the web GUI to add the new node to the framework by following the instructions on the `Docker Hosts` tab. 
per default, the localhost (the machine where the framework is running), is already added and can be used. Any other node needs to be added via the GUI or DB.

.. _mac_support:

Mac Support
-----------
If you are using an apple device, you might want to configure the docker daemon in the toolbox, by adding 

.. code-block:: 

    {
        "hosts": [
            "tcp://172.22.0.1:2375"
            "unix:///var/run/docker.sock"
        ]
    }

In your engine configuration or docker.json

Deactivating Containerd
~~~~~~~~~~~~~~~~~~~~~~~~~
Containerd needs to be deactivated, otherwise the Docker-based observability components may run into issues later on. 
To do so, go into the docker desktop ``settings > general`` and deactivate ``Use containerd for pulling and storing images``.
