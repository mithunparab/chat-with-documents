from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db import crud
from app.db.database import get_db
from app.auth import jwt
from app.auth.schemas import UserCreate, User, Token
from app.core.config import settings

router = APIRouter()

@router.post("/signup", response_model=User)
def signup(
    user: UserCreate,
    db: Session = Depends(get_db)
) -> User:
    """
    Register a new user.

    Args:
        user (UserCreate): User registration data.
        db (Session): Database session.

    Returns:
        User: The created user object.

    Raises:
        HTTPException: If the username is already registered.
    """
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@router.post("/token", response_model=Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> dict:
    """
    Authenticate user and return an access token.

    Args:
        db (Session): Database session.
        form_data (OAuth2PasswordRequestForm): Form data containing username and password.

    Returns:
        dict: Access token and token type.

    Raises:
        HTTPException: If authentication fails.
    """
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not jwt.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# TODO: Add endpoints for password reset and user profile management.