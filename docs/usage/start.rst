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
For a single-node setup, no special Docker daemon configuration is required. BICEP's core service connects to the Docker daemon through the Unix socket (``/var/run/docker.sock``), which is mounted into the core container by the ``docker-compose.yaml``. This means the daemon is never exposed over the network.

.. note::
    If you need to use a custom socket path, set the ``DOCKER_SOCKET_PATH`` environment variable in the core service.

.. warning::
    If not configured correctly you will not be able to start any IDS container or the metric service.

.. _distributed_setup:

Distributed Setup
-----------------

You may want a distributed setup to host the application on one machine and benchmark IDS' on another node, to avoid performance intereference. 
For this, the remote machine's Docker daemon needs to be reachable over TCP from the machine running BICEP.

.. warning::
    Exposing the Docker daemon over an unencrypted and unauthenticated TCP connection is a significant security risk, as it grants root-equivalent access to the remote machine. **We strongly recommend securing the daemon with TLS mutual authentication (mTLS)** before exposing it over the network. See https://docs.docker.com/engine/security/protect-access/ for the full guide.

**Recommended: Secure the daemon with TLS**

Generate a CA, server certificate and client certificate on the remote node, then configure ``/etc/systemd/system/docker.service.d/docker.conf``:

.. code-block:: bash

    [Service]
    ExecStart=
    ExecStart=/usr/bin/dockerd -H tcp://x.x.x.x:2375 -H unix:///var/run/docker.sock \
        --tlsverify --tlscacert=/etc/docker/certs/ca.pem \
        --tlscert=/etc/docker/certs/server-cert.pem \
        --tlskey=/etc/docker/certs/server-key.pem

Then place the corresponding client certificate, key and CA in a directory accessible to the core container (e.g. ``/etc/docker/certs/client/``) and mount it:

.. code-block:: yaml

    # docker-compose.yaml — core service
    volumes:
      - /etc/docker/certs/client:/etc/docker/client-certs:ro

Configure the core to use the client certs by setting the following environment variables on the core service:

.. code-block:: yaml

    environment:
      - DOCKER_TLS_CERTDIR=/etc/docker/client-certs

**Minimum (insecure) alternative**

If TLS is not possible, restrict the bind address to only the IP that the BICEP machine can reach and use firewall rules to allow port 2375 only from the BICEP host's IP.

In ``/etc/systemd/system/docker.service.d/docker.conf``:

.. code-block:: bash

    [Service]
    ExecStart=
    ExecStart=/usr/bin/dockerd -H tcp://x.x.x.x:2375 -H unix:///var/run/docker.sock --tls=false

Make sure that you expose a remotely available IP address that the other machine hosting the BICEP application can reach!

.. warning::
    Never bind to ``0.0.0.0`` without firewall restrictions. Doing so grants unauthenticated root-level access to your machine to anyone who can reach that port.

Afterwards run:

.. code-block:: bash

    sudo systemctl daemon-reload
    sudo systemctl restart docker.service

This refreshes the daemon for Docker. You can now use the web GUI to add the new node to the framework by following the instructions on the `Docker Hosts` tab. 
Per default, the localhost (the machine where the framework is running), is already added and can be used. Any other node needs to be added via the GUI or DB.

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
