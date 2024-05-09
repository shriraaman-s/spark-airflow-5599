from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class GetDetailsResponse(BaseModel):
    """
    Represents the response object for getting chat details.

    Attributes:
        chat_id (Optional[int]): The ID of the chat.
        data_name (Optional[str]): The name of the data.
        context_id (Optional[int]): The ID of the context.
        chat_name (Optional[str]): The name of the chat.
        is_active (Optional[bool]): Indicates if the chat is active.
        chat_history (Optional[Dict]): The chat history.
    """

    chat_id: Optional[int]
    data_name: Optional[str]
    context_id: Optional[int]
    chat_name: Optional[str]
    is_active: Optional[bool]
    chat_history: Optional[Dict]


class CreateOrUpdateChatRequest(BaseModel):
    """
    Represents a request to create or update a chat.

    Attributes:
        user_id (Union[int, str]): The ID of the user associated with the chat.
        data_name (Union[int, str]): The name of the chat data.
    """

    user_id: Union[int, str]
    data_name: Union[int, str]


class CreateOrUpdateChatResponse(BaseModel):
    """
    Represents the response for creating or updating a chat.

    Attributes:
        user_id (Optional[Union[int, str]]): The ID of the user associated with the chat.
        data_name (Optional[Union[int, str]]): The name of the data associated with the chat.
        report_list (Optional[List]): A list of reports associated with the chat.
        chat_details (GetDetailsResponse): The details of the chat.

    """

    user_id: Optional[Union[int, str]]
    data_name: Optional[Union[int, str]]
    report_list: Optional[List]
    chat_details: GetDetailsResponse


class ResetRequest(BaseModel):
    """
    Represents a reset request for a chat.

    Attributes:
        user_id (Union[int, str]): The ID of the user making the reset request.
        chat_id (int): The ID of the chat to be reset.
    """

    user_id: Union[int, str]
    chat_id: int


class TopicRequest(BaseModel):
    """
    Represents a topic request.

    Attributes:
        user_id (Optional[str]): The ID of the user making the request.
        chat_id (Optional[int]): The ID of the chat associated with the request.
    """

    user_id: Optional[str]
    chat_id: Optional[int]


class TopicResponse(BaseModel):
    """
    Represents a response for a topic.

    Attributes:
        context_id (Optional[int]): The ID of the context associated with the response.
    """

    context_id: Optional[int]


class FeedbackRequest(BaseModel):
    """
    Represents a feedback request.

    Attributes:
        answer_id (int): The ID of the answer.
        status (bool): The status of the feedback request.
        reason (Optional[str], optional): The reason for the feedback request. Defaults to None.
    """

    answer_id: int
    status: bool
    reason: Optional[str] = None


class FeedbackResponse(BaseModel):
    """
    Represents a feedback response.

    Attributes:
        feedback (bool): Indicates whether the feedback is positive or negative.
    """

    feedback: bool


class QuesByContextRequest(BaseModel):
    """
    Represents a request to get questions by context.

    Attributes:
        context_id (int): The ID of the context.
    """

    context_id: int


class QuesByContextResponse(BaseModel):
    """
    Represents the response containing a list of questions based on context.

    Attributes:
        ques_list (list): A list of questions.
    """

    ques_list: list


class UserCredential(BaseModel):
    """
    Represents the credentials of a user.

    Attributes:
        user_id (str): The user ID.
        password (str): The user's password.
        usertype (str): The type of user.
        domain (str): The user's domain.
        exp_date (Union[str, None], optional): The expiration date of the credentials. Defaults to None.
    """

    user_id: str
    password: str
    usertype: str
    domain: str
    exp_date: Union[str, "None"] = None


class VerifyUser(BaseModel):
    """
    Represents a user for verification.

    Attributes:
        user_id (str): The user ID.
        password (str): The user's password.
    """

    user_id: str
    password: str


class GetDataNames(BaseModel):
    """
    Represents a data model for retrieving names.

    Attributes:
        user_id (str): The ID of the user.
    """

    user_id: str


class ChatContext(BaseModel):
    """
    Represents the context of a chat.

    Attributes:
        user_id (str): The ID of the user associated with the chat.
        chat_id (int): The ID of the chat.
        domain (str): The domain of the chat.
    """

    user_id: str
    chat_id: int
    domain: str


class ChatReset(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """

    user_id: str
    domain: str


class ChatHistory(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """

    chat_ids: List[str]
    domains: str


class Tracks(BaseModel):
    """
    Data Validation of inputs for tracks.

    Args:
        BaseModel (_type_): _description_
    """

    question: str
    additional_context: Union[str, None] = ""
    language: Optional[str] = "english"
    domain_name: Optional[str] = "supply_chain_management"


class PreTracks(BaseModel):
    """
    Data Validation of inputs for pre tracks.

    Args:
        BaseModel (_type_): _description_
    """

    user_id: str
    context_id: int
    question: str
    db_conn: Optional[dict] = None


class PostTracks(BaseModel):
    """
    Data Validation of inputs for post tracks.

    Args:
        BaseModel (_type_): _description_
    """

    user_id: str
    context_id: int
    chat_id: int
    content: dict
    question: str
    data_name: str
    db_conn: Optional[dict] = None
