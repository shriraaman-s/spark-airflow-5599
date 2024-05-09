import json
import logging
import traceback
import urllib
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, Response

from app.schemas.base import CustomJSONEncoder
from app.schemas.chats import (ChatContext, ChatHistory, ChatReset,
                               CreateOrUpdateChatRequest, FeedbackRequest,
                               GetDataNames, QuesByContextRequest, Tracks, PreTracks, PostTracks,
                               UserCredential, VerifyUser)
from app.schemas.question import QuestionRequest
from app.schemas.report import GenerateReportRequest
from app.services.chat_service import (check_existing_user, create_new_context,
                                       create_new_question, feedback,
                                       get_chat_history_by_chat_id,
                                       get_questions_by_context_id, reset_chat, 
                                       check_user_type_request, db_storage)
from app.services.report_service import generate_report
from app.services.user_service import (create_user_cred, get_user_domains,
                                       validate_user_cred)
from core.database.database_factory import DatabaseFactory
from core.storage.storage_factory import StorageFactory
from core.utils.client_utils import (get_database_client, get_model_type,
                                     get_storage_client)
from core.utils.read_config import (app_database_config, cloud_config,
                                    cloud_secrets, config, initialize_config,
                                    secrets_config)
from src.main import InsightsPro

logging.getLogger().setLevel(logging.INFO)

app = FastAPI(
    title="Insights Pro",
    description="Get insights like a PRO😎",
    summary="This involves Apis within the application aimed at improving user experience through monitoring chat details, user interactions, and storing them in a database.",
    version="0.1",
)


# Instantiating the core clients for database and storage
database_client = get_database_client(database_type=app_database_config.app_db_name)
db_factory = DatabaseFactory(database_client)
storage_obj = StorageFactory(get_storage_client(cloud_config))


