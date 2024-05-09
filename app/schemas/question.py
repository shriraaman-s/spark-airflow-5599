from typing import Any, Optional  # List,

from pydantic import BaseModel

from app.schemas.base import BaseRequest  # BaseResponse


class ContentComponent(BaseModel):
    """
    Represents a content component.

    Attributes:
        category_type (Optional[str]): The category type of the content component.
        content (Any): The content of the component.
        error (Optional[str] or None): The error message associated with the component, if any.
        showError (Optional[bool]): Indicates whether to show the error message or not.
    """

    category_type: Optional[str]
    content: Any
    error: Optional[str] or None
    showError: Optional[bool]


class QuestionRequest(BaseModel):
    """
    Represents a request for a question.

    Attributes:
        context_id (int): The ID of the context.
        chat_id (int): The ID of the chat.
        user_id (str): The ID of the user.
        question (str): The question text.
        data_name (str): The name of the data.
    """

    context_id: int
    chat_id: int
    user_id: str
    question: str
    data_name: str


class QuestionResponse(BaseModel):
    """
    Represents a response to a question.

    Attributes:
        error (Optional[str]): The error message, if any.
        user_id (Optional[str]): The user ID associated with the response.
        question_id (Optional[int]): The question ID associated with the response.
        answer_id (Optional[int]): The answer ID associated with the response.
        category (Optional[str]): The category of the response.
        content (Optional[Any]): The content of the response.
    """

    error: Optional[str]
    user_id: Optional[str]
    question_id: Optional[int]
    answer_id: Optional[int]
    category: Optional[str]
    content: Optional[Any]


class ChartRequest(BaseRequest):  # Can inherit QuestionRequest
    """
    Represents a request for generating a chart based on a question.

    Attributes:
        question (str): The question for which the chart is generated.
        additional_context (Optional[str]): Additional context or information related to the question.
        sql_query (str): The SQL query used to fetch the data for the chart.
        output_table_dict (Optional[dict]): A dictionary representing the output table of the chart.
    """

    question: str
    additional_context: Optional[str]
    sql_query: str
    output_table_dict: Optional[dict]
