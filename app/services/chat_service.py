import json
import logging
import math
import random
import string
import traceback
from datetime import datetime
from typing import List, Optional

import jwt
import requests

from app.schemas.chats import CreateOrUpdateChatResponse
from app.schemas.question import QuestionResponse
from app.schemas.report import GenerateReportResponse
from app.services.user_service import check_reqs_limit, check_user_type
from core.clients.azure.database.postgres_client import AzurePostgresClient
from core.database.database_factory import DatabaseFactory
from core.utils.client_utils import get_database_client
from core.utils.read_config import (app_database_config, cloud_config,
                                    cloud_secrets, config, secrets_config)

logging.getLogger().setLevel(logging.INFO)

database_client = get_database_client(database_type=app_database_config.app_db_name)
db_factory = DatabaseFactory(database_client)


def change_date_format(data: str):
    """
    Converts a date string from a specific format to another format.

    Args:
        data (str): The input date string in the format 'YYYY-MM-DD HH MM SS fZ'.

    Returns:
        str: The formatted date string in the format 'YYYY-MM-DD HH:MM:SS'.
    """
    data = data.split("_")
    data = " ".join(data)
    custom_format = datetime.strptime(data, "%Y-%m-%d %H %M %S %fZ")
    return custom_format.strftime("%Y-%m-%d %H:%M:%S")


