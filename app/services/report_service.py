import json
import logging
import re
import traceback
from ast import literal_eval
from datetime import datetime
from typing import List, Optional

import pdfkit
import plotly.graph_objects as go
import yaml

from app.schemas.report import GenerateReportResponse
from app.services.chat_service import get_chat_history_by_chat_id
from core.utils.read_config import cloud_config, cloud_secrets, config

logging.getLogger().setLevel(logging.INFO)


class DotDict:
    def __init__(self, dictionary):
        self._dict = dictionary

    def __getattr__(self, item):
        value = self._dict.get(item)
        if isinstance(value, dict):
            return DotDict(value)  # Recursively wrap inner dictionaries
        return value

    def __getitem__(self, item):
        value = self._dict[item]
        if isinstance(value, dict):
            return DotDict(value)  # Recursively wrap inner dictionaries
        return value

    def __setattr__(self, key, value):
        if key == "_dict":
            super().__setattr__(key, value)
        else:
            self._dict[key] = value

    def __delattr__(self, item):
        del self._dict[item]

    def __repr__(self):
        return repr(self._dict)

    def __str__(self):
        return str(self._dict)


def load_yml(conf_path):
    with open(conf_path) as stream:
        try:
            config = yaml.safe_load(stream)
            return config
        except yaml.YAMLError as exc:
            logging.error(exc)
            return None


def create_new_report(
    chat_id: str,
    data_name: str,
    user_id: str,
    db_conn=None,
    client=None,
    storage_obj=None,
):
    """
    Creates a new report based on given user's chat details and creates entry in the database.

    Args:
        chat_id (str): Specifies the chat ID.
        data_name (str): Specifies the domain name.
        user_id (str): Specifies the user ID.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.
        storage_obj (storage_obj, optional): Specifies the storage core client. Defaults to None.

    Returns:
        Returns a tuple containing report_id, report_name, report_url, created_time.
    """
    try:
        formatted_date = datetime.now().strftime(
            f"%d %b %Y_%H꞉%M"
        )  # this is not colon, but modifier letter colon (U+A789)
        query = f"SELECT COUNT(DISTINCT report_id) AS counts FROM chat_reports;"

        report_name = f"{formatted_date}"
        (
            response_for_history,
            questions,
            content_list,
            context_ids,
        ) = get_details_by_chat_id(
            chat_id=chat_id, data_name=data_name, db_conn=db_conn, client=client
        )
        ans_list = create_entry(
            content_list, response_for_history, questions, context_ids
        )
        pdf_data = create_pdf(ans_list, chat_id)
        file_name = f"reports/{user_id.split('.')[0]}/{formatted_date}.pdf"

        _ = storage_obj.connect_to_storage(
            storage_details=cloud_config.reports_storage,
            connection_keys=cloud_secrets.reports_storage,
        )
        logging.info(f"File Name - {file_name}")

        file_url = storage_obj.upload_file_to_storage(file_name, pdf_data)
        file_url_without_sas_token = file_url.split("?")[0]
        report_url = file_url

        query = f"""INSERT INTO chat_reports (report_name, chat_id, ques_list, created_time, user_id, report_url, data_name)
            VALUES
            ('{report_name}', {chat_id}, NULL, CURRENT_TIMESTAMP, '{user_id}', '{file_url_without_sas_token}', '{data_name}') RETURNING report_id;"""

        report_id = client.execute_query(
            connection=db_conn, query=query, return_value=True
        )
        created_time = (
            datetime.now()
            .strftime("%Y-%m-%d %H:%M:%S")
            .replace("+00:00", "Z")
            .replace(":", "_")
            .replace(" ", "_")
            .replace(".", "_")
        )
        # TODO: get created time from above excute_query itself.
        return report_id, report_name, report_url, created_time
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def generate_report(
    user_id: str,
    data_name: str,
    chat_id: str,
    db_conn=None,
    client=None,
    storage_obj=None,
):
    """
    Generate a report for a given user, data name, and chat id.

    Args:
        user_id (str): Specifies the user ID.
        data_name (str): Specifies the domain name.
        chat_id (str): Specifies the chat ID.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.
        storage_obj (storage_obj, optional): Specifies the storage core client. Defaults to None.

    Returns:
        An object containing details of the generated report if successful, otherwise returns None.
    """
    try:
        report_details = GenerateReportResponse(
            chat_id=chat_id, data_name=data_name, user_id=user_id
        )

        # 1. Generate report
        # Create new report entry in chat_report table
        (
            report_details.report_id,
            report_details.report_name,
            report_details.report_url,
            report_details.created_time,
        ) = create_new_report(
            chat_id=chat_id,
            data_name=data_name,
            user_id=user_id,
            db_conn=db_conn,
            client=client,
            storage_obj=storage_obj,
        )

        # Get reports chat_history
        report_details.chat_history = get_chat_history_by_chat_id(
            client=client, chat_ids=[chat_id], data_names=[data_name], db_conn=db_conn
        )

        return report_details
        # TODO: Create PDF for Report
    except Exception as e:
        logging.error(traceback.format_exc())
        print(e)
        return None


