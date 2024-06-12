.. include:: ../../links.rst
.. _autonomous-agents-usage-ref:

Usage
+++++

Understand the source code
==========================

Please check the introduction, code walkthrough, and KT of the **Autonomous Agents** source code `here <url_autonomous_agents_20_>`_.

.. _autonomous-agents-data-folders-ref:

Setting up the Input Data Folders
=================================

Autonomous agents can accept inputs in various formats based on the use case. This can include SQL databases, CSV files, or unstructured data such as text ( PDFs, PPTs, etc.).

Below is the structure of the data folder:
`Click here <url_autonomous_agents_01_>`_ to download the sample data.

Prepare a folder with your domain name and create the following sub-folders (please make sure that the folder names are exactly as added below). You can find the sample folder here.

   - ``data_dictionary``: Add all data dictionary JSON files created in the previous steps in this folder
   - ``data_glossary``: Add the data glossary TXT files in this folder.
   - ``db``: Add the db file created in the previous steps in this folder. Note that, this db file is not required when using an external database (such as MySQL, Snowflake, etc.).
   - ``output_folder``: Output folder where the outputs will be saved. You can leave this empty.


.. code-block:: text
    :linenos:

    Project folder
        |- db
            |- SQL database .db file (or) CSVs
        |- data_dictionary
            |- data dictionary JSON of the tables
        |- data_glossary
            |- unstructured text data
        |- output_folder



Update the backend data
-----------------------

