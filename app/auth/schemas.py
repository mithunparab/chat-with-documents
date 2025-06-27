from pydantic import BaseModel
from typing import Optional
import uuid

class UserBase(BaseModel):
    """
    Base schema for user data.

    Attributes:
        username (str): The username of the user.
    """
    username: str

class UserCreate(UserBase):
    """
    Schema for creating a new user.

    Attributes:
        password (str): The user's password.
    """
    password: str

class User(UserBase):
    """
    Schema representing a user.

    Attributes:
        id (uuid.UUID): The unique identifier of the user.
        username (str): The username of the user.
    """
    id: uuid.UUID

    class Config:
        from_attributes = True

class Token(BaseModel):
    """
    Schema for authentication token.

    Attributes:
        access_token (str): The access token string.
        token_type (str): The type of the token.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Schema for token data.

    Attributes:
        username (Optional[str]): The username associated with the token, if any.
    """
    username: Optional[str] = None

# TODO: Add more fields and validation as needed for user and token schemas.