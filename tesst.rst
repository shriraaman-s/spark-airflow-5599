.. include:: ../../links.rst
.. _autonomous-agents-architecture-ref:


Architecture
++++++++++++

Overview
========

*Autonomous Agents* take a business question from the user (related to structured, and unstructured datasets) and come up with a solution approach to solve the question and assign tasks to various agents depending on the data availability and complexity of the question.

The current version of *Autonomous Agents* is capable of handling business questions from the end user that involve performing tasks related to SQL data gathering, visualization, insights generation, model building, summarizing, etc. The below agents with targeted individual persona and skill sets are developed to that extent:


#. :meth:`Manager agent <autonomous_agents.agents.ManagerAgent>`
#. :meth:`SQL data processor agent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>`
#. :meth:`Plotly chart generator agent <autonomous_agents.insights_pro_agents.PlotlyVisualizerAgent>`
#. :meth:`Insights generator agent <autonomous_agents.insights_pro_agents.InsightsGeneratorAgent>`
#. :meth:`Python developer agent <autonomous_agents.agents.PythonDataAgent>`
#. :meth:`Python modelling agent <autonomous_agents.agents.PythonModellingAgent>`
#. :meth:`RAG Agent <autonomous_agents.agents.RAGAgent>`
#. :meth:`Summarizer agent <autonomous_agents.agents.SummarizerAgent>`



Architecture Flowchart
======================
.. note::

    Note that the below Architecture is one possible solution for using Autonomous agents. This architecture may vary based on the data available and the complexity of the use case. It is recommended to use individual components available and orchestrate the solution based on the use case.

.. figure:: ../../images/autonomous_agents/architecture_diagram.png
    :align: center
    :name: autonomous-agents-architecture-diagram

    Autonomous Agents architecture (one possible out of many)


Understanding the Flow
======================

.. _autonomous-agents-glossary-terms-ref:

Question refactoring (glossary keywords)
----------------------------------------
When the end users ask questions like "What are the sales of Omega", since the app doesn't have context of what "Omega" is, it can't generate an appropriate response. To facilitate this, we have included a ``glossary_terms.csv`` file where the user can business-specific glossary, common terminology, and keywords. The user question is refactored to give the agents a better understanding of the terms used by the users. Refer to :meth:`question refactor function <autonomous_agents.utils.get_question_after_refactoring>` for more details.


For example, a sample ``glossary_terms.csv`` file looks like:

+-------------+-------------------------+------------+
| **keyword** | **keyword_in_the_data** | **entity** |
+-------------+-------------------------+------------+
| Omega       | OMEGA                   | brand      |
+-------------+-------------------------+------------+

We can add all variants of the keywords in separate rows in this file (Ex: Omega and omega can be two separate line entries). Mention the equivalent value available for the keyword in the data and the entity mentioned in the `entity` column will be used to add extra phrasing to the user question as shown in the example below:

.. code-block:: text
    :linenos:

    Input question - What are the sales of Omega?
    Refactored input question -  What are the sales of OMEGA where 'OMEGA' is a brand?


First, if some unstructured (text) data exists, the user's question, referred to as the **Goal**, is sent to the ``RAG Agent``. Here information relevant to the user's question will be extracted. If the unstructured data (or text documents) has enough information to answer the question, the tool will summarize the available information and respond to the user. If the text documents don't have enough information, the tool retrieves relevant information that can be used later as an additional context by other agents. If the first attempt doesn't retrieve any information from the unstructured data, we change the parameters (chunk size, overlap between the chunks) and retry until a configurable limit is reached.

In cases where the unstructured data is not available, the user's question is directly sent to the :meth:`Manager agent <autonomous_agents.agents.ManagerAgent>` without any additional context.

.. note::

    Alternatively, we may use web search agents if there is to get additional context from the web and outside the available data. For example, if the user wants to compare their metrics with industry standards, we may use the web search agents to get the industrial benchmarks.


Task Understanding and Breakdown
--------------------------------

Next, the user's question along with the additional context is passed to the :meth:`Manager agent <autonomous_agents.agents.ManagerAgent>`, which breaks the **Goal** into multiple sub-tasks. :meth:`Manager agent <autonomous_agents.agents.ManagerAgent>` is also responsible for assigning the appropriate Agent to each sub-task and the dependencies between the sub-tasks to create a **Task list**.

