"""
Diagnosis API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .models import DiagnosisRequest, DiagnosisResponse
from .ml_models import predict_disorder
from .database import get_db
from .auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Session state (in production, use Redis or database)
diagnosis_sessions = {}

@router.get("/diagnosis", response_class=HTMLResponse)
async def diagnosis_page(request: Request):
    """Diagnosis page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return templates.TemplateResponse("landing.html", {"request": request})

    # Initialize diagnosis session
    session_key = f"diagnosis_{username}"
    diagnosis_sessions[session_key] = {
        "step": 1,
        "user_input": "",
        "score": 0,
        "disorder": None
    }

    return templates.TemplateResponse("diagnosis.html", {"request": request, "username": username})

@router.post("/diagnosis/chat", response_model=DiagnosisResponse)
async def diagnosis_chat(diagnosis_request: DiagnosisRequest, request: Request):
    """Handle diagnosis chat interaction"""
    try:
        username = get_current_user(request)
    except HTTPException:
        username = "guest"
    
    session_key = f"diagnosis_{username}"

    if session_key not in diagnosis_sessions:
        diagnosis_sessions[session_key] = {
            "step": 1,
            "user_input": "",
            "score": 0,
            "disorder": None
        }

    session = diagnosis_sessions[session_key]
    user_input = diagnosis_request.user_input
    step = diagnosis_request.step

    try:
        if step == 1:
            # First question
            session["user_input"] += user_input
            session["step"] = 2
            return DiagnosisResponse(
                message="Can you share any recent events or experiences that might have triggered these feelings or symptoms?",
                completed=False
            )

        elif step == 2:
            # Second question
            session["user_input"] += " " + user_input
            session["step"] = 3
            return DiagnosisResponse(
                message="Have you experienced any significant traumas in the past, or do you have any habits or behaviors that you think might be affecting your mental health?",
                completed=False
            )

        elif step == 3:
            # Predict disorder
            session["user_input"] += " " + user_input
            disorder = predict_disorder(session["user_input"])
            session["disorder"] = disorder
            session["step"] = 4

            # Save to database
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET disorder = ? WHERE username = ?",
                (disorder, username)
            )
            conn.commit()
            conn.close()

            # Return appropriate questionnaire based on disorder
            if disorder == "Anxiety":
                return DiagnosisResponse(
                    message=f"You have: {disorder}. Now could you answer a few symptoms related questions to help diagnose the severity? Answer 0: Not at all, 1: Several days, 2: More than half the days, 3: Nearly every day. Feeling nervous, anxious, or on edge?",
                    disorder=disorder,
                    completed=False
                )
            elif disorder == "PTSD":
                return DiagnosisResponse(
                    message=f"You have: {disorder}. Have you ever experienced a traumatic event? (yes/no)",
                    disorder=disorder,
                    completed=False
                )
            elif disorder == "Depression":
                return DiagnosisResponse(
                    message=f"You have: {disorder}. Little interest or pleasure in doing things? (0-3 scale)",
                    disorder=disorder,
                    completed=False
                )
            elif disorder == "Addiction":
                return DiagnosisResponse(
                    message=f"You have: {disorder}. How often do you have strong urges or cravings? (0: Never, 1: Sometimes, 2: Often, 3: Always)",
                    disorder=disorder,
                    completed=False
                )

        elif step >= 4:
            # Handle questionnaire responses
            disorder = session["disorder"]
            return await handle_questionnaire_response(username, disorder, user_input, session)

    except Exception as e:
        logger.error(f"Error in diagnosis chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def handle_questionnaire_response(username: str, disorder: str, user_input: str, session: dict):
    """Handle questionnaire responses based on disorder"""
    step = session["step"]
    score = session["score"]

    if disorder == "Anxiety":
        score += int(user_input)
        questions = [
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid, as if something awful might happen"
        ]

        if step - 3 < len(questions):
            session["step"] += 1
            session["score"] = score
            return DiagnosisResponse(
                message=questions[step - 4],
                completed=False
            )
        else:
            # Calculate severity
            severity = calculate_anxiety_severity(score)
            session["step"] = -1

            # Save to database
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET severity = ? WHERE username = ?",
                (severity, username)
            )
            conn.commit()
            conn.close()

            return DiagnosisResponse(
                message=f"The severity of your Anxiety Disorder is {severity}.",
                disorder=disorder,
                severity=severity,
                completed=True
            )

    elif disorder == "PTSD":
        if step == 4:
            if user_input.lower() in ["no", "n"]:
                severity = "Minimal"
                session["step"] = -1
                save_severity(username, severity)
                return DiagnosisResponse(
                    message="PTSD requires a traumatic event. Consider consulting a counselor.",
                    disorder=disorder,
                    severity=severity,
                    completed=True
                )
            else:
                session["step"] = 5
                return DiagnosisResponse(
                    message="Had nightmares about it or thought about it when you did not want to?",
                    completed=False
                )
        else:
            # Handle PTSD questionnaire
            score += 1 if user_input.lower() in ["yes", "y"] else 0
            questions = [
                "Tried hard not to think about it or went out of your way to avoid situations that reminded you of it?",
                "Were constantly on guard, watchful or easily startled?",
                "Felt numb or detached from others, activities, or your surroundings?",
                "Felt guilty or unable to stop blaming yourself or others?"
            ]

            if step - 4 < len(questions):
                session["step"] += 1
                session["score"] = score
                return DiagnosisResponse(
                    message=questions[step - 5],
                    completed=False
                )
            else:
                severity = "Moderate/Severe" if score >= 3 else "Mild"
                session["step"] = -1
                save_severity(username, severity)
                return DiagnosisResponse(
                    message=f"The severity of your PTSD is {severity}.",
                    disorder=disorder,
                    severity=severity,
                    completed=True
                )

    # Similar handling for Depression and Addiction...
    return DiagnosisResponse(
        message="Diagnosis completed. Please consult a healthcare professional.",
        completed=True
    )