def get_details_by_chat_id(chat_id: int, data_name: str, db_conn=None, client=None):
    """
    Retrieve details by chat id and data name from the database.

    Args:
        chat_id (int): ID of the chat.
        data_name (str): Name of the data to retrieve.
        db_conn (connection, optional): The database connection. Defaults to None.
        client (client, optional): Specifies the database core client. Defaults to None.

    Returns:
       A tuple containing lists of response_for_history, ques_list, content_list, and context_ids.

    """
    #     query = f"""SELECT distinct b.user_question, a.content
    #                 FROM chat_questions as b
    #                 LEFT JOIN chat_responses as a on a.answer_id = b.answer_id
    #                 WHERE a.content -> 'status' -> 0 != '"failure"'
    #                 and b.chat_id = {chat_id};
    #               """
    query = f"""SELECT distinct b.user_question, a.content, b.response_for_history, b.question_id,b.context_id
                FROM chat_questions as b
                LEFT JOIN chat_responses as a on a.answer_id = b.answer_id
                WHERE b.chat_id = {chat_id} AND lower(b.data_name)= lower('{data_name}') order by b.question_id ASC;"""
    res = map(client.read_query, connection=db_conn, query=query)
    context_ids = [item[4] for item in res]
    response_for_history = [item[2] for item in res]
    content_list = [item[1] for item in res]
    ques_list = [item[0] for item in res]
    return response_for_history, ques_list, content_list, context_ids


def create_entry(
    content_list: list, response_for_history: list, questions: list, context_ids: list
):
    """
    Creates a dictionary list from provided lists of content, response_for_history, questions, and context_ids.

    Args:
        content_list (list): List of content.
        response_for_history (list): List of responses for history.
        questions (list): List of questions.
        context_ids (list): List of context IDs.

    Returns:
        A list of dictionaries containing entry details.

    """
    ans_list = []
    for i, entry in enumerate(content_list):
        ans_dict = dict()
        ans_dict["question"] = questions[i]
        ans_dict["context_id"] = context_ids[i]
        for content in entry["data"]:
            if (content["insight_type"]) in ["chart", "table"]:
                ans_dict["figure_type"] = content["insight_type"]
                ans_dict["figure"] = content["content"]
            if (content["insight_type"]) in ["multi_chart"]:
                ans_dict["figure_type"] = content["insight_type"]
                ans_dict["figure"] = [i for i in content["content"]]
                ans_dict["table"] = content["table"]
            if (content["insight_type"]) == "summary":
                ans_dict["summary"] = (
                    response_for_history[i] + "<br><br>" + content["content"]
                    if response_for_history[i] is not None
                    else content["content"]
                )
            else:
                ans_dict["summary"] = (
                    response_for_history[i]
                    if response_for_history[i] is not None
                    else ""
                )
        ans_list.append(ans_dict)
    return ans_list


def create_table(data):
    """
    Creates a HTML format table for the given tabular data.

    """
    try:
        data = literal_eval(data[0])
    except:
        data = [json.loads(s) for s in data]
        data = data[0]
    all_keys = set().union(*data)
    header = list(all_keys)
    rows = []
    for key in all_keys:
        row = [item.get(key) for item in data]
        rows.append(row)

    # Transpose the rows
    transposed_rows = list(map(list, zip(*rows)))

    # Filter out rows that are entirely None or empty
    non_empty_rows = [
        row
        for row in transposed_rows
        if any(cell is not None and cell != "" for cell in row)
    ]
    # TODO: From dynaconf object select no of rows to keep in the generated PDF
    non_empty_rows = non_empty_rows[:10]
    rows = rows[:10]

    table_html = (
        "<table style='border-collapse: collapse; width: 100%; text-align: center;'>"
    )

    # Create the table header
    table_html += "<tr style='background-color: #b3b3ff;'>"
    for col in header:
        table_html += f"<th style='border: 1px solid white; padding: 8px;'>{col}</th>"
    table_html += "</tr>"

    # Create the table rows
    for row in non_empty_rows:
        table_html += "<tr>"
        for cell in row:
            cell_value = cell if cell is not None else ""
            table_html += f"<td style='border: 1px solid white; padding: 8px; background-color: #e0e0d1;'>{cell_value}</td>"
        table_html += "</tr>"

    table_html += "</table>"

    return table_html


