import time
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt as authlib_jwt

from app.db import crud, models
from app.db.database import get_db
from app.auth import jwt
from app.auth.schemas import UserCreate, User, Token
from app.core.config import settings
from app.core.dependencies import get_current_user


router = APIRouter()
oauth = OAuth()

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

def generate_apple_client_secret():
    """Generates the client_secret JWT for Apple Sign-In."""
    if not all([settings.APPLE_TEAM_ID, settings.APPLE_CLIENT_ID, settings.APPLE_KEY_ID, settings.APPLE_PRIVATE_KEY]):
        return None
    
    header = {'alg': 'ES256', 'kid': settings.APPLE_KEY_ID}
    payload = {
        'iss': settings.APPLE_TEAM_ID,
        'iat': int(time.time()),
        'exp': int(time.time()) + 86400 * 180,  # 180 days
        'aud': 'https://appleid.apple.com',
        'sub': settings.APPLE_CLIENT_ID,
    }
    # Authlib expects bytes for the key
    key = settings.APPLE_PRIVATE_KEY.encode('utf-8')
    return authlib_jwt.encode(header, payload, key)

if all([settings.APPLE_CLIENT_ID, settings.APPLE_TEAM_ID, settings.APPLE_KEY_ID, settings.APPLE_PRIVATE_KEY]):
    oauth.register(
        name='apple',
        client_id=settings.APPLE_CLIENT_ID,
        client_secret=generate_apple_client_secret(),
        server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid name email',
            'response_mode': 'form_post', # Apple requires this
        }
    )

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)) -> models.User:
    """Register a new user with email and password."""
    if crud.get_user_by_username(db, username=user.username):
        raise HTTPException(status_code=400, detail="Username is already registered")
    if crud.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email is already registered")
    
    return crud.create_user(db=db, user=user)

@router.post("/token", response_model=Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """Authenticate with username/password and return an access token."""
    user = crud.get_user_by_username(db, username=form_data.username)
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password, or user signed up with a different method.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not jwt.verify_password(form_data.password, user.hashed_password):
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

@router.get("/login/{provider}")
async def login_via_provider(request: Request, provider: str):
    """Redirects the user to the OAuth provider's login page."""
    if provider not in oauth._clients:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not supported.")

    redirect_uri = request.url_for('auth_callback', provider=provider)
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)

@router.api_route("/auth/{provider}", methods=["GET", "POST"], name="auth_callback")
async def auth_callback(request: Request, provider: str, db: Session = Depends(get_db)):
    """
    Callback endpoint for OAuth providers. Receives authorization token,
    fetches user info, creates/logs in the user, and redirects to frontend.
    """
    if provider not in oauth._clients:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not supported.")

    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    
    if provider == 'google':
        user_info = await client.parse_id_token(token)
    elif provider == 'apple':
        # Apple's user info is in the id_token
        user_info = await client.parse_id_token(token)
        # Apple may not return name on subsequent logins, so we need to handle that
        # It's part of the 'user' key in the form data on first login
        form_data = await request.form()
        if 'user' in form_data:
            import json
            apple_user = json.loads(form_data['user'])
            user_info['name'] = f"{apple_user['name'].get('firstName', '')} {apple_user['name'].get('lastName', '')}".strip()

    else:
        raise HTTPException(status_code=400, detail="Provider data parsing not implemented.")
    
    # Add provider to info dict
    user_info['provider'] = provider

    # Create or retrieve user from database
    db_user = crud.get_or_create_oauth_user(db, user_info)

    # Create our application's JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )

    # Redirect user to frontend with the token
    redirect_url = f"{settings.FRONTEND_URL}?token={access_token}"
    return RedirectResponse(url=redirect_url)

@router.get("/users/me", response_model=User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Get current authenticated user's details."""
    return current_user