def create_new_chat(user_id: str, data_name: str, db_conn=None, client=None):
    """
    Creates a new chat session for the given user credentials.

    Args:
        user_id (str): Specifies the user ID.
        data_name (str): Specifies the domain name.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns Chat ID and Chat Name
    """
    try:
        chat_name = "chat " + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        query = f"""UPDATE chat_details SET is_active=FALSE WHERE user_id='{user_id}' AND lower(data_name)=lower('{data_name}');
                    INSERT INTO chat_details
                    (user_id, chat_name, is_active, created_time, modified_time, data_name)
                    VALUES
                    ('{user_id}', '{chat_name}', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '{data_name}') RETURNING chat_id;"""

        chat_id = client.execute_query(
            connection=db_conn, query=query, return_value=True
        )
        return chat_id, chat_name
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def get_report_list(user_id: str, data_name: str, db_conn=None, client=None):
    """
    Retrieves the chat reports for the given user credentials.

    Args:
        user_id (str): Specifies the user ID.
        data_name (str): Specifies the domain name.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns a list containing result objects with chat and report information related details.
    """
    try:
        query = f"""select * from chat_reports where user_id like ('{user_id}') and lower(data_name) like (lower('{data_name}')) ORDER BY chat_id;"""
        report_rows = client.read_query(connection=db_conn, query=query)
        logging.info("Report Rows")
        result = []
        for row in report_rows:
            item = GenerateReportResponse()
            item.report_id = row[0]
            item.report_name = row[1]
            item.chat_id = row[2]
            item.ques_list = row[3] if row[3] is not None else []
            item.created_time = row[4]
            item.user_id = row[5]
            item.report_url = row[6]
            result.append(item)

        return result
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def reset_chat(user_id: str, data_name: str, db_conn=None, client=None):
    """
    Creates a new chat session, context for the given user credentials.

    Args:
        user_id (str): Specifies the user ID.
        data_name (str): Specifies the domain name.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns the result object containing new chat details and updated report history.
    """
    try:
        result = CreateOrUpdateChatResponse(
            user_id=user_id, data_name=data_name, chat_details={}
        )
        # 1. Create New chat
        new_chat_id, new_chat_name = create_new_chat(
            user_id=user_id, data_name=data_name, db_conn=db_conn, client=client
        )

        # 2. Create New Context
        new_context_id = (
            create_new_context(
                chat_id=new_chat_id,
                user_id=user_id,
                data_name=data_name,
                db_conn=db_conn,
                client=client,
            )
            if new_chat_id is not None
            else None
        )

        # 3. Get Report History
        result.report_list = get_report_list(
            user_id=user_id, data_name=data_name, db_conn=db_conn, client=client
        )

        # 4. Get chat History
        result.chat_details.chat_history = {}
        result.chat_details.chat_id = new_chat_id
        result.chat_details.chat_name = new_chat_name
        result.chat_details.is_active = True
        result.chat_details.context_id = new_context_id

        return result

    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def check_existing_user(user_id: str, data_name: str, db_conn=None, client=None):
    """
    Creates a new chat session, context for the given user credentials.

    Args:
        user_id (str): Specifies the user ID.
        data_name (str): Specifies the domain name.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns the result object containing the updated chat details and report history for the user.
    """
    try:
        result = CreateOrUpdateChatResponse(
            user_id=user_id, data_name=data_name, chat_details={}
        )
        # Check for existing user
        query = f"SELECT * FROM user_config WHERE user_id like ('{user_id}') and lower(data_name) like (lower('{data_name}'));"
        user_rows = client.read_query(connection=db_conn, query=query)
        logging.info(f"User Rows - {user_rows}")

        # TODO: also add last_login_time column which you will get from get_user_details_from_token
        # last_login_time = get_last_login_time(access_token)
        last_login_time = "CURRENT_TIMESTAMP"

        if len(user_rows) > 0:
            # Functionality for exisitng user
            # Update user's login time
            query = f"UPDATE user_config SET last_login_time = {last_login_time}, modified_time = CURRENT_TIMESTAMP WHERE user_id like ('{user_id}') AND lower(data_name) like (lower('{data_name}'));"
            client.execute_query(connection=db_conn, query=query)

            # get chat details
            query = f"""SELECT cd.chat_id, cd.chat_name, cd.is_active, cc.context_id, cc.data_name
                    FROM chat_details AS cd
                    LEFT JOIN chat_contexts AS cc ON cc.chat_id = cd.chat_id AND lower(cc.data_name)=lower(cd.data_name)
                    WHERE cd.user_id = '{user_id}' AND lower(cd.data_name) = lower('{data_name}') AND cd.is_active = TRUE AND cc.is_active=TRUE;"""
            chat_details_row = client.read_query(connection=db_conn, query=query)[0]
            result.chat_details.chat_id = chat_details_row[0]
            result.chat_details.data_name = chat_details_row[4]
            result.chat_details.chat_name = chat_details_row[1]
            result.chat_details.is_active = chat_details_row[2]
            result.chat_details.context_id = chat_details_row[3]

            # Get report
            result.report_list = get_report_list(
                user_id=user_id, data_name=data_name, db_conn=db_conn, client=client
            )

            # TODO: Implemente Get chat history functionality
            result.chat_details.chat_history = get_chat_history_by_chat_id(
                [result.chat_details.chat_id], [result.chat_details.data_name], db_conn
            )

        else:
            # Functionality for New user

            # TODO: Add user_name, User_email columns in user_config table in database. ```name, user_id, email = get_user_details_from_token(token)```
            query = f"INSERT INTO user_config (user_id, created_time, modified_time, last_login_time,data_name) VALUES ('{user_id}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, {last_login_time}, '{data_name}');"
            client.execute_query(connection=db_conn, query=query)

            result = reset_chat(
                user_id=user_id, data_name=data_name, db_conn=db_conn, client=client
            )

        return result

    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def create_new_context(
    chat_id: str, user_id: str, data_name: str, db_conn=None, client=None
):
    """
    Creates a new chat context for the given chat session.

    Args:
        chat_id (str): Specifies the chat ID.
        user_id (str): Specifies the user ID.
        data_name (str): Specifies the domain name.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns the context ID created for the user.
    """
    try:
        query = f"""UPDATE chat_contexts SET is_active=FALSE WHERE user_id='{user_id}' AND lower(data_name)=lower('{data_name}');
                    INSERT INTO chat_contexts (user_id, chat_id, created_time, modified_time, data_name)
                    VALUES ('{user_id}', {chat_id}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '{data_name}')
                    RETURNING context_id;"""

        context_id = client.execute_query(
            connection=db_conn, query=query, return_value=True
        )
        return context_id
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def get_last_login_time(access_token):
    """
    Finds the last login time of a user.

    Args:
        access_token: Specifies the access token of the user

    Returns:
        Returns the last_login_time of the user.
    """
    try:
        # TODO: Implement GettingTimeFromJwtToken When we start getting Token in Request Header from frontend team
        # decoded_token = jwt.decode(access_token, verify=False, algorithms=['HS256'])  # Use appropriate decoding and verification
        iat_timestamp = datetime.now()  # decoded_token.get("iat")
        formatted_time = iat_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return {"error": True}


