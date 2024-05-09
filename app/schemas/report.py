from typing import Any, List, Optional, Union

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    """
    Represents a request to generate a report.

    Attributes:
        user_id (Union[int, str]): The ID of the user.
        data_name (Union[int, str]): The name of the data.
        chat_id (int): The ID of the chat.
    """

    user_id: Union[int, str]
    data_name: Union[int, str]
    chat_id: int


class GenerateReportResponse(BaseModel):
    """
    Represents the response object for generating a report.

    Attributes:
        chat_id (Optional[int]): The ID of the chat.
        report_id (Optional[int]): The ID of the report.
        report_name (Optional[str]): The name of the report.
        user_id (Optional[str]): The ID of the user.
        report_url (Optional[str]): The URL of the report.
        ques_list (Optional[List[int]]): The list of question IDs.
        chat_history (Optional[Any]): The chat history.
        created_time (Optional[str]): The time when the report was created.
    """

    chat_id: Optional[int]
    report_id: Optional[int]
    report_name: Optional[str]
    user_id: Optional[str]
    report_url: Optional[str]
    ques_list: Optional[List[int]]
    chat_history: Optional[Any]
    created_time: Optional[str]
