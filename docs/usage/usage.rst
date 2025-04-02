Usage
======
This section describes how to actually use the framework (how to start a container, ensemble and analyses).

The following demo gives you an impression on how to spin up a new IDS container, how to trigger a static analysis and,  and how to obtain the resulting metrics. 

.. image:: ../../assets/bicep-demo.gif

Combine container to ensembles
-------------------------------

To combine multiple containers into an Ensemble, the following requirements need to be met:
1. Have multiple IDS spun up using the framework
2. The IDS containers need to be idle, i.e. they must not execute any analyses at the moment

Then you can use the web GUI's ``setup`` tab to craete a new ensemble which consists of the IDS containers. Duriong the setup form you will be asked for the exact containers and the enesembling method to use.
If you made a mistake, you can later edit the ensemble at any time to change the containers and techniques used.

Start analyses
---------------

On the dashboard view, after you have deployed at least one IDS container, you can trigger a static or a live analysis. You can do this by clicking on the ``start analysis`` button on either an IDS or ensemble.

.. note::
    The container needs to be idle in order to trigger an analysis. For an ensemble, simply click the button on the ensemble card. Please note, that **EVERY** container that is part of the ensemble needs to be idle in order to be able to trigger an analysis.


Evaluation of IDS container and ensembles
--------------------------------------------

The following metrics are curerntly supported and displayed in Grafana (which is embedded in the web GUI on the ``Metrics`` tab).

- CPU consumption
- RAM consumption
- False Positive Rate
- False Negative Rate
- Detection Rate
- False Detection Rate
- Accuracy
- Precision
- F1 Score
- Unassigned Ratio

The unassigned ratio metric reflects how many of the alerts that were yielded by the IDS or ensemble could be assigned to an entry in the labels file. If this value is high, then your IDS is likely to either produce many alerts for flows that do not exist in your labels file, or to yield multiple alerts for a single flow. The metric should not be overstated.