@app.post("/create_user")
def create_user(body: UserCredential):
    """
    Creates a user based on provided credentials.

    Args:
        body (UserCredential): UserCredential object containing credentials details.

    Returns:
        json: A message indicating whether credentials were created or not.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(
            app_database_config
        )  # creating the database connection
        logging.info("Connection Established - got connector")

        resp = create_user_cred(
            user_id=body.user_id,
            pwd=body.password,
            usertype=body.usertype,
            domain=body.domain.lower(),
            exp_date=body.exp_date,
            db_conn=conn,
            client=db_factory,
        )

        if resp is None:
            return f"An error occurred while processing the request. "
        result = {"response": resp}
        json_data = json.dumps(
            result, cls=CustomJSONEncoder
        )  # converting the credentials to json and saving them
        logging.info(json_data)
        return json_data
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/verify_user")
def verify_user(body: VerifyUser):
    """
    Verifies a user credential based on provided credentials.

    Args:
        body (VerifyUser): VerifyUser object containing user_id and password.

    Returns:
        json: A message indicating whether authentication was successful or not.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        resp = validate_user_cred(
            user_id=body.user_id, pwd=body.password, db_conn=conn, client=db_factory
        )  # validating the user credentials

        if resp is None:
            return "An error occurred while processing the request."
        result = {"response": resp}
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/get_data_names")
def get_data_names(body: GetDataNames):
    """
    Gives domain names based on user credentials.

    Args:
        body (GetDataNames): GetDataNames object containing user_id.

    Returns:
        json: A list containing domain names for the given credential.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        domains = get_user_domains(
            user_id=body.user_id, db_conn=conn, client=db_factory
        )  # gets the domains associated with the user from database.

        # If user id not in user credentials then take from blobs
        if domains is not None:
            data_names = domains
        else:
            _ = storage_obj.connect_to_storage(
                storage_details=config.cloud_details.data_names_storage,
                connection_keys=secrets_config.cloud_details.data_names_storage,
            )
            data_names = storage_obj.get_folder_name_from_storage()

        if data_names is None:
            return "An error occurred while processing the request."
        result = {"data_names": data_names}
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/chat_initiation")
def chat_initiation(body: CreateOrUpdateChatRequest):
    """
    Initiates a chat session for a given user and domain name.

    Args:
        body (CreateOrUpdateChatRequest): CreateOrUpdateChatRequest object containing user_id and data_name.

    Returns:
        json: A dictionary containing chat details for the given credentials including report list, chat history.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        result = check_existing_user(
            user_id=body.user_id,
            data_name=body.data_name,
            db_conn=conn,
            client=db_factory,
        )  # checking if the user exists in the database or not if not then new chat initiation is done.

        if result is None:
            return "An error occurred while processing the request."
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/chat_context")
def chat_context(body: ChatContext):
    """
    Cretes new context id for given credentials

    Args:
        body (ChatContext): ChatContext object containing user_id, chat_id and domain.

    Returns:
        json: New context id.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        context_id = create_new_context(
            chat_id=body.chat_id,
            user_id=body.user_id,
            data_name=body.domain.lower(),
            db_conn=conn,
            client=db_factory,
        )  # creates the new context if for the new chat session.

        if context_id is None:
            return f"An error occurred while processing the request."
        result = {"context_id": context_id}
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/chat_get_questions_by_context_id")
def chat_get_questions_by_context_id(body: QuesByContextRequest):
    """
    Retrieves the list of questions based on the provide context id.

    Args:
        body (QuesByContextRequest): CreateOrUpdateChatRequest object containing context id.

    Returns:
        json: A list containing questions for given context id.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        result = get_questions_by_context_id(
            context_id=body.context_id, db_conn=conn, client=db_factory
        )  # retrives all the questions associated with the context id.

        if result is None:
            return "An error occurred while processing the request."
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/chat_reset")
def chat_reset(body: ChatReset):
    """
    Resets the chat for the given session.

    Args:
        body (ChatReset): ChatReset object containing user_id and domain.

    Returns:
        json: A dictionary containing new chat details.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        result = reset_chat(
            user_id=body.user_id,
            data_name=body.domain.lower(),
            db_conn=conn,
            client=db_factory,
        )  # creates a new chat session for the user.

        if result is None:
            return "An error occurred while processing the request."
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/chat_history")
def chat_history(body: ChatHistory):
    """
    Retrieves the chat history for the given chat ids and domain name.

    Args:
        body (ChatHistory): ChatHistory object containing chat_ids and domains.

    Returns:
        json: A dictionary containing new chat details.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        result = get_chat_history_by_chat_id(
            chat_ids=body.chat_ids,
            data_names=[body.domains],
            db_conn=conn,
            client=db_factory,
        )

        if result is None:
            return "An error occurred while processing the request."
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/chat_feedback")
def chat_feedback(body: FeedbackRequest):
    """
    Resets the chat for the given session.

    Args:
        body (FeedbackRequest): FeedbackRequest object containing answer_id, status and reason.

    Returns:
        json: Boolean value if the feedback has been submitted.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        result = feedback(
            answer_id=body.answer_id,
            status=body.status,
            reason=body.reason,
            db_conn=conn,
            client=db_factory,
        )  # stores the feedback of user for genereated insights.

        if result is None:
            return f"An error occurred while processing the request."
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


@app.post("/report_generate")
def report_generate(body: GenerateReportRequest):
    """
    Generates the pdf report for current session and uploads the report on blob and resets the active chat.

    Args:
        body (GenerateReportRequest): GenerateReportRequest object containing user_id, data_name and chat_id.

    Returns:
        json: Dictionary with report and new chat details.

    Raises:
        Exception: If the connection to database fails.
    """
    logging.info("FastAPI function processed a request.")

    try:
        logging.info("Establishing DB Connection")
        conn = db_factory.create_database_connection(app_database_config)
        logging.info("Connection Established - got connector")

        report_details = generate_report(
            user_id=body.user_id,
            data_name=body.data_name,
            chat_id=body.chat_id,
            db_conn=conn,
            client=db_factory,
            storage_obj=storage_obj,
        )  # generates the report for the user which contains all the insights generated like table, chat history, etc.

        if report_details is None:
            return f"An error occurred while processing the request."

        new_chat_details = reset_chat(
            user_id=body.user_id,
            data_name=body.data_name.lower(),
            db_conn=conn,
            client=db_factory,
        )  # creates a new chat session for the user.

        if new_chat_details is None:
            return f"An error occurred while processing the request."

        result = {"report": report_details, "new_chat": new_chat_details}
        json_data = json.dumps(result, cls=CustomJSONEncoder)
        logging.info(json_data)

        return json_data

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


# Read config
user_config, data_config, model_config, debug_config = initialize_config(
    domain_name="supply_chain_management"
)


track1_ins = InsightsPro(
    user_config=user_config,
    data_config=data_config,
    model_config=model_config,
    debug_config=debug_config,
)

# Track Dict - To store question and output from track 1
track_dict = {"track1": {"question": [], "output": []}}


# Track - 1
@app.post("/text_to_query")
def text_to_query(body: Tracks):
    """
    Creates API using FastAPI for track 1.

    Args:
        question(str): user_question
        additional_context(str): additional information provided by user
        language(str): language that GPT uses to respond to user
        domain_name(str): domain name

    Returns:
        sql_query(json): contains status, sql, output table and table dictionary
        response_json(json): Response JSON

    """
    track1_output = track1_ins.text_to_query(
        question=body.question,
        language=body.language,
        additional_context=body.additional_context,
    )
    sql_query = track1_output[0]
    response_json = track1_output[1]
    if sql_query["status"] == "success":
        # storing the sql query and output table in track_dict
        sql_query = {
            "status": sql_query["status"],
            "sql": sql_query["output"][0],
            "table": sql_query["output"][1].to_dict(),
            "table_dictionary": sql_query["output"][2],
        }
    # track_dict - Update
    track_dict["track1"]["question"].append(body.question)
    track_dict["track1"]["output"].append(sql_query)
    # Formatting dictionary to JSON
    sql_query = json.dumps(sql_query, indent=4)

    return sql_query, response_json


# Track - 2
@app.post("/query_to_chart")
def query_to_chart(body: Tracks):
    """
    It creates API using FastAPI for track 2.
    The function's used to generate chart from a table based on the user's question and additional context.
    It does this by looking up the user's question in a predefined dictionary (track_dict).

    Args:
        question(str): user_question
        additional_context(str): additional information provided by user
        language(str): language that GPT uses to respond to user
        domain_name(str): domain name

    Returns:
        chart_dict(json): contains status, chart_object and output table
        response_json(json): Response JSON

    """
    ind = track_dict["track1"]["question"].index(body.question)
    sql_query = track_dict["track1"]["output"][ind]

    chart = track1_ins.query_to_chart(
        question=body.question,
        language=body.language,
        additional_context=body.additional_context,
        track1_output_table=pd.DataFrame.from_dict(sql_query["table"]),
        track1_output_table_dict=sql_query["table_dictionary"],
    )
    # storeing the chart object and output table in chart_dict
    response_json = chart[1]
    if chart[0]["status"] in ["skip", "success"]:
        chart = {"status": chart[0]["status"], "chart": chart[0]["output"][0]}

    chart = urllib.parse.urlencode(chart)
    chart_dict = urllib.parse.parse_qs(chart)
    for key, value in chart_dict.items():
        chart_dict[key] = urllib.parse.unquote(value[0])
    chart_dict["table"] = sql_query["table"]
    # Formatting dictionary to JSON
    chart_dict = json.dumps(chart_dict, indent=4)

    return chart_dict, response_json


# Track - 3
@app.post("/table_to_insights")
def table_to_insights(body: Tracks):
    """
    It creates API using FastAPI for track 3.
    The function's used to generate insights from a table based on the user's question and additional context.
    It does this by looking up the user's question in a predefined dictionary (track_dict). 

    Args:
        question(str): user_question
        additional_context(str): additional information provided by user
        language(str): language that GPT uses to respond to user
        domain_name(str): domain name

    Returns:
        insights(json): contains status and insights generated from table
        response_json(json): Response JSON

    """
    ind = track_dict["track1"]["question"].index(body.question)
    sql_query = track_dict["track1"]["output"][ind]

    track3_output = track1_ins.table_insights(
        question=body.question,
        language=body.language,
        additional_context=body.additional_context,
        track1_output_table=pd.DataFrame.from_dict(sql_query["table"]),
        track1_output_table_dict=sql_query["table_dictionary"],
    )
    # storing the track3 insights in insights_dict
    insights = track3_output[0]
    response_json = track3_output[1]
    # Formatting dictionary to JSON
    insights = json.dumps(insights, indent=4)

    return insights, response_json


@app.post("/chat_question")
def chat_question(body: QuestionRequest):
    """
    Invokes all three tracks and captures response json from each track.

    Args:
        context_id (int): Context id from user conversation
        chat_id (int): Chat id of current conversation
        user_id (str): User Id
        question (str): User question
        data_name (str): Domain name

    Returns:
        json: JSON object containing user_id, question_id, answer_id, category and response_json.

    """
    logging.info("Python HTTP trigger function processed a request.")

    try:
        context_id = body.context_id
        chat_id = body.chat_id
        user_id = body.user_id
        question = body.question
        data_name = body.data_name.lower()

        result, err = create_new_question(
            chat_id,
            context_id,
            user_id,
            question,
            data_name,
            additional_context="",
            language="english",
        )
        if result is None:
            return f"An error occurred while processing the request. {str(err)}"
        json_data = json.dumps(result, cls=CustomJSONEncoder)

        return json_data

    except Exception as e:
        logging.error(str(e))
        return f"An error occurred while processing the request. {str(e)}"


# Pre Track
@app.post("/pre_track")
def pre_track(body: PreTracks):
    """
    Creates API before track call.

    Args:
        db_conn (dict): DB connection
    
    Returns:
        db_conn (dict): DB connection
    """
    print("---------Pre Track----------")
    skip_track1=skip_track2=skip_track3=None
    if body.db_conn is None:
        db_conn = db_factory.create_database_connection(app_database_config)
    user_type, ques_list = check_user_type_request(body.user_id, body.context_id, body.question, db_conn)

    return user_type, ques_list, skip_track1, skip_track2, skip_track3


# Post Track
@app.post("/post_track")
def post_track(body: PostTracks):
    """
    Post Processing output of Response JSON returned from track API's.

    Args:
        content (dict):
        db_conn (dict): DB connection
    Returns:

    """
    if body.db_conn is None:
        db_conn = db_factory.create_database_connection(app_database_config)

    result = db_storage(body.user_id, body.context_id, body.chat_id, body.content, body.question, body.data_name, db_conn)

    return result, None