def get_scopes_from_token(access_token):
    """
    Finds the scope of the user based on access_token.

    Args:
        access_token: Specifies the access token of the user

    Returns:
        Returns the scopes of the user.
    """
    try:
        decoded_token = jwt.decode(
            access_token, verify=False
        )  # Use appropriate decoding and verification
        scopes = decoded_token.get("scp", "").split()
        return scopes
    except jwt.DecodeError:
        # Handle decoding error
        return []
    except jwt.ExpiredSignatureError:
        # Handle expired token error
        return []


def replace_nan_with_none(data):
    """
    Recursively replaces NaN (Not a Number) values with None in a dictionary or a list.

    Args:
        data: A dictionary or a list possibly containing NaN values.

    Returns:
        None
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) or isinstance(value, list):
                replace_nan_with_none(value)
            elif isinstance(value, float) and math.isnan(value):
                data[key] = None
    elif isinstance(data, list):
        for item in data:
            replace_nan_with_none(item)


def create_new_question(
    chat_id: int,
    context_id: int,
    user_id: str,
    question: str,
    data_name: str,
    additional_context: str,
    language: str,
    db_conn=None,
):
    """
    Creates a database connection, if it doesn't exist.

    Parameters
    ----------
        - chat_id: Specifies the chat ID
        - context_id: Specifies the context ID
        - user_id: Specifies the user ID
        - question: Specifies the question asked by the user
        - db_conn: Specifies the database connection

    Returns
    -------
        Returns the result object containing the updated chat details for the user .
    """
    try:        
        headers = {
            "Content-Type": "application/json",
        }

        url = "http://ipro-app-service.default.svc.cluster.local:80/"

        data = {
            "user_id": user_id,
            "context_id": context_id,
            "question": question,
        }

        # Pre Track
        pre_track_api = url + "pre_track"
        # Make the POST request
        response = requests.post(pre_track_api, json=data, headers=headers)
        if response.status_code == 200:
            output_response = response.json()
            logging.info("Pre Track Respone: %s", output_response)
            content = output_response[1]
        else:
            return f"POST request failed in pre_track with status code:", {
                response.status_code
            }
        
        data = {
            "question": question,
            "additional_context": additional_context,
            "language": language,
            "domain_name": data_name.replace(" ", "_"),
        }
        # Track 1
        track1_api = url + "text_to_query"
        # Make the POST request
        response = requests.post(track1_api, json=data, headers=headers)
        if response.status_code == 200:
            output_response = response.json()
            logging.info("Response 1: %s", output_response)
            content = output_response[1]
        else:
            return f"POST request failed in text_to_query with status code:", {
                response.status_code
            }

        # Track 2
        track2_api = url + "query_to_chart"
        # Make the POST request
        response = requests.post(track2_api, json=data, headers=headers)
        if response.status_code == 200:
            output_response = response.json()
            logging.info("Response 2: %s", output_response)
            content = output_response[1]
        else:
            return f"POST request failed in query_to_chart with status code:", {
                response.status_code
            }

        # Track 3
        track3_api = url + "table_to_insights"
        # Make the POST request
        response = requests.post(track3_api, json=data, headers=headers)
        if response.status_code == 200:
            output_response = response.json()
            logging.info("Response 3: %s", output_response)
            content = output_response[1]
        else:
            return f"POST request failed in table_to_insights with status code:", {
                response.status_code
            }

        data = {
            "user_id": user_id,
            "context_id": context_id,
            "chat_id": chat_id,
            "content": content,
            "question": question,
            "data_name": data_name
        }
        # Post Track
        post_track_api = url + "post_track"
        # Make the POST request
        response = requests.post(post_track_api, json=data, headers=headers)
        if response.status_code == 200:
            output_response = response.json()
            logging.info("Post Track Respone: %s", output_response)
        else:
            return f"POST request failed in post_track with status code:", {
                response.status_code
            }
        return output_response

    except Exception as e:
        logging.info(traceback.format_exc())
        logging.info(e)
        return None, e


def get_bot_response(ques_list: list, context_id: int, db_conn=None, client=None):
    """
    Retrieve bot responses for given questions from the database.

    Args:
        ques_list (list): List of user questions to retrieve responses for.
        context_id (int): Context ID for filtering responses.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns list of bot responses for the given questions if found, otherwise returns None.
    """
    try:
        query = f"""SELECT ARRAY_AGG(response_for_history) AS response_for_history_list
                    FROM chat_questions
                    WHERE user_question IN {ques_list} and context_id={context_id};"""

        bots = client.read_query(connection=db_conn, query=query)
        logging.info(bots[0][0])
        return bots[0][0]
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def get_chat_history_by_chat_id(
    chat_ids: List[str], data_names: List[str], db_conn=None, client=None
):
    """
    Retrieves chat history for given chat ids and data names.


    Args:
        chat_ids: Specifies the list of chat IDs.
        data_names: Specifies the list of domain names.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns the chat history of the user using the list of chat IDs.
    """
    try:
        query = f"""
                    SELECT json_object_agg(chat_history.context_id, chat_history.context_data) as response
                    FROM (
                        SELECT chat_history.context_id, json_agg(chat_history) as context_data
                        FROM (
                            SELECT cq.question_id, cq.answer_id, cq.context_id, cr.category as type, cr.user_feedback as feedback, cq.created_time, cr.answer_seq, cq.user_question as question, cr.content as data
                            FROM chat_questions AS cq
                            LEFT JOIN chat_responses AS cr ON cq.answer_id = cr.answer_id
                            LEFT JOIN chat_details AS cd ON cq.chat_id = cd.chat_id
                            WHERE cq.chat_id IN ({','.join(map(str, chat_ids))})
                            AND cd.data_name IN ({','.join([f"'{data_name.lower()}'" for data_name in data_names])})
                            ORDER BY cq.question_id
                        ) AS chat_history
                        GROUP BY chat_history.context_id
                        ORDER BY chat_history.context_id
                    ) AS chat_history;


                    """
        chat_history = client.read_query(connection=db_conn, query=query)

        return chat_history[0][0] if chat_history[0][0] else {}

    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def feedback(
    answer_id: str,
    status: bool,
    reason: Optional[str] = None,
    db_conn=None,
    client=None,
):
    """
    Stores the feedback of user for a genrated answer using answer id.

    Args:
        answer_id (str): Specifies the answer ID
        status (bool): Specifies the status given by the user for an answer (if status=True means user liked the answer, if status=False means user disliked the answer).
        reason (str): Specifies the reason if the user disliked the answer (status=False)
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns boolean value true post successfull feedback update.
    """
    try:
        query = f"UPDATE chat_responses SET user_feedback={status}, user_comment='{reason}', modified_time = CURRENT_TIMESTAMP WHERE answer_id='{answer_id}';"
        client.execute_query(connection=db_conn, query=query)
        return {"status": True}

    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def get_questions_by_context_id(context_id: int, db_conn=None, client=None):
    """
    Retrieves the questions associated with a context id.

    Args:
        context_id (int): Specifies the context id.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
        Returns the list of questions for the given context ID.
    """
    try:
        query = f"SELECT array_agg(user_question) as question_list,ARRAY_AGG(response_for_history) AS category_list FROM chat_questions WHERE context_id={context_id};"
        response_list = db_factory.read_query(
            connection=db_conn, query=query
        )
        logging.info(response_list[0])
        queslist, botlist = response_list[0]
        logging.info(queslist)
        logging.info(botlist)
        return queslist, botlist

    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def send_mock_insight_type_answer():
    """
    Sends a mock response with insight type answer.

    """
    # TODO: get a second response without an error
    return """jsonb_build_array(
                jsonb_build_object(
                'insight_type', 'sql_query',
                'content', 'SELECT COUNT(DISTINCT sto_sap_invoice) AS shipment_count FROM invoice_data WHERE source_location_name LIKE ''%Location 14%''',
                'error', null,
                'showError', false
                ),
                jsonb_build_object(
                'insight_type', 'chart',
                'content', '{"x-axis": "shipment1, shipment2, shipment3", "y-axis": "34, 45, 67"}',
                'error', null,
                'showError', true
                ),
                jsonb_build_object(
                'insight_type', 'summary',
                'content', 'The table contains data for three brands: BoldBites, FlavorCrave, and RidgeBite, with ordered_qty values of 44,879,360, 37,633,471, and 24,690,799 respectively, and all having an unshipped_qty of 4. - There is a strong positive correlation between brand popularity and ordered_qty, with BoldBites being the most popular and RidgeBite being the least popular.',
                'error', null,
                'showError', false
                )
            )"""


def send_mock_clarification_type_answer():
    """
    Sends a mock response requesting more business context.

    Returns:
        dict: A dictionary with the mock response.
    """
    return (
        {"content": "I did not understand. Can you give me more business context?"},
    )


def send_mock_table_selector_type_answer():
    """
    Sends a mock response with a list of table JSON objects.

    Returns:
        dict: A dictionary with a list of table JSON objects
    """
    return (
        {"content": "[{table_json1}, {table_json2}, {table_json3}, {table_json4}]"},
    )


def check_user_type_request(user_id, context_id, question, db_conn=None):
    """
    Checks user type and requests made by user(for external user(other than tiger)) and gets question list.

    Args:
        user_id (int): User ID
        context_id (int): Context ID
        question (str): User question
        db_conn (dict): DB connection

    Returns:
        user_type (str): User type
        remainder (int): Remaining number of request for a user
        ques_list (list): List of questions
    """
    user_type = check_user_type(user_id=user_id, db_conn=db_conn)
    if user_type == "external":
        remainder = check_reqs_limit(user_id=user_id, db_conn=db_conn)
        if remainder is None:
            return None, "Exhausted Questions Quota!!"
    ques_list, botlist = get_questions_by_context_id(context_id, db_conn)
    logging.info("Question List %s", ques_list)
    if ques_list is None:
        ques_list = [[question, None]]
    else:
        # ques_list = list(set(ques_list))
        logging.info(len(ques_list))

        ques_list = [list(pair) for pair in zip(ques_list, botlist)]
        ques_list.append([question, None])
        # ques_str = "; ".join([f"{pair[0]}: {pair[1]}" for pair in ques_list])
    logging.info("Question List %s", ques_list)

    if user_type != "tiger":
        query = f"""UPDATE user_credentials SET total_requests = total_requests + 1 WHERE user_id= ('{user_id}')"""
        db_factory.execute_query(db_conn, query, return_value=False)

    return user_type, ques_list


def db_storage(user_id, context_id, chat_id, content, question, data_name, db_conn):
    """
    Stores chat responses and chat questions based input to database and returns response json.
    """
    result = QuestionResponse()
    replace_nan_with_none(content)

    logging.info(content["Response JSON"])

    query = """
        INSERT INTO chat_responses (category, created_time, modified_time, content)
        VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
        RETURNING answer_id;
    """
    # TODO
    answer_id = db_factory.execute_query(db_conn, query, True, content)
    logging.info("answer_id %s", answer_id)
    question_to_insert = question.replace("'", "''")
    response_to_insert = content["Response JSON"]["response_for_history"].replace(
        "'", "''"
    )
    question_index = content["Response JSON"]["question_index"]
    output_path = content["Response JSON"]["output_path"]
    engines = json.dumps(content["Response JSON"]["engines"])
    # store question data and answer_id in chat_questions
    query = f"""INSERT INTO chat_questions
            (user_question, answer_id, context_id, chat_id, user_id, created_time, modified_time,response_for_history, data_name, question_index, output_path, engines)
            VALUES
            ('{question_to_insert}', {answer_id}, {context_id}, {chat_id}, '{user_id}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,'{response_to_insert}', '{data_name}', '{question_index}', '{output_path}', '{engines}') RETURNING question_id;"""
    question_id = db_factory.execute_query(db_conn, query, True)
    logging.info("question_id %s", question_id)
    # 3. modified DS API's response in such way it could be provided to frontend Team
    result.user_id = user_id
    result.question_id = question_id
    result.answer_id = answer_id
    result.category = content["Response JSON"]["type"]
    # TODO: Get created_time from above question-storing-query
    result.content = content["Response JSON"]
    logging.info("Result %s", result)
    
    return result