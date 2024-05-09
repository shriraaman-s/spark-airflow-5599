import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class ErrorEntity(BaseModel):
    """
    Represents an error entity.

    Attributes:
        timestamp (datetime): The timestamp when the error occurred.
        status (int): The status code of the error.
        error (str): The error type or category.
        message (str): The error message.
        path (str): The path or URL associated with the error.
    """

    timestamp: datetime
    status: int
    error: str
    message: str
    path: str


class BaseRequest(BaseModel):
    """
    Represents a base request object.

    Attributes:
        context_id (str): The context ID.
        chat_id (str): The chat ID.
        user_id (str): The user ID.
        session_id (str): The session ID.
        role (str): The role of the request (user or assistant).
        seq (int): The sequence number.
        content (Any): The request entity.
        chat_history (List): The chat history.
    """

    context_id: str
    chat_id: str
    user_id: str
    session_id: str
    role: str  # user | assistant
    seq: int
    content: Any  # Request Entity will come here
    chat_history: List


class BaseResponse(BaseModel):
    """
    Represents the base response for API calls.

    Attributes:
        success (bool, optional): Indicates whether the API call was successful.
        error (ErrorEntity, optional): Contains error details if the API call was unsuccessful.
        content (Any, optional): Contains the response entity.
    """

    success: Optional[bool]
    error: Optional[ErrorEntity]  # if success is false
    content: Optional[Any]  # Response Entity will come here


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that extends the functionality of the base JSONEncoder class.
    It provides custom serialization for datetime objects and objects with a __dict__ attribute.
    """

    def default(self, obj):
        """
        Override the default method to provide custom serialization for specific object types.

        Args:
            obj: The object to be serialized.

        Returns:
            The serialized representation of the object.

        """
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)
