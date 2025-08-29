"""
Authentication and authorization utilities using bcrypt for secure password hashing
"""

import os
import bcrypt
from fastapi import HTTPException, Request, Response
import secrets
import logging
import json
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt with automatic salt generation
    Returns the hashed password as a string
    """
    try:
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise HTTPException(status_code=500, detail="Password hashing failed")

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify password against hash using bcrypt
    Returns True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def generate_secret_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure secret key
    """
    return secrets.token_hex(length)

def get_current_user(request: Request):
    """
    Get current user from session cookie
    In production, use proper JWT tokens or session management
    """
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        session_data = json.loads(session_cookie)
        username = session_data.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid session")
        return username
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid session")

def create_session_response(username: str, redirect_url: str = "/home"):
    """
    Create a response with session cookie set
    """
    from fastapi.responses import RedirectResponse
    
    session_data = {
        "username": username,
        "created_at": datetime.now().isoformat()
    }
    
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="session",
        value=json.dumps(session_data),
        httponly=True,
        max_age=3600,  # 1 hour
        expires=3600,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    return response

def clear_session_response(redirect_url: str = "/"):
    """
    Create a response with session cookie cleared
    """
    from fastapi.responses import RedirectResponse
    
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.delete_cookie(key="session")
    return response

def authenticate_user(username: str, password: str, db_conn) -> bool:
    """
    Authenticate user against database using secure password verification
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT password FROM users WHERE username = ?",
            (username,)
        )

        result = cursor.fetchone()
        if not result:
            return False

        stored_hash = result[0]
        return verify_password(password, stored_hash)

    except Exception as e:
        logger.error(f"Error authenticating user {username}: {e}")
        return False

def authenticate_doctor(username: str, password: str, db_conn) -> bool:
    """
    Authenticate doctor against database using secure password verification
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT password FROM doctors WHERE username = ?",
            (username,)
        )

        result = cursor.fetchone()
        if not result:
            return False

        stored_hash = result[0]
        return verify_password(password, stored_hash)

    except Exception as e:
        logger.error(f"Error authenticating doctor {username}: {e}")
        return False

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength requirements (simplified - just check if not empty)
    Returns (is_valid, message)
    """
    if len(password) < 1:
        return False, "Password is required"
    return True, "Password is valid"

def get_secret_key() -> str:
    """
    Get the application secret key from environment
    """
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        logger.warning("SECRET_KEY not found in environment, generating temporary key")
        secret_key = generate_secret_key()
    return secret_key
