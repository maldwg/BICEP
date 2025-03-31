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

