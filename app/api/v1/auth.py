from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import httpx
from httpx_oauth.clients.google import GoogleOAuth2

from app.db import crud
from app.db.database import get_db
from app.auth import jwt
from app.auth.schemas import UserCreate, User, Token
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.db import models
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Google OAuth2 Client Setup ---
# This needs to be defined at the top level of the module
google_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)

# === Local Authentication ===

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)) -> models.User:
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    # Also check if email is taken, as it should be unique
    if crud.get_user_by_email(db, email=user.email):
         raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@router.post("/token", response_model=Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> dict:
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not user.hashed_password or not jwt.verify_password(form_data.password, user.hashed_password):
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


# === Google OAuth2 Authentication (THE MISSING PIECE) ===
@router.get("/login/google", name="auth:google_login")
async def login_google(request: Request):
    """
    Redirects the user to Google's authentication page.
    """
    # --- THIS IS THE NEW, SIMPLIFIED LOGIC ---
    if settings.GOOGLE_OAUTH_REDIRECT_URI:
        # If a specific redirect URI is configured (for Codespaces), use it directly.
        redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    else:
        # Otherwise, fall back to FastAPI's request-based URL generation (for localhost).
        redirect_uri = request.url_for("auth:google_callback")

    return await google_client.get_authorization_url(
        redirect_uri=redirect_uri,
        scope=["email", "profile"],
    )

@router.get("/callback/google", name="auth:google_callback")

async def callback_google(request: Request, db: Session = Depends(get_db)): # 'request' is needed here for query_params
    try:
        redirect_uri = f"{settings.PUBLIC_API_URL}/api/v1/"
        async with httpx.AsyncClient() as client:
            token_data = await google_client.get_access_token(request.query_params["code"], redirect_uri, client)
            user_info = await google_client.get_id_email(token_data["access_token"], client)
    
        email = user_info["email"]
        social_id = user_info["sub"]
        full_name = user_info.get("name", "")

        db_user = crud.get_user_by_social_id(db, provider="google", social_id=social_id)
        if not db_user:
            # If no user with this social ID, check if the email is already in use by another account
            if crud.get_user_by_email(db, email=email):
                # Redirect with an error message to the frontend
                error_url = f"{settings.FRONTEND_URL}?error=email_exists"
                return RedirectResponse(url=error_url)

            db_user = crud.create_oauth_user(db, email=email, full_name=full_name, provider="google", social_id=social_id)
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.create_access_token(
            data={"sub": db_user.username}, expires_delta=access_token_expires
        )

        redirect_url = f"{settings.FRONTEND_URL}?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"An error occurred during Google authentication: {e}", exc_info=True)
        error_url = f"{settings.FRONTEND_URL}?error=oauth_failed"
        return RedirectResponse(url=error_url)


# === User Management ===

@router.get("/users/me", response_model=User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return current_user

@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete the currently authenticated user's account."""
    logger.info(f"User '{current_user.username}' (ID: {current_user.id}) has requested account deletion.")
    crud.delete_user(db, user_id=current_user.id)
    logger.info(f"Successfully deleted account for user '{current_user.username}'.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)