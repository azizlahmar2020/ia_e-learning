from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from features.cours_management.memory_course.conversation_memory import ConversationMemory

from .auth import authenticate_user, verify_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
conversation_memory = ConversationMemory()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class Token(BaseModel):
    token: str
    user: dict

class LoginCredentials(BaseModel):
    email: str
    password: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token)
    if not token_data:
        logging.error("Invalid token in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Return the user data from the token
    return token_data

@router.post("/login")
async def login(credentials: LoginCredentials):
    logger.debug(f"Login attempt for email: {credentials.email}")
    try:
        user_data = await authenticate_user(credentials.email, credentials.password)
        if not user_data:
            logger.warning(f"Authentication failed for email: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        logger.debug(f"Login successful for user: {user_data['user']['email']}")
        return user_data
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

@router.get("/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
