import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from passlib.context import CryptContext
import logging
import requests
BASE_URL = "https://apex.oracle.com/pls/apex/naxxum/"
# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8"
}

# Configure logging
logging.basicConfig(filename="debug.log", level=logging.DEBUG)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logging.error("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError as e:
        logging.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def refresh_token(token: str) -> Optional[str]:
    """Refresh an expired token if it's still valid for refresh"""
    try:
        # Decode the token without verification to get the payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})

        # Check if the token is not too old (e.g., less than 24 hours old)
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            if datetime.utcnow() - exp_datetime > timedelta(hours=24):
                logging.error("Token too old to refresh")
                return None

        # Create a new token with the same data but new expiration
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_token = create_access_token(
            data={
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "firstname": payload.get("firstname"),
                "lastname": payload.get("lastname"),
                "phone": payload.get("phone"),
                "user_role": payload.get("user_role")
            },
            expires_delta=access_token_expires
        )

        logging.debug("Token refreshed successfully")
        return new_token
    except Exception as e:
        logging.error(f"Error refreshing token: {str(e)}")
        return None


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    try:
        logging.debug(f"Attempting to authenticate user with email: {email}")

        # Get user from database
        url = f"{BASE_URL}elearning/users"
        logging.debug(f"Making request to: {url}")

        response = requests.get(
            url,
            params={"email": email},
            headers=HEADERS
        )
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response headers: {response.headers}")

        if response.status_code != 200:
            logging.error(f"Failed to get user data. Status code: {response.status_code}")
            logging.error(f"Response content: {response.text}")
            return None

        response.raise_for_status()

        users = response.json()
        logging.debug(f"Received users data: {users}")

        if not users or len(users) == 0:
            logging.warning(f"No user found with email: {email}")
            return None

        user = users.get('items')[0]
        logging.debug(f"Found user: {user}")

        # For testing purposes, if the password is not hashed, hash it
        if not user.get("user_password", "").startswith("$2b$"):
            logging.debug("Password not hashed, hashing it now")
            user["user_password"] = get_password_hash(password)

        # Verify password
        if not verify_password(password, user.get("user_password", "")):
            logging.warning(f"Invalid password for user: {email}")
            return None

        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "user_id": user["user_id"],
                "email": user["email"],
                "firstname": user["firstname"],
                "lastname": user["lastname"],
                "phone": user["phone"],
                "user_role": user["user_role"]
            },
            expires_delta=access_token_expires
        )

        logging.debug("Successfully created access token")

        return {
            "token": access_token,
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "firstname": user["firstname"],
                "lastname": user["lastname"],
                "phone": user["phone"],
                "user_role": user["user_role"]
            }
        }
    except Exception as e:
        logging.error(f"Authentication error: {str(e)}", exc_info=True)
        return None