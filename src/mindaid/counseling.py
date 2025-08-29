"""
Counseling API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .models import CounselingRequest, CounselingResponse
from .ml_models import get_counseling_response
from .database import get_db
from .auth import get_current_user
from datetime import date
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/counsel", response_class=HTMLResponse)
async def counsel_page(request: Request):
    """Counseling page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return templates.TemplateResponse("landing.html", {"request": request})

    # Update counseling date in database
    conn = get_db()
    cursor = conn.cursor()
    today = str(date.today())
    cursor.execute(
        "UPDATE users SET date = ? WHERE username = ?",
        (today, username)
    )
    conn.commit()
    conn.close()

    return templates.TemplateResponse("counsel.html", {"request": request, "username": username})

@router.post("/counsel/chat", response_model=CounselingResponse)
async def counsel_chat(counsel_request: CounselingRequest, request: Request):
    """Handle counseling chat interaction"""
    try:
        username = get_current_user(request)
    except HTTPException:
        username = "guest"
    
    user_input = counsel_request.user_input
    session_id = counsel_request.session_id or f"counsel_{username}"

    try:
        # Get AI response
        ai_response = get_counseling_response(user_input, session_id)

        # Save conversation history to database
        conn = get_db()
        cursor = conn.cursor()

        # Get current history
        cursor.execute("SELECT history FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        current_history = result[0] if result and result[0] else ""

        # Append new conversation
        new_entry = f"User: {user_input} | AI: {ai_response}"
        updated_history = current_history + " | " + new_entry if current_history else new_entry

        # Update database
        cursor.execute(
            "UPDATE users SET history = ? WHERE username = ?",
            (updated_history, username)
        )
        conn.commit()
        conn.close()

        return CounselingResponse(
            message=ai_response,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Error in counseling chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """User history page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return templates.TemplateResponse("landing.html", {"request": request})

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT history FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            # Clean up the history string
            history = result[0]
            if history.startswith("('") and history.endswith("',)"):
                history = history[2:-3]
            elif history.startswith("'") and history.endswith("'"):
                history = history[1:-1]
        else:
            history = "No conversation history available."

        return templates.TemplateResponse("history.html", {
            "request": request,
            "input_string": history
        })

    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return templates.TemplateResponse("history.html", {
            "request": request,
            "input_string": "Error retrieving history."
        })

# @router.get("/get")
# async def get_counseling_response(msg: str, request: Request):
#     """Handle counseling chat interaction via GET request (for frontend compatibility)"""
#     try:
#         username = get_current_user(request)
#     except HTTPException:
#         username = "guest"
#     
#     user_input = msg
#     session_id = f"counsel_{username}"
# 
#     try:
#         # Get AI response
#         ai_response = get_counseling_response(user_input, session_id)
# 
#         # Save conversation history to database
#         conn = get_db()
#         cursor = conn.cursor()
# 
#         # Get current history
#         cursor.execute("SELECT history FROM users WHERE username = ?", (username,))
#         result = cursor.fetchone()
#         current_history = result[0] if result and result[0] else ""
# 
#         # Append new conversation
#         new_entry = f"User: {user_input} | AI: {ai_response}"
#         updated_history = current_history + " | " + new_entry if current_history else new_entry
# 
#         # Update database
#         cursor.execute(
#             "UPDATE users SET history = ? WHERE username = ?",
#             (updated_history, username)
#         )
#         conn.commit()
#         conn.close()
# 
#         return ai_response
# 
#     except Exception as e:
#         logger.error(f"Error in counseling chat: {e}")
#         return "I'm sorry, I'm having trouble responding right now. Please try again later."

# @router.get("/get")
# async def get_counseling_response(msg: str, request: Request):
#     """Handle counseling chat interaction via GET request (for frontend compatibility)"""
#     try:
#         username = get_current_user(request)
#     except HTTPException:
#         username = "guest"
#     
#     user_input = msg
#     session_id = f"counsel_{username}"
# 
#     try:
#         # Get AI response
#         ai_response = get_counseling_response(user_input, session_id)
# 
#         # Save conversation history to database
#         conn = get_db()
#         cursor = conn.cursor()
# 
#         # Get current history
#         cursor.execute("SELECT history FROM users WHERE username = ?", (username,))
#         result = cursor.fetchone()
#         current_history = result[0] if result and result[0] else ""
# 
#         # Append new conversation
#         new_entry = f"User: {user_input} | AI: {ai_response}"
#         updated_history = current_history + " | " + new_entry if current_history else new_entry
# 
#         # Update database
#         cursor.execute(
#             "UPDATE users SET history = ? WHERE username = ?",
#             (updated_history, username)
#         )
#         conn.commit()
#         conn.close()
# 
#         return ai_response
# 
#     except Exception as e:
#         logger.error(f"Error in counseling chat: {e}")
#         return "I'm sorry, I'm having trouble responding right now. Please try again later."

# Export router with expected name
counseling_router = router
