Extend the framework
=====================

.. _add_new_dataset:
How to add a new dataset type
-----------------------------

If you need to use a dataset that of a type that is currently not supported, you can add your own type to the framework.
First you will need to add a new entry to the DB. This can be done while the framework is running or by adding the necessary sql statements in 
``./database/bicep.sql``
Each entry should look like this:

.. code-block:: sql

    INSERT INTO dataset_type (name, description, function_prefix) VALUES ('Network Analysis Data', 'Network traffic data in form of PCAPs. The labels are in CSV file format', 'network_traffic_data');
The ``function_prefix`` determines how your python file has to be named and what the prefix for the functions you will need to implemented is.

BICEP is designed to automatically look for the appropriate dataset types listed in the DB. Your code to handle the new type needs to be located in
``./backend/core/app/models/dataset_types_implementation/<your_dataset_type_name>.py``
Then you will need to implement 2 functions which **NEED TO ADHERE** to the following naming convention:

``<your_dataset_type_name>_get_benign_and_malicious_counts_of_labels_file``
``<your_dataset_type_name>_get_positives_and_negatives_from_dataset``
This ensures that the system can find these. The documentation for these methods can be found in :doc:`Dataset Types Implementation </design/models.dataset_types_implementation>`
Afterwards, feel free to create a pull request to contribute to the framework.

.. _add_new_ensembling_technique:
How to add a new ensembling technique
--------------------------------------

Currently, only the simple majority vote algorithm is supported to construct an ensemble. If you need a more sophisticated technique, you will need to implement it. 
To do so, you will need to add a new entry to the DB first. This can be done while the framework is running or by adding the necessary sql statements in 
``./database/bicep.sql``
Each entry should look like this:

.. code-block:: sql

    INSERT INTO ensemble_technique (name, description, function_name) VALUES ('Majority Vote', 'A simply Majority vote approach where all IDS in the ensemble have the same weight', 'majority_vote');`

Where ``name`` is the display name, and function_name your python file and function name.
BICEP is designed to automatically look for the appropriate ensembling techniques listed in the DB. Your code to handle the new type needs to be located in
``./backend/core/app/models/ensemble_techniques_implementation/<your_ensemble_technique_name>.py``
Then you will need to implement 2 functions which **NEED TO ADHERE** to the following naming convention:

``<your_dataset_type_name>_get_benign_and_malicious_counts_of_labels_file``
``<your_dataset_type_name>_get_positives_and_negatives_from_dataset``
This ensures that the system can find these. The documentation for these methods can be found in :doc:`Ensembling Technique Implementation </design/models.ensemble_techniques_implementation>`
Afterwards, feel free to create a pull request to contribute to the framework.