def calculate_anxiety_severity(score: int) -> str:
    """Calculate anxiety severity based on GAD-7 score"""
    if score <= 4:
        return "Minimal"
    elif score <= 9:
        return "Mild"
    elif score <= 14:
        return "Moderate"
    else:
        return "Severe"

def save_severity(username: str, severity: str):
    """Save severity to database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET severity = ? WHERE username = ?",
        (severity, username)
    )
    conn.commit()
    conn.close()

# @router.get("/get")
# async def get_diagnosis_response(msg: str, request: Request):
#     """Handle diagnosis chat interaction via GET request (for frontend compatibility)"""
#     try:
#         username = get_current_user(request)
#     except HTTPException:
#         username = "guest"
#     
#     session_key = f"diagnosis_{username}"
#
#     # Initialize session if it doesn't exist
#     if session_key not in diagnosis_sessions:
#         diagnosis_sessions[session_key] = {
#             "step": 1,
#             "user_input": "",
#             "score": 0,
#             "disorder": None
#         }
#
#     session = diagnosis_sessions[session_key]
#     user_input = msg
#     step = session["step"]
#
#     try:
#         if step == 1:
#             # First question
#             session["user_input"] += user_input
#             session["step"] = 2
#             return "Can you share any recent events or experiences that might have triggered these feelings or symptoms?"
#
#         elif step == 2:
#             # Second question
#             session["user_input"] += " " + user_input
#             session["step"] = 3
#             return "Have you experienced any significant traumas in the past, or do you have any habits or behaviors that you think might be affecting your mental health?"
#
#         elif step == 3:
#             # Predict disorder
#             session["user_input"] += " " + user_input
#             disorder = predict_disorder(session["user_input"])
#             session["disorder"] = disorder
#             session["step"] = 4
#
#             # Save to database
#             conn = get_db()
#             cursor = conn.cursor()
#             cursor.execute(
#                 "UPDATE users SET disorder = ? WHERE username = ?",
#                 (disorder, username)
#             )
#             conn.commit()
#             conn.close()
#
#             # Return appropriate first questionnaire question based on disorder
#             if disorder == "Anxiety":
#                 return f"You have: {disorder}. Now could you answer a few symptoms related questions to help diagnose the severity? Answer 0: Not at all, 1: Several days, 2: More than half the days, 3: Nearly every day. Feeling nervous, anxious, or on edge? (0-3)"
#             elif disorder == "PTSD":
#                 return f"You have: {disorder}. Have you ever experienced a traumatic event? (yes/no)"
#             elif disorder == "Depression":
#                 return f"You have: {disorder}. Little interest or pleasure in doing things? (0-3 scale)"
#             elif disorder == "Addiction":
#                 return f"You have: {disorder}. How often do you have strong urges or cravings? (0: Never, 1: Sometimes, 2: Often, 3: Always)"
#             else:
#                 return f"You have: {disorder}. Diagnosis completed. Please consult a healthcare professional."
#
#         elif step >= 4:
#             # Handle questionnaire responses
#             disorder = session["disorder"]
#             return await handle_questionnaire_response_simple(username, disorder, user_input, session)
#
#     except Exception as e:
#         logger.error(f"Error in diagnosis chat: {e}")
#         return "I'm sorry, I'm having trouble with the diagnosis right now. Please try again later."

# async def handle_questionnaire_response_simple(username: str, disorder: str, user_input: str, session: dict):
#     """Simplified questionnaire response handler for GET endpoint"""
#     step = session["step"]
#     score = session["score"]
#
#     if disorder == "Anxiety":
#         try:
#             score += int(user_input)
#         except ValueError:
#             return "Please provide a number between 0-3."
#
#         questions = [
#             "Not being able to stop or control worrying (0-3)",
#             "Worrying too much about different things (0-3)",
#             "Trouble relaxing (0-3)",
#             "Being so restless that it is hard to sit still (0-3)",
#             "Becoming easily annoyed or irritable (0-3)",
#             "Feeling afraid, as if something awful might happen (0-3)"
#         ]
#
#         if step - 3 < len(questions):
#             session["step"] += 1
#             session["score"] = score
#             return questions[step - 4]
#         else:
#             severity = calculate_anxiety_severity(score)
#             session["step"] = -1
#             save_severity(username, severity)
#             return f"The severity of your anxiety is {severity}. Diagnosis completed."
#
#     elif disorder == "PTSD":
#         if step == 4:
#             if user_input.lower() in ['yes', 'y']:
#                 session["step"] += 1
#                 return "Tried hard not to think about it or went out of your way to avoid situations that reminded you of it? (yes/no)"
#             else:
#                 return "Since you haven't experienced trauma, PTSD diagnosis is not applicable. Please consult a healthcare professional."
#         
#         questions = [
#             "Were constantly on guard, watchful or easily startled? (yes/no)",
#             "Felt numb or detached from others, activities, or your surroundings? (yes/no)",
#             "Felt guilty or unable to stop blaming yourself or others? (yes/no)"
#         ]
#         
#         if step - 4 < len(questions):
#             session["step"] += 1
#             return questions[step - 5]
#         else:
#             severity = "Moderate/Severe" if score >= 2 else "Mild"
#             session["step"] = -1
#             save_severity(username, severity)
#             return f"The severity of your PTSD is {severity}. Diagnosis completed."
#
#     elif disorder == "Depression":
#         try:
#             score += int(user_input)
#         except ValueError:
#             return "Please provide a number between 0-3."
#
#         questions = [
#             "Feeling down, depressed, or hopeless? (0-3)",
#             "Trouble falling or staying asleep, or sleeping too much? (0-3)",
#             "Feeling tired or having little energy? (0-3)",
#             "Poor appetite or overeating? (0-3)",
#             "Feeling bad about yourself or that you are a failure? (0-3)",
#             "Trouble concentrating on things? (0-3)"
#         ]
#
#         if step - 3 < len(questions):
#             session["step"] += 1
#             session["score"] = score
#             return questions[step - 4]
#         else:
#             severity = "Moderate/Severe" if score >= 10 else "Mild"
#             session["step"] = -1
#             save_severity(username, severity)
#             return f"The severity of your depression is {severity}. Diagnosis completed."
#
#     elif disorder == "Addiction":
#         try:
#             score += int(user_input)
#         except ValueError:
#             return "Please provide a number between 0-3."
#
#         questions = [
#             "Spent a lot of time trying to get, use, or recover from use? (0-3)",
#             "Wanted to cut down or stop but couldn't? (0-3)",
#             "Activities given up or reduced because of use? (0-3)",
#             "Continued use despite problems? (0-3)",
#             "Neglected responsibilities? (0-3)",
#             "Used despite health/social problems? (0-3)"
#         ]
#
#         if step - 3 < len(questions):
#             session["step"] += 1
#             session["score"] = score
#             return questions[step - 4]
#         else:
#             severity = "Moderate/Severe" if score >= 4 else "Mild"
#             session["step"] = -1
#             save_severity(username, severity)
#             return f"The severity of your addiction is {severity}. Diagnosis completed."
#
#     return "Diagnosis completed. Please consult a healthcare professional."

# Export router with expected name
diagnosis_router = router

@router.get("/get")
async def get_diagnosis_response(msg: str, request: Request):
    """Handle diagnosis chat interaction via GET request (for frontend compatibility)"""
    try:
        username = get_current_user(request)
    except HTTPException:
        username = "guest"
    
    session_key = f"diagnosis_{username}"

    # Initialize session if it doesn't exist
    if session_key not in diagnosis_sessions:
        diagnosis_sessions[session_key] = {
            "step": 1,
            "user_input": "",
            "score": 0,
            "disorder": None
        }

    session = diagnosis_sessions[session_key]
    user_input = msg
    step = session["step"]

#     try:
#         if step == 1:
#             # First question
#             session["user_input"] += user_input
#             session["step"] = 2
#             return "Can you share any recent events or experiences that might have triggered these feelings or symptoms?"

#         elif step == 2:
#             # Second question
#             session["user_input"] += " " + user_input
#             session["step"] = 3
#             return "Have you experienced any significant traumas in the past, or do you have any habits or behaviors that you think might be affecting your mental health?"

#         elif step == 3:
#             # Predict disorder
#             session["user_input"] += " " + user_input
#             disorder = predict_disorder(session["user_input"])
#             session["disorder"] = disorder
#             session["step"] = 4

#             # Save to database
#             conn = get_db()
#             cursor = conn.cursor()
#             cursor.execute(
#                 "UPDATE users SET disorder = ? WHERE username = ?",
#                 (disorder, username)
#             )
#             conn.commit()
#             conn.close()

#             # Return appropriate first questionnaire question based on disorder
#             if disorder == "Anxiety":
#                 return f"You have: {disorder}. Now could you answer a few symptoms related questions to help diagnose the severity? Answer 0: Not at all, 1: Several days, 2: More than half the days, 3: Nearly every day. Feeling nervous, anxious, or on edge? (0-3)"
#             elif disorder == "PTSD":
#                 return f"You have: {disorder}. Have you ever experienced a traumatic event? (yes/no)"
#             elif disorder == "Depression":
#                 return f"You have: {disorder}. Little interest or pleasure in doing things? (0-3 scale)"
#             elif disorder == "Addiction":
#                 return f"You have: {disorder}. How often do you have strong urges or cravings? (0: Never, 1: Sometimes, 2: Often, 3: Always)"
#             else:
#                 return f"You have: {disorder}. Diagnosis completed. Please consult a healthcare professional."

# #         elif step >= 4:
# #             # Handle questionnaire responses
# #             disorder = session["disorder"]
# #             return await handle_questionnaire_response_simple(username, disorder, user_input, session)

# #     except Exception as e:
# #         logger.error(f"Error in diagnosis chat: {e}")
# #         return "I'm sorry, I'm having trouble with the diagnosis right now. Please try again later."

# Export router with expected name
diagnosis_router = router