Get the data and the data dictionary from the client and mask the data, if needed. Rename the CSV data files to the table names that you want to appear in the SQL queries (don't add any client names/ information in the table names).

If the client doesn't have the data dictionary, then prepare one (Reference). Each table should have one data dictionary with the following keys (please make sure that the column names are exactly as added below).

  - ``table_name``:  Make sure the table name is mentioned correctly.
  - ``columns``: The value for this key is a list of n dictionaries where n is the number of columns in the table. The key-value pairs for these dictionaries are mentioned below
  - ``column_name``: Column name
  - ``column_description``: Description of the column

The below keys are not mandatory but it's good to have them.

  - ``id``: Boolean indicating if the column is an ID column. You can leave this blank if the column isn't an ID column and mark it as ``"Yes"`` only for the ID columns
  - ``unique values``: Leave this column blank or mention all the unique values. The above notebook will create unique values for some of the columns based on some heuristic logic. Please check the outputs and also make necessary changes before using this column
  - ``units of measurement``: For example, if a column has distance data, mention if it is km or meters or any other unit of measure. Leave it blank if it is not relevant

You can add any other columns that you think are relevant and non-blank values will be added as it is to the prompt. Please consider that the models have token limits and will not work if we add more and more data to the prompt.

**Example for Data Dictionary**

.. code-block:: yaml
    :linenos:

    {
    "table_name": "Employee_details",
    "columns": [
        {
            "name": "EmployeeID",
            "description": "Unique identifier for each employee",
            "id": "Yes"
        },
        {
            "name": "FirstName",
            "description": "First name of the employee"
        },
        {
            "name": "LastName",
            "description": "Last name of the employee"
        },
        {
            "name": "Salary",
            "description": "Employee's salary (must be a positive value)"
        }
        {
            "name": "DateJoined",
            "description": "Date when the employee joined the company"
        }
        {
            "name": "Department",
            "description": "Employee's department (maximum length of 50 characters)."
        }
    ]
    }

Instructions for preparing the data dictionary
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please refer to `this document <url_autonomous_agents_06_>`_ for detailed instructions on setting up the data and preparing a data dictionary.

A notebook for creating the data dictionary JSON files in the required formats from the cvs can be found `here <url_autonomous_agents_09_>`_. The notebook also adds additional columns like unique values to the data dictionary.

You can also create a CSV file and convert it into a JSON file. The instructions are given further below on how to do it. The instructions for columns of this CSV file are the same as mentioned below 'columns'.

  #. Column description should be accurate and relevant in the context of the dataset.
  #. In case of a column having values like ``1`` or ``0`` or ``True`` or ``False``, describe what each of them means in the context of the data.
  #. For columns with ordinal data, mention the order of importance. For example - column name: priority, column description: Priority is between (1 (Highest) to 5 (Lowest)); Each Incident has a priority.
  #. In case there is an abbreviated version of a term in the column name, it is recommended to write the full form of that term in the column description. For example - *column name*: made_sla, *column description*: There is a service level Agreement for each priority by when this needs to be resolved; this column helps to know if the SLA was Met or not.
  #. Mask the columns that have sensitive information like client names, account names or numbers, etc.
  #. Convert the dataset to a database file. You can use this code to do the same.
  #. Convert the data dictionaries to JSON formats that can be consumed by the Insights Pro. You can use this code to do the same.
  #. Prepare a data glossary containing any additional information that you want to feed to the LLM while getting the answers (Ex: KPI measurement definitions etc) in TXT format (Reference).

Instructions for preparing the data glossary
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We can create and add a Data glossary file that contains business and KPI information. This information will be passed as a context to the LLM to assist in getting results that are aligned with the business expectations. This file may contain any business-specific abbreviations, formulas, KPI definitions for the business, or understandings of the data.

An example data glossary file for a Supply chain dataset is added `here <url_autonomous_agents_07_>`_.


Config setup
============

There are a total of 6 config files. Four of them are for InsightsPro, and the remaining two are for Autonomous Agents.

+---------------------------+------------------------------------+
| InsightsPro configs       | ``user_config.yaml``               |
|                           +------------------------------------+
|                           | ``data_config.yaml``               |
|                           +------------------------------------+
|                           | ``model_config.yaml``              |
|                           +------------------------------------+
|                           | ``debug_config.yaml``              |
+---------------------------+------------------------------------+
| Autonomous Agents configs | ``agents_description_config.yaml`` |
|                           +------------------------------------+
|                           | ``agents_prompt_config.yaml``      |
+---------------------------+------------------------------------+


Refer to `this link <url_autonomous_agents_04_>`_ to get sample configs. The next section covers *Autonomous Agents* configs. For details of Insights_pro configs refer to :ref:`insights-pro-code-walkthrough-sql-generator-ref` in insights pro documentation and :ref:`data-config-setup-ref` .

Agents Description Config
-------------------------

This config is used to list the available agents that can perform tasks. It contains ``name``, ``description``, ``allowed_inputs`` and ``returned_outputs``. Users can also enable or disable the agents from this config with the help of the ``enabled`` variable.

There are 2 lists of agents.

#. ``available_agent_manager`` - This list of agents will be used by the :meth:`ManagerAgent <autonomous_agents.agents.ManagerAgent>` to assign the sub-tasks.
#. ``available_agents_orchestrator`` - This list of agents will be used by the orchestrator to get the answer to the question asked by the user.

Below is an example for ``available_agent_manager``.

.. code-block:: yaml
  :linenos:

  [
    {
      name: PythonDataAgent,
      enabled: true,
      description: "Given a general task question this agent generates a Python code to answer the question and generate required data. It is capable of data cleaning, feature engineering, and any complex data-related operations. It can ONLY take data as input and generate data as output.",
      allowed_inputs: ["data-csv"],
      returned_outputs: ["data-csv"],
    },
    {
      name: DataProcessorSQLAgent,
      enabled: true,
      description: "Given a general task question this agent generates a complex SQL query to answer the question and generate required data. It can ONLY take data as input and generate data as output.",
      allowed_inputs: ["data-csv", "data-sql"],
      returned_outputs: ["data-csv"],
    },
    {
      name: PlotlyVisualizerAgent,
      enabled: true,
      description: "This agent ONLY takes in processed data from DataProcessorSQLAgent agent or PythonDataAgent and questions as context to generate plotly visualizations. It can ONLY take data as input and generate plots as output.",
      allowed_inputs: ["data-csv"],
      returned_outputs: ["chart"],
    },
    {
      name: InsightsGeneratorAgent,
      enabled: true,
      description: "This agent ONLY takes in processed data from DataProcessorSQLAgent agent or PythonDataAgent and question as context to generate insights to answer the given question. It can ONLY take in data as input and generate insights as output.",
      allowed_inputs: ["data-csv"],
      returned_outputs: ["insights"],
    },
    {
      name: PythonModellingAgent,
      enabled: false,
      description: "This agent utilizes processed data from the data_processor_sql or PythonAgent and question as context, to build machine learning or deep learning models in Python. It can ONLY take data as input and generate model, predictions as output.",
      allowed_inputs: ["data-csv"],
      returned_outputs: ["model", "data-csv"],
    },
    {
      name: "AutogenModelingAgent",
      enabled: false,
      description: "This agent utilizes processed data from the data_processor_sql or PythonAgent and question as context to build machine learning or deep learning models in Python. It can ONLY take data as input and generate model, predictions as output.",
      allowed_inputs: ["data-csv"],
      returned_outputs: ["model", "data-csv"],
    },
  ]


Below is an example for ``available_agents_orchestrator``.

.. code-block:: yaml
    :linenos:

    [
      {
        name: "ManagerAgent",
        enabled: true,
        description: "This agent serves as a manager, coordinating and overseeing the activities of other agents in the system."
      },
      {
        name: RAGAgent,
        enabled: true,
        description: "This agent takes on the task of retrieving data from unstructured documents (policy or legal documents) and generating insights to answer the given question.",
      },
      {
        name: "SummarizerAgent",
        enabled: true,
        description: "This agent specializes in summarizing information, condensing lengthy content to provide concise and informative summaries."
      }
    ]

To add a new agent, the agent details must be added to this list.

Agents Prompt Config
--------------------

This config is similar to the model config used in *InsightsPro*. It includes details about model parameters and prompt templates. These details include prompts for all available agents specified in the ``agents_description_config.yaml`` file. Additionally, it also includes prompts utilized by the :meth:`ManagerAgent <autonomous_agents.agents.ManagerAgent>` (for task breakdown, reflection, etc.) and the :meth:`SummarizerAgent <autonomous_agents.agents.SummarizerAgent>`. Each agent may have more than one LLM call, and all the prompts should be incorporated into this config file.

Following is an example of :meth:`PythonCodeGenerator <autonomous_agents.actions.PythonCodeGenerator>` agent:

.. code-block:: yaml
    :linenos:

    PythonDataAgent:
      static_prompt: |
        You are an expert Python developer and data scientist who excels in writing efficient, elegant, and coherent working code to solve data science and Python problems using the data provided.

        Your task is to ONLY write Python code to solve the problem such that new data is returned.

        You will be given a data dictionary and path to a CSV file for which you need to write Python code to answer the question.
        You may also be given additional context in the form of research titled "Research" and a plan titled "Plan". Ignore if not provided. You may use this to answer the question ONLY if it's relevant. Else ignore.

        Remember to properly format code using backticks as follows.
        For code ALWAYS use
        ```python
        ```

        The resulting output of the code SHOULD always be new data.

        Question:
        {question}

        Research:
        {web_research}

        Plan:
        {plan}

        Data Dictionary:
        {data_dictionary}

        Data Path: {data_path}
        ALWAYS use whatever data path is provided above to load the data.

        Remember to follow the below scenario of outputs always when generating code:
        1. When performing operations on the data, the code should ALWAYS save the output DataFrame to a CSV file as {output_path}/data_output.csv

        Follow the below Guidelines when generating code:
        1. The response should ALWAYS contain a code block and output type block.
        2. Avoid mere repetition of historical code. Always aim to generate novel and appropriate responses to the questions at hand.

        ...

        1.   Never have unnamed columns in the DataFrame. When using the pivot function or groupby or when manually creating new columns, make sure the names are verbose and meaningful.

.. _data-config-setup-ref:

Data Folder and Configuration Setup
-----------------------------------
#. Data Folder Setup:
    Create a folder named data to store all data-related files in the project folder.
#. Download Zip Folders:
    Download zip folders for each domain and save them in the data folder.
#. Domain Folder Structure:
    Each domain folder should contain the following details:
        * **data_dictionary**: Contains data dictionaries for tables.
        * **data_glossary**: Contains data glossary for domain-specific terms.
        * **db**: Contains database files.
        * **output_folder**: Used for storing output files.
        * **output_folder_test**: Used for storing test output files.
#. Usage in Data Configuration File:
    #. ``input_path``: Either Use the ``data_path`` and ``data_dictionary_path`` if a single data table is required to answer the user question or use the ``sql_data_path`` and ``data_dictionary_sql_path`` if more than one data tables are required to answer the user question. Do not use ``data_path``, ``data_dictionary_path`` and ``sql_data_path``, ``data_dictionary_sql_path`` at the same time.
            * ``data_path``: Path for **single data table** as an input.
            * ``data_dictionary_path``: Path for **single data Dictionary** as an input.
            * ``sql_data_path``: Path for ``database.db`` that contains more than 1 data tables.
            * ``data_dictionary_sql_path``: Path for ``data_dictionary`` folder that contains multiple data dictionaries.
            * ``document_path``: Path for the input document (txt/pdf/docs etc) (unstructured data).
            * ``glossary_terms_path``: Path for ``glossary_terms.csv``, that contains glossary.
    #. ``context``
            * ``additional_context``: Additional context for agents
            * ``summary_context``: Context to be given for summarizing to answer the user question
    #. ``other``
            * ``reflect``: True/False: Whether to have an extra LLM call for reflection on the generated task_list
            * ``force_insights_for_data``: True/False: Whether to force insights agent for the data output
            * ``use_shared_memory``: True/False: Whether to store the task list and its corresponding output/errors to the vectorDB
            * ``task_update``: True/False: Whether to update the task list based on the previous task results.
            * ``manual_task_list``:  Provide manual task list ``list(dict)``
    #. ``path``
            * ``input_data_path``: Path where the input data, db files, and output folder (will be created in the code) are saved
            * ``exclude_table_names``: Table names that need to be excluded
            * ``data_dictionary_path``: Path where the data dictionaries are available (one JSON file per one table mentioned in the path.input_file_name section of this config)
            * ``business_overview_path``:  Path to the txt file containing the business overview.
            * ``api_key_location``:  Path where the API key is stored. This will be added as a temporary environment variable in the code
            * ``output_path``: Output path where results will be saved
            * ``exp_name``: Experiment name. A subfolder inside output_path will be created with this name. All results of runs will be saved inside ``output_path/exp_name``
    #. ``db_params``
            * ``db_name``: Database name (supports MySQL and SQLite).
            * ``host``: Hostname.
            * ``username``: Username.
            * ``password_path``: Path where the database connection password is stored (valid for MySQL).
            * ``sqlite_database_path``: Path where the database file for SQLite is stored (can be created using a notebook in project support codes).
    #. ``cloud_storage``: Define connection parameters for the cloud storage.
            * ``platform``: Platform of the cloud. Can be blank (for local FS) or "azure".
            * ``prefix_url``: Azure Blob Storage prefix (typically "abfs://")
            * ``DefaultEndpointsProtocol``: Indicate whether you want to connect to the storage account through HTTPS or HTTP
            * ``account_key_path``:  Path where the Account Key is stored.
            * ``AccountName``: Path in the local FS where the Account Name is stored.
            * ``EndpointSuffix``: Used for establishing the connection.

How to Run
==========

This section contains steps on how to run the existing or default set-up of Autonomous agents. Once the Data is placed in the right folders, the config files are updated, and the environment is set up, the following code snippets can be run to initialize and execute the agents.

There are two ways to run the application as listed below.

#. Initialize and run required agents individually. `Please click here to check an example Notebook <url_autonomous_agents_02_>`_
#. Execute all the agents by orchestrating a flow. `Please click here to check an example Notebook <url_autonomous_agents_03_>`_


Run required agents individually
--------------------------------

Import and initialize individual agents
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Import the required Agents

   .. code-block:: python
      :linenos:

      from autonomous_agents.agents import (
            ManagerAgent,
            PythonDataAgent,
            PythonModellingAgent,
            )
      from insights_pro.utils import load_config
      from autonomous_agents.utils import load_data_dictionary, create_logger

#. Then initialize configs and loggers

   .. code-block:: python
      :linenos:

      prompt_config = load_config(os.path.join(CONFIG_PATH, "agents_prompt_config.yaml"))
      agents_config = load_config(os.path.join(CONFIG_PATH, "agents_description_config.yaml"))

      data_dictionary = load_data_dictionary(DATA_DICTIONARY_PATH)
      data_path = os.path.join(DATA_PATH, "db", "data.csv")

      create_logger(
            logger_name=LOGGER_NAME,
            level=DEBUG_LEVEL,
            log_file_path=None,
            verbose=True,
        )


ManagerAgent
^^^^^^^^^^^^^

Generally, the initial step involves converting the user question into multiple sub-tasks. This task is performed by the :meth:`ManagerAgent <autonomous_agents.agents.ManagerAgent>`, which utilizes the agents listed in the ``agents_config`` to assign the sub-tasks to the available agents. The generated task list then undergoes reflection to merge redundant or duplicate sub-tasks. The below code can be used to use :meth:`ManagerAgent <autonomous_agents.agents.ManagerAgent>`

  .. code-block:: python
    :linenos:

    question = "Identify the products that have generally done well at the region level but are continuously underperforming for a few locations."

    manager = ManagerAgent(prompt_config=prompt_config, agents_config=agents_config, reflect=True)
    available_agent_names = ", ".join([agent["name"] for agent in agents_config.available_agents]).strip()

    response = manager.execute(
        available_agent_actions=json.dumps(available_agents_actions, indent=4),
        available_agent_names=available_agent_names,
        data_dictionary=json.dumps(data_dictionary, indent=4),
        data_type="data-csv",
        question=question,
    )

This results in a list of tasks containing, (``task_id``, ``agent``, ``task_description``, ``dependent_task_id``). Below is an example response:

  .. code-block:: yaml
    :linenos:

    [(0,
      'DataProcessorSQLAgent',
      'Create a SQL query to calculate the average ordered amount and cut amount per product per region and location. The result should include columns for product, region, location, average ordered amount, and average cut amount.',
      None),
    (1,
      'PythonDataAgent',
      'Process the result from the SQL query to calculate the difference between the average ordered amount and the average cut amount for each at each location and region. This will give us an indication of how well each product is performing at each location and region.',
      0),
    (2,
      'PythonDataAgent',
      'Identify the products that are performing well at the region level but are underperforming at certain locations. These are the products where the difference between the average ordered amount and the average cut amount is high at the region level but low at certain locations.',
      1),
    (3,
      'PlotlyVisualizerAgent',
      'Create a visualization to show the performance of each product at the region level and each location. The x-axis should be the product, the y-axis should be the difference between the average ordered amount and the average cut amount, and there should be separate lines for each region and location.',
      2),
    (4,
      'InsightsGeneratorAgent',
      'Generate insights from the processed data and visualization to identify the products that are generally doing well at the region level but are continuously underperforming for few locations.',
      2)]


Agents that perform sub-tasks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
All available agents can be initialized and executed similarly. For example, to utilize :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` individually, you can follow the steps below for initialization and execution. Similar procedures can be applied to other available agents. It takes in an input data frame, its data dictionary, and the sub-task.

  .. code-block:: python
    :linenos:

    python_data_agent = PythonDataAgent(prompt_config=prompt_config, agents_config=agents_config, reflect=True)

    question = "Clean and preprocess the data."

    response = python_data_agent.execute(
        data=data,
        data_dictionary=json.dumps(data_dictionary, indent=4),
        question=question,
    )


This agent first generates a step-by-step plan to solve the user question. Then, it generates a Python code as per the plan, which when executed results in a data frame with processed data. Following is an example response:

  **Plan**:

  .. code-block:: text

      1. Load the data into a pandas dataframe.cloud_storage
      2. Check for missing values and handle them appropriately. If there are missing values, consider dropping the rows or filling them with appropriate values.
      3. Check for duplicates and handle them appropriately. If there are duplicates, consider dropping them or aggregating them.
      ...
      n. Save the cleaned and preprocessed dataframe to a new file for further analysis.

  **Code**:

  .. code-block:: python
      :linenos:

      import pandas as pd

      # Load the data into a pandas dataframe
      data_path = "../../bin/_temp/data.csv"
      df = pd.read_csv(data_path)

      # Check for missing values and handle them appropriately
      print("Number of missing values before handling: ", df.isnull().sum().sum())
      df = df.replace("(null)", pd.NA)
      df = df.dropna()
      print("Number of missing values after handling: ", df.isnull().sum().sum())

      # Check for duplicates and handle them appropriately
      print("Number of duplicates before handling: ", df.duplicated().sum())
      df = df.drop_duplicates()
      print("Number of duplicates after handling: ", df.duplicated().sum())

      ...

      print("Output file saved to: ", output_path)

Execute all the agents
----------------------

Import and initialize AutonomousAgents
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Import the required Agents

   .. code-block:: python
      :linenos:

      from autonomous_agents.agents import (
            ManagerAgent,
            PythonDataAgent,
            PythonModellingAgent,
            )
      from insights_pro.utils import load_config
      from autonomous_agents.utils import load_data_dictionary, create_logger

#. Then initialize configs, loggers, and, ``AutonomousAgents``

   .. code-block:: python
      :linenos:

      prompt_config = load_config(os.path.join(CONFIG_PATH, "agents_prompt_config.yaml"))
      agents_config = load_config(os.path.join(CONFIG_PATH, "agents_description_config.yaml"))

      data_dictionary = load_data_dictionary(DATA_DICTIONARY_PATH)
      data_path = os.path.join(DATA_PATH, "db", "data.csv")

      create_logger(
            logger_name=LOGGER_NAME,
            level=DEBUG_LEVEL,
            log_file_path=None,
            verbose=True,
      )

      autonomousAgents = AutonomousAgents(
          prompt_config=prompt_config,
          agents_config=agents_config,
          logging_level=DEBUG_LEVEL,
      )

#. Execute the flow in ``orchestrator.py`` using the below code. This will pass the question to an :meth:`RAGAgent <autonomous_agents.agents.RAGAgent>` to get more context to answer the question. Then, the question along with the additional context is passed to the :meth:`ManagerAgent <autonomous_agents.agents.ManagerAgent>` to break it down into multiple sub-tasks assigned to the available agents, which when executed, generates a solution to all the sub-tasks. Finally, all the responses are then collated and summarized to get a final response to the question by the :meth:`SummarizerAgent <autonomous_agents.agents.SummarizerAgent>`.

   .. code-block:: python
      :linenos:

      result = autonomousAgents.execute_subgoal(
          sub_goal=question,
          output_path=output_path,
          sql_data_path=os.path.join(DATA_PATH, "supply_chain_management", "db", "database.db"),
          data_dictionary_sql_path=os.path.join(DATA_PATH, "supply_chain_management", "data_dictionary"),
          reflect=True,
          use_shared_memory=True,
          task_update=True
      )

.. note::

  To modify the provided architecture, adjustments can be made to the flow within orchestrator.py. These changes should ensure that the solution architecture aligns with the complexity of the use case and the availability of data.


Outputs
=======

Refer to the following `link <url_autonomous_agents_05_>`_ to view sample outputs of each run of Autonomous Agents.

Output Folder Structure
------------------------
Each agent's output will be saved in a separate folder. Common outputs for the run (logger, configs used, etc) are saved in the experiment's main folder itself

.. code-block::
    :linenos:

    Project folder
        |- output_folder
            |- orchestrator output
                |- text_to_query
                |- PythonDataAgent
                |- ManagerAgent
                |- SummarizerAgent
                |- query_to_chart
                |- configs_used
                |- runtime log (txt)
                |- subgoal (txt)
                |- task report (JSON)
                |- Total runtime (txt)

.. _autonomous-agents-add_new-ref:

Adding a new Agent, Action, or a Tool
=====================================

This section is a guide on how to add another Agent, Tool, or Action.

.. note:: These are the paths.

    - Agents - ``src/autonomous_agents/agents``

    - Tools - ``src/autonomous_agents/tools``

    - Actions - ``src/autonomous_agents/actions``

Adding an Agent
---------------
To add an Agent one must look into the following steps:

#. Write the code for the agent with all the necessary methods properly defined.
#. Put the code for agents in the Agents folder, along with all the other agents.
#. Every agent must inherit :meth:`AgentBase <autonomous_agents.agents.AgentBase>` as it acts as an orchestrator between agents, tools, and actions.
#. Every agent must inherit the tools that will be used by the agent to execute tasks.
#. Update ``agents_description_config`` with all the details of the new agent.
#. Update ``agents_incompatible_with_scaler_input_list`` in :meth:`orchestrator <autonomous_agents.AutonomousAgents>` if the new agent is not compatible with scaler input.

  .. Note:: - Summarizer Agent inherits :meth:`SummarizerUtils <autonomous_agents.tools.SummarizerUtils>` as it will only need the ``generate_summary_dict`` tool to fulfill its purpose
      - :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` inherits 2 tools
          - :meth:`CodeUtils <autonomous_agents.tools.CodeUtils>`
          - :meth:`DataDictionaryUtils <autonomous_agents.tools.DataDictionaryUtils>`

#. Every agent must inherit the actions that will be used by the agent to execute tasks.

  .. Note:: - Manager Agent inherits :meth:`TaskListGenerator <autonomous_agents.actions.TaskListGenerator>` as it will only need the ``task_list_generation`` action to fulfill its purpose
      - :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` inherits 4 actions
          - :meth:`DataDictionaryGenerator <autonomous_agents.actions.DataDictionaryGenerator>`
          - :meth:`PlanGenerator <autonomous_agents.actions.PlanGenerator>`
          - :meth:`PythonCodeCorrector <autonomous_agents.actions.PythonCodeCorrector>`
          - :meth:`PythonCodeGenerator <autonomous_agents.actions.PythonCodeGenerator>`

#. The actions and tools must be defined in ``_init_actions`` and ``_init_tools`` respectively.

  .. Note:: The actions and tools will be executed in the exact sequence as mentioned in the ``_init_actions`` and ``_init_tools`` respectively.

#. You can add ``validation_dict``, to the agents which returns a data frame and data dictionary.

Adding an Action
----------------
#. Write the code for the action with all the necessary methods.
#. Put the code for the action in the actions folder, along with all the other actions.
#. Every action must inherit :meth:`ActionBase <autonomous_agents.actions.ActionBase>` as it acts as an orchestrator.
#. Prepare a prompt for the action that you are adding and put that in the ``insights_agents_prompts.yaml`` file. the prompt should preferably be named after the action.
#. Add the prompts for all the agents for which the action will be executed.

  .. Note:: :meth:`PythonCodeGenerator <autonomous_agents.actions.PythonCodeGenerator>` is used for both :meth:`PythonDataAgent <autonomous_agents.agents.PythonDataAgent>` and :meth:`PythonModellingAgent <autonomous_agents.agents.PythonModellingAgent>`, hence there are 2 different prompts given for each agent.

#. Add the import statement for the new action in the ``__init__.py`` file inside the actions folder.
#. Make sure the agent that is using this action has imported it and included it in ``_init_actions``.


Adding a Tool
-------------
#. Write the code for the tool with all the necessary methods.
#. Put the code for the tool in the tools folder, along with all the other tools.
#. For every tool, the class name should include Utils for eg. :meth:`DataDictionaryUtils <autonomous_agents.tools.DataDictionaryUtils>`.


API Framework
=============

The API Framework,built using FastAPI,provides a set of endpoints for accessing the agents of the *Autonomous Agents*. 

Run the API Locally
---------------------------
#. To start the FastAPI server locally using Uvicorn:
  - Navigate to the directory containing "apicode.py" file.
    ```cd api/app```

  - Once you're in the correct directory, use the following command to start the server:
  ```uvicorn apicode:app --reload```

Accessing API Endpoints
-----------------------
#. Determine the URL of the endpoint you want to access by going through the functions of each endpoint in docs.
#. If the endpoint requires any input data, prepare the request payload accordingly.
#. Use an HTTP client library, such as ``requests`` in Python, to send an HTTP request to the endpoint URL. Specify the HTTP method and request body as necessary.

Adding an API endpoint
----------------------
#. Write the code for the endpoint handler function, which defines the functionality of the endpoint. This function should handle incoming requests, process data as needed, and generate appropriate responses.
#. Put the code for the endpoint handler function,in the ``apicode.py`` along with other endpoints.
#. If the endpoint accepts parameters in the request (e.g.,request body), add these parameters in :meth:`Tracks <api.Tracks>` class, including their names, types, and any validation rules.
#. Define the response returned by the endpoint, specifying the data structure, content type (e.g., JSON), and any possible status codes or error messages.

Endpoints 
---------
List Agents :meth:`/ListAgents <api.list_agents>`
^^^^^^^^^^^

The ``/list_agents`` endpoint returns a list of available agents, i.e., agents which are enabled in config for a domain.

**Returns**
* agent_list (list): List containing all the available agents for the given domain.

**Example**
Here is an example of how to use the ``/list_agents`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/list_agents"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)


Manager Agent :meth:`/ManagerAgent <api.manager_agent>`
^^^^^^^^^^^^^
Generate a list of tasks to be executed by other agents.

**Returns**
* ``task_list`` : list
    A list of tasks to be executed for the user's query.

**Example**
Here is an example of how to use the ``/manager_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/manager_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": "Are there any specific source locations that consistently have a low fill rate? If so, what factors contribute to this?",
        "language": "english",
        "data_dictionary_path": "../../data/supply_chain/data_dictionary/warehouse_metrics_monthly.json",
        "output_path": "../../../examp"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_22_>`_ to view sample output of manager agent output.


Orchestrator Agent :meth:`/Orchestrator <api.orchestrator_agent>`
^^^^^^^^^^^^^^^^^^
The ``/Orchestrator`` endpoint executes a subgoal by orchestrating the execution of multiple agents.The agent coordinates the execution of these tasks and returns a comprehensive summary along with various insights.

**Returns**

- ``final_summary`` (str): The final summary of the subgoal.
- ``rag_content`` (str): The content provided by the RAG agent.
- ``web_content`` (str): The content provided from the web.
- ``manager_response`` (dict): The response from the Manager agent.
- ``task_report`` (dict): The task report of each task executed.
- ``task_tracker`` (dict): The task tracker containing results of each task executed.
- ``summarizer_response`` (str): The response from the Summarizer agent.

**Example**
Here is an example of how to use the ``/orchestrator`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/orchestrator"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": "Does on time shipment affect efficiency?",
        "language": "english",
        "additional_context": "None",
        "reflect": True,
        "sql_data_path": "../../data/supply_chain/db/database.db",
        "data_dictionary_sql_path": "../../data/supply_chain/data_dictionary/",
        "manual_task_list": None
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_21_>`_ to view sample output of orchestrator agent output.


Python Data Agent :meth:`/PythonDataAgent <api.python_data_agent>`
^^^^^^^^^^^^^^^^^
The python_data_agent endpoint allows users to execute data-related tasks using Python scripts.

**Returns**
* ``plan`` (str): The plan for solving the user's question.
* ``code_gen`` (str): The generated Python code.
* ``data_dict`` (dict): JSON representation of the output data dictionary.
* ``code_stdout`` (str): Std output generated.
* ``data`` (dict): JSON representation of the output data

**Example**
Here is an example of how to use the ``/python_data_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/python_data_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": 'Calculate the correlation between "on_road_time" and "efficiency" to understand their relationship.',
        "language": "english",
        "data_path": "../../data/supply_chain/db/carrier_metrics_monthly.csv",
        "data_dictionary_path": "../../data/supply_chain/data_dictionary/carrier_metrics_monthly.json"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        # Pretty-print the response JSON data
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        # Print the response data in case of failure
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_23_>`_ to view sample output of python data agent output.

Python Model Agent :meth:`/PythonModelAgent <api.python_model_agent>`
^^^^^^^^^^^^^^^^^^
The python_model_agent endpoint allows users to perform modeling tasks using Python scripts.

**Returns**
* ``plan`` (str): The plan for solving the user's question.
* ``code_gen`` (str): The generated Python code.
* ``data_dict`` (dict): JSON representation of the output data dictionary.
* ``code_stdout`` (str): Std output generated.
* ``data`` (dict): JSON representation of the output data

**Example**
Here is an example of how to use the ``/python_model_agent`` endpoint in Python:

.. code-block:: python 

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/python_model_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": 'Calculate the correlation between "efficiency" and other metrics using a correlation matrix.',
        "language": "english",
        "data_path": "../../data/supply_chain/db/carrier_metrics_monthly.csv",
        "data_dictionary_path": "../../data/supply_chain/data_dictionary/carrier_metrics_monthly.json"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        # Pretty-print the response JSON data
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        # Print the response data in case of failure
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_24_>`_ to view sample output of python model agent output.


SQL Agent :meth:`/SQLAgent <api.sql_agent>`
^^^^^^^^^

The ``/sql_agent`` endpoint allows users to perform data processing tasks using SQL queries.This endpoint returns the SQL query, the output data generated by the query, and an output data dictionary.

**Returns**
* ``query`` (str): The SQL query.
* ``output_data`` (str): Output data generated by the query.
* ``dictionary`` (dict): Output data dictionary.

**Example**
Here is an example of how to use the ``/sql_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/sql_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": 'Extract the "on_road_time" and "efficiency" columns from the "carrier_metrics_monthly" table in the database.',
        "language": "english",
        "data_path": "../../data/supply_chain/db/carrier_metrics_monthly.csv",
        "data_dictionary_path": "../../data/supply_chain/data_dictionary/carrier_metrics_monthly.json"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        # Pretty-print the response JSON data
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        # Print the response data in case of failure
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_25_>`_ to view sample output of sql agent output.


Plot Agent :meth:`/PlotAgent <api.plot_agent>`
^^^^^^^^^^
Generate plots and visualizations.

**Returns**
* ``df`` (pandas.DataFrame) : The data used for chart generation.
* ``chart`` (dict): The generated chart in JSON format.

**Example**
Here is an example of how to use the ``/plot_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/plot_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": "Generate a line plot showing the monthly trend of efficiency for each carrier",
        "language": "english",
        "data_path": "../../data/supply_chain/db/carrier_metrics_monthly.csv",
        "data_dictionary_path": "../../data/supply_chain/data_dictionary/carrier_metrics_monthly.json"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_26_>`_ to view sample output of plot agent output.


Insights Agent :meth:`/InsightsAgent <api.insights_agent>`
^^^^^^^^^^^^^^
Generate insights based on data analysis.

**Returns**
* ``insights`` (dict) : The generated insights.
	
**Example**
Here is an example of how to use the ``/insights_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/insights_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": "Generate insights on the carriers with above and below average on-time shipment rates.",
        "language": "english",
        "data_path": "../../data/supply_chain/db/warehouse_metrics_monthly.csv",
        "data_dictionary_path": "../../data/supply_chain/data_dictionary/warehouse_metrics_monthly.json"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_27_>`_ to view sample output of plot agent output.

Summarizer Agent :meth:`/SummarizerAgent <api.summarizer_agent>`
^^^^^^^^^^^^^^^^

Generate summaries based on input data.

**Returns**
* ``final_summary`` (str): The generated final summary.

**Example**
Here is an example of how to use the ``/summarizer_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/summarizer_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "supply_chain",
        "question": "Efficiency of a location depends on many factors. What factor is more correlated towards efficiency?",
        "language": "english",
        "result_list_path": "../../data/autonomous_agents/output/supply_chain/experiment_folder_new/orchestrator_op_20240528101839_6591/task_report.json"
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_29_>`_ to view sample output of Summarizer agent output.


RAG Agent :meth:`/RAGAgent <api.rag_agent>`
^^^^^^^^^

Execute a Retrieval-Augmented Generation (RAG) agent to answer a user's question.

**Returns**
* ``rag_answer`` (str) : The answer generated for the user query.

**Example**
Here is an example of how to use the ``/rag_agent`` endpoint in Python:

.. code-block:: python

    import requests
    from pprint import pprint

    # Define the URL for the API endpoint
    url = "http://localhost:8000/rag_agent"

    # Create the request body with the necessary parameters
    request_body = {
        "domain_name": "luxury_retailer",
        "document_path": "../../data/luxury_retailer/unstructured",
        "question": "What is the warranty period for omega brand watches and is it international warranty?",
        "num_retries": 2
    }

    # Send a POST request to the specified URL with the request body as JSON
    response = requests.post(url, json=request_body)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful!")
        pprint(response.json())
    else:
        print("Request failed with status code:", response.status_code)
        print("Response data:", response.text)

Refer to the following `link <url_autonomous_agents_28_>`_ to view sample output of rag output.








