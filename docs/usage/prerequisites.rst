Prerequisites
=============
Initialize the submodules
--------------------------
In order to be able to start the project you will need to initialize it first. Do this by running:
``git submodule update --init--recursive```
This fetches the newest version of the submodule for the backend code and is necessary for the application to work seamlessly.


Prepare the docker node
------------------------
In order to use the framework locally, you will need to have Docker installed. 
Furthermore, your docker client needs to be configured properly, as the framework will try to use the docker daemon to run containers.
For the proper configuration of your docker client, refer to the sections :ref:`Core Configuration <core_configuration>` and :ref:`Distributed Setup <distributed_setup>`