This generated task list undergoes reflection where the number of sub-tasks in the list is reduced. For example, two consecutive SQL sub-tasks can be combined into one, or if there are SQL or modeling sub-tasks that are related to each other and the intermediate output is not necessary then these sub-tasks are merged to create an updated task list.

This task list is added to the :meth:`shared memory <autonomous_agents.shared_memory.SharedMemory>` where the :meth:`Manager agent's <autonomous_agents.agents.ManagerAgent>` response (along with the other agents' responses) are stored.

We also check if there is any :meth:`SQL data processor agent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>` that is not used as a data dependency for any agent except :meth:`Plotly chart generator agent <autonomous_agents.insights_pro_agents.PlotlyVisualizerAgent>` and force :meth:`Insights generator agent <autonomous_agents.insights_pro_agents.InsightsGeneratorAgent>` for any such :meth:`SQL data processor agents <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>` and update the task list. This is done so that we get better summarizer outputs (instead of returning tables to the end user) for the questions that are dependent on SQL agents. We call this ``forced_insights``, for more information, please check :meth:`add_insights_for_data function <autonomous_agents.AutonomousAgents.add_insights_for_data>`

.. note::

    The current setup undergoes only one layer of task breakdown. For more complex problem statements, we might need multiple layers of breaking down **global-goal** into multiple **sub-goals** and each **sub-goal** into multiple **sub-tasks**.


Execution Flow
--------------
The sub-tasks generated above will be executed by the assigned agents in order sequentially. They produce Python or SQL codes as outputs, which, when executed, provide answers to the sub-tasks. The output from one or more agents can serve as input for another agent, with dependencies specified in the task list. The final outputs from the agent could be tables, plots, insights (stdout), model objects, csv outputs, error messages, etc.

During execution, the responses produced by each agent are stored in a :meth:`vector database <autonomous_agents.shared_memory.SharedMemory>` and local/ cloud file storage. Additionally, the responses are also added to ``agent_conversation``. After every agent run, we check if there is a need to update the next sub-task based on the generated responses based on the ``agent_conversation`` and dynamically update the task list. We also use ``forced_insights`` while updating the task list.

Summarization
-------------

Finally, the responses generated by all the agents will be collected and passed to a :meth:`Summarizer agent <autonomous_agents.agents.SummarizerAgent>` which summarizes the responses of each agent (queries, graphs, insights, and other responses) to answer the user question.

.. note::

    Multiple SummarizerAgents should be used when there are multiple layers of task breakdown.

.. _autonomous-agents-components-ref:

Components
==========

To simplify and enhance the results, agents and helping tools are created. Separate agents are created to perform specific tasks. Helping tools are used to help the agents perform their respective tasks. For example, the :meth:`TaskListGenerator <autonomous_agents.actions.TaskListGenerator>` tool is used to help generate the task list by the manager agent.


.. _autonomous-agents-agents-docs-ref:
.. _autonomous-agents-insights-pro-agents-docs-ref:

Agent
-----
Agents are individual building blocks of Autonomous Agents designed to carry out a particular task (code generation (SQL and Python), summarization, task breakdown, modeling, etc) assigned to them. They take the help of tools and data available to them and carry out the task using LLM calls. The current version of Autonomous Agents has the following agents:

Manager Agent
^^^^^^^^^^^^^
This agent breaks down the question and generates a task list. It ensures that the task list does not have any ambiguity and the tasks generated are relevant to the original question. This is done by adding a step after task list generation. This step is named reflection, where the task list is passed and the LLM is asked to brainstorm on it and make required changes to the list. The format of the task list generated is as follows.

``[(task_id, agent_name, task_description, input_task_id), (task_id, agent_name, task_description, input_task_id), ...]``

- ``task_id`` - It is a unique ID to which the task is mapped.
- ``agent_name`` - The Name of the agent that will perform the task.
- ``task_description`` - The description of the task.
- ``input_task_id`` - Task ID of the task whose output can be used as an input for the current task.

+--------+-------------------------------+
| Input  | Question                      |
|        +-------------------------------+
|        | Data Dictionary               |
|        +-------------------------------+
|        | Additional Context (optional) |
|        +-------------------------------+
|        | Research (optional)           |
|        +-------------------------------+
|        | available_agent_names         |
|        +-------------------------------+
|        | available_agent_actions       |
+--------+-------------------------------+
| Output | Task list                     |
+--------+-------------------------------+


For Example, for the input question, ``How do I improve the efficiency of Location 22?``, the output will be:

.. code-block:: yaml
    :linenos:

    {
        [
            {
                "task_id": 0,
                "name": "DataProcessorSQLAgent",
                "description": "Extract all the data from the \"warehouse_metrics_monthly\" table in the SQLite database.",
                "data_dependency": null
            },
            {
                "task_id": 1,
                "name": "PythonDataAgent",
                "description": "Perform feature correlation analysis between \"efficiency\" and all other numerical features in the dataset to identify potential key drivers.",
                "data_dependency": 0
            },
            {
                "task_id": 2,
                "name": "PlotlyVisualizerAgent",
                "description": "Generate a correlation heatmap of \"efficiency\" with all other numerical features to visually identify potential key drivers.",
                "data_dependency": 0
            },
            {
                "task_id": 3,
                "name": "PythonModellingAgent",
                "description": "Build a regression model with \"efficiency\" as the target variable and all other numerical features as predictors. Use the model to identify the most important features driving \"efficiency\".",
                "data_dependency": 0
            },
            {
                "task_id": 4,
                "name": "PythonModellingAgent",
                "description": "Build a regression model for Location 22 with \"efficiency\" as the target variable and all other numerical features as predictors. Use the model to identify the most important features driving \"efficiency\".",
                "data_dependency": 0
            },
            {
                "task_id": 5,
                "name": "InsightsGeneratorAgent",
                "description": "Based on the correlation analysis generate insights about the key drivers of efficiency of Location 22.",
                "data_dependency": 1
            }
        ]
    }

Data Processor SQL Agent
^^^^^^^^^^^^^^^^^^^^^^^^
Given a general task, this agent generates a complex SQL query to answer the question and generate the required data.

+--------+---------------------------------------+
| Input  | Question                              |
|        +---------------------------------------+
|        | Database (SQLite/MySQL) or Data (CSV) |
|        +---------------------------------------+
|        | Data Dictionary                       |
|        +---------------------------------------+
|        | Additional Context (optional)         |
+--------+---------------------------------------+
| Output | SQL query (SQL)                       |
|        +---------------------------------------+
|        | Data Table (CSV)                      |
|        +---------------------------------------+
|        | Data Dictionary (JSON)                |
+--------+---------------------------------------+

For Example, for the input Question, ``Extract all the data from the "warehouse_metrics_monthly" table in the SQLite database``, the output will be:

.. code-block:: sql
    :linenos:

    SELECT * FROM warehouse_metrics_monthly;

Plotly Visualizer Agent
^^^^^^^^^^^^^^^^^^^^^^^
This agent takes processed data from :meth:`DataProcessorSQLAgent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>` or :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and the question as input to generate plotly visualizations.

+--------+---------------------------------------+
| Input  | Question                              |
|        +---------------------------------------+
|        | Data Table                            |
|        +---------------------------------------+
|        | Data Dictionary                       |
|        +---------------------------------------+
|        | Additional Context (optional)         |
+--------+---------------------------------------+
| Output | Chart code (py)                       |
|        +---------------------------------------+
|        |  Plot (png)                           |
+--------+---------------------------------------+

For Example, for the input Question, ``Generate a correlation heatmap of "efficiency" with all other numerical features to visually identify potential key drivers.``, the output will be:

.. figure:: ../../images/autonomous_agents/sample_image_output.png
    :align: center
    :name: Example heatmap

    Example heatmap

For the input Question, ``Generate a time series plot for "on_time_shipment", "turn_around", and "efficiency" metrics for "Location 22" to visualize the performance over time.``, the output will be:

.. figure:: ../../images/autonomous_agents/sample_image_output_2.png
    :align: center
    :name: Example chart

    Example chart



Insights Generator Agent
^^^^^^^^^^^^^^^^^^^^^^^^
This agent takes processed data from the :meth:`DataProcessorSQLAgent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>` or :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and the question as input to generate insights on the answer generated for the given question.

+--------+---------------------------------------+
| Input  | Question                              |
|        +---------------------------------------+
|        | Data Table                            |
|        +---------------------------------------+
|        | Data Dictionary                       |
|        +---------------------------------------+
|        | Additional Context (optional)         |
+--------+---------------------------------------+
| Output | Text Insights                         |
+--------+---------------------------------------+

.. note::

    :meth:`Insights generator agent <autonomous_agents.insights_pro_agents.InsightsGeneratorAgent>` should occur at least once in the task list. The reason is that the consolidated list of results is passed to the summarizer agent, and the summarizer agent requires insights to generate the final summary.

    A ``force_insights_for_data`` flag is passed in ``orchestrator.py``. This will add 1 or more ``Insights generator agent`` tasks for every task which gives data as an output.

For Example, for the input Question, ``Based on the correlation analysis generate insights about the key drivers of efficiency of Location 22.``, the output will be:

.. code-block:: yaml
    :linenos:

    {
        - The top three features highly correlated with efficiency are 'on_time_shipment', 'on_time_shipment_norm', and 'on_time_in_full', with correlation values of 0.7975644985699883, 0.7975644985699883, and 0.4471465475464717 respectively.
        - The majority of correlation values (50% to 75%) fall within the range of 0.2654693452454858 to 0.4471465475464717, indicating these features are key drivers of efficiency.
    }


Python Developer agent
^^^^^^^^^^^^^^^^^^^^^^
Given a general question, this agent generates a Python code to answer the question and generate the required data. This agent is capable of data cleaning, feature engineering, and any complex data-related operations in Python. It can only take data as input and generate data as output.

+--------+-------------------------------+
| Input  | Question                      |
|        +-------------------------------+
|        | Research (optional)           |
|        +-------------------------------+
|        | Plan                          |
|        +-------------------------------+
|        | Data Dictionary               |
|        +-------------------------------+
|        | Input Data Path               |
|        +-------------------------------+
|        | Output Folder Path            |
+--------+-------------------------------+
| Output | Output data (CSV)             |
+--------+-------------------------------+

**Flow**
These 5 activities will be performed for the Python Developer/ Python Modeling agents:

+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``PlanGenerator``           | Generates plan that will be executed by ``PythonCodeGenerator``. This is needed because the manager generates the high-level task description which needs multiple further sub-steps to be performed to successfully perform the task                                                                                                                                                                                                            |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``DataDictionaryGenerator`` | Uses ``DataDictionaryUtils`` to add new keys in the data dictionary [num_unique, top_most_occurring_values, num_missing_values, descriptive_statistics (mean, median, mode)] . If any new columns are generated by previous tasks, we update the data dictionary of those columns alone in this. If the columns are used as it is from the input table, their corresponding descriptions are also taken as it is from the data dictionary.       |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``PythonCodeGenerator``     | Generates the code, and executes it by ``CodeUtils``.                                                                                                                                                                                                                                                                                                                                                                                            |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``PythonCodeCorrector``     | Corrects the code, if any error is encountered. The original code that is generated in the previous step and the error message is passed to the LLM call for getting the updated and corrected code                                                                                                                                                                                                                                              |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``DataDictionaryGenerator`` | Creates a new data dictionary for newly generated columns. If the previous steps create any new columns or rename any columns, the data dictionary is updated for those columns alone.                                                                                                                                                                                                                                                           |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

For Example, for the input Question, ``Perform feature correlation analysis between "efficiency" and all other numerical features in the dataset to identify potential key drivers``, the output will be:

====================== ============
feature                correlation
====================== ============
on_time_shipment        0.797564499
on_time_shipment_norm   0.797564499
on_time_in_full         0.447146548
on_time_in_full_norm    0.447146548
turn_around_norm        0.294738949
fill_rate_norm          0.236199741
fill_rate               0.236025247
velocity                0.229215039
velocity_norm           0.228675473
turn_around             -0.29681409
====================== ============

Python Modelling Agent
^^^^^^^^^^^^^^^^^^^^^^
This agent is capable of building machine learning and deep learning models using Python. This agent takes processed data from the :meth:`DataProcessorSQLAgent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>` or :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and the question as input to generate a complex modeling code to answer the question and thereby generate model and predictions as output.

Below are the inputs required for this agent:

+--------+-------------------------------+
| Input  | Question                      |
|        +-------------------------------+
|        | Research (optional)           |
|        +-------------------------------+
|        | Plan                          |
|        +-------------------------------+
|        | Data Dictionary               |
|        +-------------------------------+
|        | Input Data Path               |
|        +-------------------------------+
|        | Output Folder Path            |
+--------+-------------------------------+
| Output | Model object (PKL)            |
|        +-------------------------------+
|        | Intermediate output (CSV)     |
|        +-------------------------------+
|        | Test prediction (CSV)         |
|        +-------------------------------+
|        | Correlation matrix (CSV)      |
+--------+-------------------------------+


**Flow**
These activities listed below will be performed to complete the tasks assigned to Python Developer/ Python modeling agents:

+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``PlanGenerator``           | Generates plan that will be executed by ``PythonCodeGenerator``. This is needed because the manager generates the high-level task description which needs multiple further sub-steps to be performed to successfully perform the task                                                                                                                                                                                                            |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``DataDictionaryGenerator`` | Uses ``DataDictionaryUtils`` to add new keys in the data dictionary [num_unique, top_most_occurring_values, num_missing_values, descriptive_statistics (mean, median, mode)] . If any new columns are generated by previous tasks, we update the data dictionary of those columns alone in this. If the columns are used as it is from the input table, their corresponding descriptions are also taken as it is from the data dictionary.       |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``PythonCodeGenerator``     | Generates the code, and executes it by ``CodeUtils``.                                                                                                                                                                                                                                                                                                                                                                                            |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``PythonCodeCorrector``     | Corrects the code, if any error is encountered. The original code that is generated in the previous step and the error message is passed to the LLM call for getting the updated and corrected code                                                                                                                                                                                                                                              |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``DataDictionaryGenerator`` | Creates a new data dictionary for newly generated columns. If the previous steps create any new columns or rename any columns, the data dictionary is updated for those columns alone.                                                                                                                                                                                                                                                           |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

For Example, for the input Question, ``Build a regression model with \"efficiency\" as the target variable and all other numerical features as predictors. Use the model to identify the most important features driving \"efficiency\".``, the output will be:

.. code-block:: text
    :linenos:

    R-squared score: 0.9986222634513674
    Mean absolute error: 0.002815328515907459
    Mean squared error: 1.0610120782181784e-05

=====================  ===========
Feature importance     Coefficient
=====================  ===========
fill_rate_norm         0.032137
on_time_shipment       0.029450
on_time_shipment_norm  0.029450
velocity               0.025274
turn_around            0.020899
on_time_in_full        0.019587
on_time_in_full_norm   0.019587
fill_rate              0.012390
turn_around_norm       0.003033
velocity_norm          0.000605
=====================  ===========

The most important features driving efficiency are:
``['fill_rate_norm', 'on_time_shipment', 'on_time_shipment_norm', 'velocity', 'turn_around', 'on_time_in_full', 'on_time_in_full_norm', 'fill_rate', 'turn_around_norm', 'velocity_norm']``

The model has an R-squared score of 0.9986222634513674 which means that 99.86 % of the variance in efficiency can be explained by the model.
The mean absolute error of the model is 0.0 and the mean squared error of the model is 0.0.

Autogen Modelling Agent
^^^^^^^^^^^^^^^^^^^^^^^
This agent is capable of building machine learning and deep learning models using Python. This agent takes processed data from the :meth:`DataProcessorSQLAgent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>` or :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and the question as input to generate a complex modeling code to answer the question and thereby generate model and predictions as output.

.. Note:: This agent is based on the Autogen framework that enables the development of LLM applications using multiple agents that can converse with each other to solve tasks. AutoGen agents are customizable, conversable, and seamlessly allow human participation. They can operate in various modes that employ combinations of LLMs, human inputs, and tools.

+--------+-------------------------------+
| Input  | Question                      |
|        +-------------------------------+
|        | Data Dictionary               |
|        +-------------------------------+
|        | Input Data Path               |
|        +-------------------------------+
|        | Output Folder Path            |
+--------+-------------------------------+
| Output | Model object (PKL)            |
|        +-------------------------------+
|        | Intermediate output (CSV)     |
|        +-------------------------------+
|        | Test prediction (CSV)         |
+--------+-------------------------------+


Summarizer Agent
^^^^^^^^^^^^^^^^
This agent takes the results of all the tasks successfully executed from :ref:`autonomous-agents-tools-docs-ref` and generates a summary for the given question.

+--------+---------------------------------+
| Input  | Question                        |
|        +---------------------------------+
|        | Result list (All Agent outputs) |
+--------+---------------------------------+
| Output | Text Summary                    |
+--------+---------------------------------+

**Example Summarizer output**

.. code-block:: yaml
    :linenos:

    {
        - To improve the efficiency of Location 22, we need to focus on the top 5 features driving efficiency which are velocity, turn_around_norm, fill_rate, turn_around, and on_time_shipment. These features were identified using a regression model built for Location 22 with "efficiency" as the target variable and all other numerical features as predictors. The model has a mean absolute error of 0.04 and an R-squared value of 0.89, indicating that the model can explain 89.27% of the variance in the target variable. The most important feature driving efficiency is the velocity with a coefficient of 0.02.

        - We can also generate insights about the key drivers of the efficiency of Location 22 based on the correlation analysis. The top three features highly correlated with efficiency are 'on_time_shipment', 'on_time_shipment_norm', and 'on_time_in_full', with correlation values of 0.7975644985699883, 0.7975644985699883, and 0.4471465475464717 respectively. The majority of correlation values (50% to 75%) fall within the range of 0.2654693452454858 to 0.4471465475464717, indicating these features are key drivers of efficiency.

        - Therefore, to improve the efficiency of Location 22, we should focus on improving the velocity, turn_around_norm, fill_rate, turn_around, and on_time_shipment.
    }

RAG Agent
^^^^^^^^^
The RAG Agent is capable of answering queries based on a pool of documents. It is capable of extracting data from unstructured documents such as `pdf` or `txt`. It does this by first retrieving a list of documents using the Vector Database Tool. The summary is then generated using the Retrieval Augmented Generation Task.

+--------+---------------------------------------------+
| Input  | Question                                    |
|        +---------------------------------------------+
|        | Data folder path (having pdf and txt files) |
+--------+---------------------------------------------+
| Output | Response to the question                    |
+--------+---------------------------------------------+

.. _autonomous-agents-actions-docs-ref:

Actions
-------
Actions are used by agents to get a response. Each agent will be performing a certain action to deliver the result. For example, the :meth:`ManagerAgent <autonomous_agents.agents.ManagerAgent>` will perform an action named :meth:`TaskListGenerator <autonomous_agents.actions.TaskListGenerator>`, to generate the task list, it will also use :meth:`ActionBase <autonomous_agents.actions.ActionBase>` to perform the reflection on the task list. All the actions use 1 or more LLM calls.

currently, we have the following Actions:

task_list_generation
^^^^^^^^^^^^^^^^^^^^
This action is used for the Manager Agent. It takes a question, data dictionary, and available agent details as input, it generates a task list in 3 steps.

#. ``task_list_generation`` - It generates a task list with ``task_id``, ``agent_name`` and ``task_description``.
#. ``assign_input_dependency`` - The response from step 1 goes to step 2 where all the ``task_id`` are assigned with ``input_task_id``.
#. ``reflection`` - The response from step 2 goes to step 3 where it performs a reflection. It checks for redundancy and the format of the final ``task_list``.

plan_generation
^^^^^^^^^^^^^^^
This action is used for :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>`. It takes a question and a data dictionary from the agent as input and creates a plan ensuring the agent executes the given task appropriately.

- :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` - The action generates a plan that looks into all the granular problems that could occur while generating a Python code. It specifies that these problems should be avoided while generating the Python code and the final goal of the plan would be to generate and save a dataframe that can be used to answer the question.
- :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>` - The action generates a plan that directs the LLM to generate the proper model. The plan would cover key aspects of a model-building process such as train test split, hyperparameter tuning, model selection, and metrics evaluation.

summary_generation
^^^^^^^^^^^^^^^^^^
This action is used for :meth:`SummarizerAgent <autonomous_agents.agents.SummarizerAgent>`. It takes the question, ``task_result``, and the ``task_list`` as input to summarize the result into simple text. This makes the raw data more readable.

python_code_generation
^^^^^^^^^^^^^^^^^^^^^^
This action is used for :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>`. It takes a question, plan, data dictionary, and data as input and generates Python code.

- :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` - The action generates a Python code that solves the problem that is passed to it. It mentions all the problems that may occur while generating a code, and what shall be done if those problems are encountered.
- :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>` - The action generates a Python code that performs various modeling tasks as mentioned in the plan that is created by :meth:`PlanGenerator <autonomous_agents.actions.PlanGenerator>`. It instructs the LLM such that the probability of getting an incorrect response is minimized.

python_code_correction
^^^^^^^^^^^^^^^^^^^^^^
This action is used for :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>`. Once the Python code is generated by :meth:`PythonCodeGenerator <autonomous_agents.actions.PythonCodeGenerator>`, if any error occurs while running the code, this action will be called.  It takes the code with an error message, debugs the code, and returns an error-free code.

You can find an example `Here <url_autonomous_agents_16_>`_.

The example shows a run for :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>`. You can find the subtask for modeling in **sub_task_description.txt**. The folder **PythonCodeGenerator** has the generated code, **code_error.txt** file stores the error that was encountered. The folder **PythonCodeCorrector** stores the corrected code in **python_code.py** and the output generated by the code is stored in folder **2**.

data_dictionary_generator
^^^^^^^^^^^^^^^^^^^^^^^^^
This action is used for :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>`. It takes a data dictionary, Python code, and a small sample of the data generated by the code to return a data dictionary with the column name and description of the new columns that are formed while executing the code. This action only takes place if there are any new columns formed.

action_base
^^^^^^^^^^^
this is the base class for all the Actions to interact with each other and the agents, all the base tasks are orchestrated from this class.

retrieval_augmented_generation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This action is used to generate a summary of a document using a Vector Database Tool. The summary is generated by first retrieving a list of documents using the Vector Database Tool. The summary is then generated using the OpenAI LLM call using the query, list of documents, and prompts in the config.

.. _autonomous-agents-shared-memory-docs-ref:

Shared Memory
--------------
Shared memory is designed to create an agent conversation and update the task list based on the conversation. The conversation will have the subgoal and details of outputs of each task executed till it is called. :meth:`Shared Memory <autonomous_agents.shared_memory.SharedMemory>` is called every time a task in the ``task_list`` is executed. If there is any error encountered during the execution of a particular task, shared memory changes the subsequent tasks in the ``task_list``. It will make sure that the failed task is not repeated in the ``updated_task_list``.

The following changes can be made in the ``task_list``:

#. It can change or rephrase the task description.
#. If a task fails and any of the subsequent tasks are dependent on the failed task, shared memory can change the ``input_task_id`` for the subsequent tasks.
#. If the ``input_task_id`` is assigned incorrectly, it will reassign it.

For Example, if Plotly agent output is taken as input for another task,

Shared memory utilizes ``vector_database`` to store the results of the tasks. This is done to open the prospect of searching and retrieving any relevant task results in the future. Below is the list of agents and the outputs that are stored for the respective agents.

+----------------------------------------------------------------------------------------------------+------------------------------------------------+
| :meth:`Manager agent <autonomous_agents.agents.ManagerAgent>`                                      | task_list, subgoal                             |
+----------------------------------------------------------------------------------------------------+------------------------------------------------+
| :meth:`SQL data processor agent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>`     | agent_description, sub_task, status,response.  |
+----------------------------------------------------------------------------------------------------+------------------------------------------------+
| :meth:`Plotly chart generator agent <autonomous_agents.insights_pro_agents.PlotlyVisualizerAgent>` | agent_description, sub_task, status, response. |
+----------------------------------------------------------------------------------------------------+------------------------------------------------+
| :meth:`Insights generator agent <autonomous_agents.insights_pro_agents.InsightsGeneratorAgent>`    | agent_description, sub_task, status, response. |
+----------------------------------------------------------------------------------------------------+------------------------------------------------+
| :meth:`Python developer agent <autonomous_agents.agents.PythonDataAgent>`                          | agent_description, sub_task, status.           |
+----------------------------------------------------------------------------------------------------+------------------------------------------------+
| :meth:`Python modelling agent <autonomous_agents.agents.PythonModellingAgent>`                     | agent_description, sub_task, status.           |
+----------------------------------------------------------------------------------------------------+------------------------------------------------+

+--------+---------------------------------------------+
| Input  | Task list (generated by Manager Agent)      |
|        +---------------------------------------------+
|        | Agent Conversation                          |
+--------+---------------------------------------------+
| Output | Updated task list                           |
+--------+---------------------------------------------+

For the input question, ```How does the on-road time affect the efficiency of a carrier?```, the original task list is:

.. code-block:: yaml
    :linenos:

    {

        [
            {   "task_id": 0,
                "name": "DataProcessorSQLAgent",
                "description": "Extract the \"on_road_time\" and \"efficiency\" columns from the \"carrier_metrics_monthly\" table in the database.",
                "data_dependency": null},
            {   "task_id": 1,
                "name": "PythonDataAgent",
                "description": "Calculate the correlation between \"on_road_time\" and \"efficiency\".",
                "data_dependency": 0 },
            {   "task_id": 2,
                "name": "PlotlyVisualizerAgent",
                "description": "Generate a scatter plot with \"on_road_time\" on the x-axis and \"efficiency\" on the y-axis to visualize the relationship between these two variables.",
                "data_dependency": 1},
            {   "task_id": 3,
                "name": "InsightsGeneratorAgent",
                "description": "Generate insights on how \"on_road_time\" affects the \"efficiency\" of a carrier based on the correlation and the scatter plot.",
                "data_dependency": 1}
        ]
    }

which gets updated to:

.. code-block:: yaml
    :linenos:

    {
        Updated Task List -

        [
            {   "task_id": 0,
                "name": "DataProcessorSQLAgent",
                "description": "Extract the \"on_road_time\" and \"efficiency\" columns from the \"carrier_metrics_monthly\" table in the database.",
                "data_dependency": null},
            {   "task_id": 1,
                "name": "PythonDataAgent",
                "description": "Calculate the correlation between \"on_road_time\" and \"efficiency\".",
                "data_dependency": 0},
            {   "task_id": 2,
                "name": "PlotlyVisualizerAgent",
                "description": "Generate a scatter plot with \"on_road_time\" on the x-axis and \"efficiency\" on the y-axis to visualize the relationship between these two variables.",
                "data_dependency": 1},
            {   "task_id": 3,
                "name": "InsightsGeneratorAgent",
                "description": "Generate insights on how \"on_road_time\" affects the \"efficiency\" of a carrier based on the correlation and the scatter plot.",
                "data_dependency": 0}
        ]

    }

Explanation - The ``data_dependency`` of ``task_id`` 3 was changed. while the tasks were being executed the plotly had failed with ``data_dependency`` on ``PythonDataAgent``. So for the next task execution, shared memory updated the ``data_dependency`` of ``task_id: 3`` to ``DataProcessorSQLAgent``

.. _autonomous-agents-tools-docs-ref:

Tools
-----
Tools are used to support the process and assist the agents in performing the tasks assigned to them. For example, if any query is generated by the :meth:`DataProcessorSQLAgent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>`, and it has created some columns. The :meth:`DataDictionaryUtils <autonomous_agents.tools.DataDictionaryUtils>` tool will add new columns to the latest data dictionary generated for the output.

The following tools are available in the current version of Autonomous Agents:

SummarizerUtils
^^^^^^^^^^^^^^^
This tool collates the results of the tasks that are executed successfully into a list of dictionaries. Thereby the generated list is used by the :meth:`SummarizerAgent <autonomous_agents.agents.SummarizerAgent>`.

Below are the keys of the dictionary passed to the summarizer agent:

+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| **Agent**                                                                                          | **Keys of Data Dictionary**                                                                                        |
+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| :meth:`SQL data processor agent <autonomous_agents.insights_pro_agents.DataProcessorSQLAgent>`     | output_type, data_dictionary, task_description, agent_name, agent_description, result_status, data_used.           |
+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| :meth:`Plotly chart generator agent <autonomous_agents.insights_pro_agents.PlotlyVisualizerAgent>` | output_type, task_description, agent_name, agent_description, result_status, data_used.                            |
+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| :meth:`Insights generator agent <autonomous_agents.insights_pro_agents.InsightsGeneratorAgent>`    | output_type, insights, task_description, agent_name, agent_description, result_status,data_used.                   |
+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| :meth:`Python developer agent <autonomous_agents.agents.PythonDataAgent>`                          | output_type, insights, data_dictionary, task_description, agent_name, agent_description, result_status, data_used. |
+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| :meth:`Python modelling agent <autonomous_agents.agents.PythonModellingAgent>`                     | output_type, insights, task_description, agent_name, agent_description, result_status, data_used.                  |
+----------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------+

DataDictionaryUtils
^^^^^^^^^^^^^^^^^^^
As mentioned in the above example whenever there are any changes in the code data dictionary, this tool will update the output data dictionary. This tool will add the newly created columns and remove the columns which are not used in that particular scenario, by doing this we manage to keep the output as relevant as possible.

CodeUtils
^^^^^^^^^
This tool contains the class :meth:`CodeUtils <autonomous_agents.tools.CodeUtils>`. This is an A utility class for running code snippets in various languages. It has various methods to execute a code written in Python language or any other language mentioned in the input. The tool is used by all the agents that may require any code execution.

VectorDatabase
^^^^^^^^^^^^^^
This tool is used to create and search a vector database. The tool uses Chroma-db from the langchain vector store. The vector database is created using a given embedding and chunking strategy. The vector database is searched using a given retrieval strategy. The vector database tool can detect changes to the files in the database and update the database accordingly.