def create_chart(data):
    """
    Creates a HTML format chart for the given data.

    """
    for trace in data:
        fig = go.Figure(trace)
    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    #     fig.show()
    return chart_html


def create_pdf(ans_list: List[str], chat_id: int, save_to: Optional[str] = None):
    """
    Creates a PDF from the HTML format by arranging and creating the template.

    """
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #f2f2f2;
            }}
            .logo-image {{
                max-width: 100px;
                max-height: 100px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background-color: white; /* Header background color */
                padding: 10px;
                border-bottom: 1px solid #ccc; /* Bottom border for header */
            }}
            .content {{
                padding: 20px;
            }}
            .thicker-hr {{
                border: none;
                border-top: 3px solid #ccc; /* Adjust the thickness and color as needed */
                margin: 10px 0;
            }}
        </style>
        <script>
            function updateDateTime() {{
                const options = {{ year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric', hour12: false }};
                const currentDateTime = new Date().toLocaleString('en-US', options);
                document.getElementById("current_date_time").textContent = currentDateTime;
            }}
            window.onload = updateDateTime;
        </script>
    </head>
    <body>
        <header class="header">
            <img src="data:image/png;base64,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" alt="Logo" class="logo-image">
            <span id="current_date_time" style="text-align: right;"></span>
        </header>
        <div class="content">
            {content}
        </div>
    </body>
    </html>
    """

    content = ""
    prev_context_id = ans_list[0].get("context_id")
    for i in range(len(ans_list)):
        context_id = ans_list[i].get(
            "context_id"
        )  # Get the context_id for the current answer
        if context_id != prev_context_id:
            if prev_context_id is not None:
                # Insert a horizontal line between different context_ids
                content += '<hr class="thicker-hr">'
            prev_context_id = context_id
        content += f"<h1>Question {i+1}</h1>"
        content += f"<p>{ans_list[i]['question']}</p>"
        content += f"<h2>Answer {i+1}</h2>"
        bullet_points = re.findall(
            r"- (.+?)(?=\n|$)", ans_list[i]["summary"], re.DOTALL
        )
        if bullet_points:
            content += "<ul>"
            for point in bullet_points:
                content += f"<li>{point}</li>"
            content += "</ul>"
        else:
            content += f"<p>{ans_list[i]['summary']}</p>"
        if "figure_type" not in ans_list[i]:
            continue
        figure_type = ans_list[i]["figure_type"].capitalize()
        if ans_list[i]["figure_type"] == "table":
            table_html = create_table(ans_list[i]["figure"])
            content += f'<div style="page-break-inside: avoid;"><h2>{figure_type}</h2>{table_html}</div>'
        elif ans_list[i]["figure_type"] == "chart":
            chart_html = create_chart(ans_list[i]["figure"])
            # Wrap the chart HTML in a div with the page-break-inside: avoid; CSS property
            content += f'<div style="page-break-inside: avoid;"><h2>{figure_type}</h2>{chart_html}</div>'
        elif ans_list[i]["figure_type"] == "multi_chart":
            for j, fig in enumerate(ans_list[i]["figure"]):
                f_type = f"Chart - {j+1}"
                chart_html = create_chart(fig["data"])
                content += f'<div style="page-break-inside: avoid;"><h2>{f_type}</h2>{chart_html}</div>'
                content += "<br>"
                content += "<br>"
            # chart_html = create_chart(ans_list[i]["figure"])

            table_html = create_table(ans_list[i]["table"])
            # TODO Same rows limit from dynaconf
            f_type = f"Table - [Top 10]"
            content += f'<div style="page-break-inside: avoid;"><h2>{f_type}</h2>{table_html}</div>'
        content += "<br>"
        content += "<br>"
        content += "<br>"
        content += "<br>"

    # Merge the content into the template
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_html = html_template.format(
        content=content, current_date_time=current_date_time
    )
    # Configure PDF options (optional)
    pdf_options = {
        "page-size": "A4",
        "orientation": "Portrait",
        "margin-top": "0.75in",
        "margin-right": "0.75in",
        "margin-bottom": "0.75in",
        "margin-left": "0.75in",
    }
    try:
        pdf_data = pdfkit.from_string(final_html, False, options=pdf_options)
    except:
        logging.error(traceback.format_exc())
    return pdf_data
