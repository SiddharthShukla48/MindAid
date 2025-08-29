"""
MindAid - Mental Health Diagnosis and Counseling Platform
FastAPI Application
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import hashlib
from datetime import date
from dotenv import load_dotenv
import logging
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from .database import init_db, get_db
from .models import User, Doctor
from .auth import get_current_user, authenticate_user, authenticate_doctor, hash_password, validate_password_strength, create_session_response, clear_session_response
from .diagnosis import diagnosis_router, get_diagnosis_response
from .counseling import counseling_router, get_counseling_response
from .ml_models import load_diagnosis_model, load_vector_store

# Global variables for ML models
diagnosis_model = None
tokenizer = None
vector_store = None

# Global session state (in production, use Redis or database)
user_sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global diagnosis_model, tokenizer, vector_store

    # Startup
    logger.info("Starting MindAid application...")

    # Initialize database
    init_db()

    # Load ML models
    try:
        diagnosis_model, tokenizer = load_diagnosis_model()
        vector_store = load_vector_store()
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ML models: {e}")

    yield

    # Shutdown
    logger.info("Shutting down MindAid application...")

# Create FastAPI app
app = FastAPI(
    title="MindAid",
    description="AI-Powered Mental Health Diagnosis and Counseling Platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers (keeping for additional API endpoints)
# app.include_router(diagnosis_router, prefix="/api", tags=["diagnosis"])
# app.include_router(counseling_router, prefix="/api", tags=["counseling"])

@app.get("/get")
async def get_response(msg: str, request: Request):
    """Handle chat responses for both diagnosis and counseling (for frontend compatibility)"""
    try:
        username = get_current_user(request)
    except HTTPException:
        username = "guest"
    
    # Get or initialize user session
    if username not in user_sessions:
        user_sessions[username] = {
            'InDiagnosis': False,
            'InCounselor': False,
            'total': 0,
            'userScore': 0,
            'userText_diagnosis': "",
            'predicted_class': None
        }
    
    session = user_sessions[username]
    
    try:
        # For diagnosis workflow
        if session['InDiagnosis'] and not session['InCounselor']:
            # Import the diagnosis model functions
            from .ml_models import predict_disorder
            
            # Step 1: Initial symptoms
            if session['total'] == 1:
                session['total'] += 1
                session['userText_diagnosis'] += msg
                return "Can you share any recent events or experiences that might have triggered these feelings or symptoms?"
            
            # Step 2: Triggers and background
            elif session['total'] == 2:
                session['total'] += 1
                session['userText_diagnosis'] += " " + msg
                return "Have you experienced any significant traumas in the past, or do you have any habits or behaviors that you think might be affecting your mental health?"
            
            # Step 3: Make prediction and start questionnaire
            elif session['total'] == 3:
                session['total'] += 1
                session['userText_diagnosis'] += " " + msg
                
                # Get prediction from BERT model
                disorder = predict_disorder(session['userText_diagnosis'])
                session['predicted_class'] = disorder
                
                # Save diagnosis to database
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
                    return "You have: " + disorder + "<br>" + "Now could please answer a few symptoms related questions, to help me diagnose the severity of you disorder? <br> Answer 0 : For Not At All <br> Answer 1: If several days <br> Answer 2: If More than half the days <br> Answer 3: If Nearly every day <br> <br>  Feeling nervous, anxious, or on edge ? <br><br> NOTE: Please provide Numerical Input !"
                elif disorder == "PTSD":
                    return "You have: " + disorder + "<br>" + "Now could please answer a few symptoms related questions, to help me diagnose the severity of you disorder? <br> NOTE: Please Answer in 'yes' or 'no' ! <br><br> Sometimes things happen to people that are unusually or especially frightening, horrible, or traumatic. <br> For example: <br> - A serious accident or fire <br> - A physical or sexual assualt or abuse <br> - Seeing someone getting killed or get seriously injured <br> - Having a loved one die through homicide or sucide <br><br> Have you ever experienced this kind of event? "
                elif disorder == "Depression":
                    return "You have: " + disorder + "<br>" + "Now could please answer a few symptoms related questions, to help me diagnose the severity of you disorder? <br> Answer 0 : For Not At All <br> Answer 1: If several days <br> Answer 2: If More than half the days <br> Answer 3: If Nearly every day <br> <br>Little interest or pleasure in doing things ? <br><br> NOTE: Please provide Numerical Input !"
                elif disorder == "Addiction":
                    return "You have: " + disorder + "<br>" + "Now could please answer a few symptoms related questions, to help me diagnose the severity of you disorder? <br> Answer 0 : For Not At All <br> Answer 1: For Sometimes <br> Answer 2: For Often <br> Answer 3: For Always <br> <br>  How often do you have strong urges or cravings to use the substance or engage in the behavior? <br><br> NOTE: Please provide Numerical input !"
            
            # Step 4+: Handle questionnaire responses based on disorder type
            elif session['total'] >= 4:
                predicted_class = session['predicted_class']
                
                if predicted_class == "Anxiety":
                    if msg in ['0', '1', '2', '3']:
                        if session['total'] == 4:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Not being able to stop or control worrying"
                        elif session['total'] == 5:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Worrying too much about different things"
                        elif session['total'] == 6:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Trouble relaxing"
                        elif session['total'] == 7:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Being so restless that it is hard to sit still"
                        elif session['total'] == 8:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Becoming easily annoyed or irritable"
                        elif session['total'] == 9:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Feeling afraid, as if something awful might happen"
                        elif session['total'] == 10:
                            session['userScore'] += int(msg)
                            session['total'] = -1
                            
                            # Calculate severity
                            conn = get_db()
                            cursor = conn.cursor()
                            
                            if 0 <= session['userScore'] <= 4:
                                severity = "Minimal"
                                message = "The Severity of your Anxiety Disorder is Minimal.<br>You can refer to professional help or You can also try our Anxiety Health Counsellor"
                            elif 5 <= session['userScore'] <= 9:
                                severity = "Mild"
                                message = "The Severity of your Anxiety Disorder is Mild.<br>You can refer to professional help or You can also try our Anxiety Health Counsellor"
                            elif 10 <= session['userScore'] <= 14:
                                severity = "Moderate"
                                message = "The Severity of your Anxiety Disorder is Moderate.<br>I recommend taking professional help. Along with that You can also try our Anxiety Health Counsellor"
                            else:
                                severity = "Severe"
                                message = "The Severity of your Anxiety Disorder is Severe.<br>You can try our Anxiety Health Counsellor, but I strongly recommend taking professional help"
                            
                            cursor.execute("UPDATE users SET severity = ? WHERE username = ?", (severity, username))
                            conn.commit()
                            conn.close()
                            return message
                    else:
                        return "Please Provide Answers in Required Format !"
                
                elif predicted_class == "Depression":
                    if msg in ['0', '1', '2', '3']:
                        if session['total'] == 4:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Feeling down, depressed, or hopeless"
                        elif session['total'] == 5:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Trouble falling or staying asleep, or sleeping too much"
                        elif session['total'] == 6:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Feeling tired or having little energy"
                        elif session['total'] == 7:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Poor appetite or overeating"
                        elif session['total'] == 8:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Feeling bad about yourself or that you are a failure or have let yourself or your family down"
                        elif session['total'] == 9:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Trouble concentrating on things, such as reading the newspaper or watching television"
                        elif session['total'] == 10:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Moving or speaking so slowly that other people could not have noticed. Or the opposite being so figety or restless that you have been moving around a lot more than usual"
                        elif session['total'] == 11:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "Thoughts that you would be better off dead, or of hurting yourself"
                        elif session['total'] == 12:
                            session['userScore'] += int(msg)
                            session['total'] = -1
                            
                            # Calculate severity
                            conn = get_db()
                            cursor = conn.cursor()
                            
                            if 0 <= session['userScore'] <= 4:
                                severity = "Minimal"
                                message = "The Severity of your Depression Disorder is Minimal.<br>You can refer to professional help or You can also try our Depression Health Counsellor"
                            elif 5 <= session['userScore'] <= 9:
                                severity = "Mild"
                                message = "The Severity of your Depression Disorder is Mild.<br>You can refer to professional help or You can also try our Depression Health Counsellor"
                            elif 10 <= session['userScore'] <= 14:
                                severity = "Moderate"
                                message = "The Severity of your Depression Disorder is Moderate.<br>I recommend taking professional help. Along with that You can also try our Depression Health Counsellor"
                            elif 15 <= session['userScore'] <= 19:
                                severity = "Moderately Severe"
                                message = "The Severity of your Depression Disorder is Moderately Severe.<br>You can try our Depression Health Counsellor, but I strongly recommend taking professional help"
                            else:
                                severity = "Severe"
                                message = "The Severity of your Depression Disorder is Quite Severe.<br>I strongly recommend taking professional help however you can also try our Depression Health Counsellor"
                            
                            cursor.execute("UPDATE users SET severity = ? WHERE username = ?", (severity, username))
                            conn.commit()
                            conn.close()
                            return message
                    else:
                        return "Please Provide Answers in Required Format !"
                
                elif predicted_class == "PTSD":
                    if session['total'] == 4:
                        if msg.lower() in ["no", "nO"]:
                            session['total'] = 15
                            conn = get_db()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET severity = ? WHERE username = ?", ("Minimal", username))
                            conn.commit()
                            conn.close()
                            return "PTSDs are generally caused due to a traumatic event. I would recommend you to consult our PTSD Mental Health Counsellor or Consider taking Professional Help."
                        elif msg.lower() in ["yes", "yES", "yEs", "yeS", "YeS", "YEs"]:
                            session['total'] += 1
                            return "Had nightmares about it or thought about it when you did not want to?"
                        else:
                            return "Please Provide Answer in Required Format"
                    
                    elif session['total'] == 5:
                        if msg.lower() in ["yes", "yES", "yEs", "yeS", "YeS", "YEs"]:
                            session['userScore'] += 1
                            session['total'] += 1
                            return "Tried hard not to think about it or went out of your way to avoid situations that reminded you of it?"
                        elif msg.lower() in ["no", "nO"]:
                            session['total'] += 1
                            return "Tried hard not to think about it or went out of your way to avoid situations that reminded you of it?"
                        else:
                            return "Please Provide Answer in Required Format"
                    
                    elif session['total'] == 6:
                        if msg.lower() in ["yes", "yES", "yEs", "yeS", "YeS", "YEs"]:
                            session['userScore'] += 1
                            session['total'] += 1
                            return "Were constantly on guard, watchful or easily startled?"
                        elif msg.lower() in ["no", "nO"]:
                            session['total'] += 1
                            return "Were constantly on guard, watchful or easily startled?"
                        else:
                            return "Please Provide Answer in Required Format"
                    
                    elif session['total'] == 7:
                        if msg.lower() in ["yes", "yES", "yEs", "yeS", "YeS", "YEs"]:
                            session['userScore'] += 1
                            session['total'] += 1
                            return "Felt numb or detached from others, activities, or your surroundings?"
                        elif msg.lower() in ["no", "nO"]:
                            session['total'] += 1
                            return "Felt numb or detached from others, activities, or your surroundings?"
                        else:
                            return "Please Provide Answer in Required Format"
                    
                    elif session['total'] == 8:
                        if msg.lower() in ["yes", "yES", "yEs", "yeS", "YeS", "YEs"]:
                            session['userScore'] += 1
                            session['total'] += 1
                            return "Felt guilty or unable to stop blaming yourself or others for the event or any problems the event may have caused"
                        elif msg.lower() in ["no", "nO"]:
                            session['total'] += 1
                            return "Felt guilty or unable to stop blaming yourself or others for the event or any problems the event may have caused"
                        else:
                            return "Please Provide Answer in Required Format"
                    
                    elif session['total'] == 9:
                        if msg.lower() in ["yes", "yES", "yEs", "yeS", "YeS", "YEs"]:
                            session['userScore'] += 1
                            session['total'] = -1
                        elif msg.lower() in ["no", "nO"]:
                            session['total'] = -1
                        else:
                            return "Please Provide Answer in Required Format"
                        
                        conn = get_db()
                        cursor = conn.cursor()
                        
                        if 0 <= session['userScore'] < 3:
                            severity = "Mild"
                            message = "The Severity of your PTSD Disorder is Mild.<br>You can refer to professional help or You can also try our PTSD Health Counsellor"
                        else:
                            severity = "Moderate/Severe"
                            message = "The Severity of your PTSD Disorder is Moderate/Severe.<br>You can try our PTSD Health Counsellor, but I strongly recommend taking professional help"
                        
                        cursor.execute("UPDATE users SET severity = ? WHERE username = ?", (severity, username))
                        conn.commit()
                        conn.close()
                        return message
                
                elif predicted_class == "Addiction":
                    if msg in ['0', '1', '2', '3']:
                        if session['total'] == 4:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you find it difficult to control or stop using the substance or engaging in the behavior?"
                        elif session['total'] == 5:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you need to use more of the substance or engage more in the behavior to achieve the same effect?"
                        elif session['total'] == 6:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you experience physical or emotional withdrawal symptoms when you try to stop using the substance or engaging in the behavior?"
                        elif session['total'] == 7:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you neglect your responsibilities at work, school, or home due to your use of the substance or engagement in the behavior?"
                        elif session['total'] == 8:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you continue to use the substance or engage in the behavior despite knowing it causes problems in your life?"
                        elif session['total'] == 9:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you spend a lot of time obtaining, using, or recovering from the substance or behavior?"
                        elif session['total'] == 10:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you lose interest in other activities or hobbies because of your use of the substance or engagement in the behavior?"
                        elif session['total'] == 11:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you continue to use the substance or engage in the behavior in situations where it is physically dangerous (e.g., driving, operating machinery)?"
                        elif session['total'] == 12:
                            session['userScore'] += int(msg)
                            session['total'] += 1
                            return "How often do you feel guilty or ashamed about your use of the substance or engagement in the behavior?"
                        elif session['total'] == 13:
                            session['userScore'] += int(msg)
                            session['total'] = -1
                            
                            # Calculate severity
                            conn = get_db()
                            cursor = conn.cursor()
                            
                            if 0 <= session['userScore'] <= 6:
                                severity = "Mild"
                                message = "The Severity of your Addiction Disorder is Mild.<br>You can refer to professional help or You can also try our Addiction Health Counsellor"
                            elif 7 <= session['userScore'] <= 15:
                                severity = "Moderate"
                                message = "The Severity of your Addiction Disorder is Moderate.<br>You can refer to professional help or You can also try our Addiction Health Counsellor"
                            elif 16 <= session['userScore'] <= 24:
                                severity = "Mildly Severe"
                                message = "The Severity of your Addiction Disorder is Mildly Severe.<br>I recommend taking professional help. Along with that You can also try our Addiction Health Counsellor"
                            else:
                                severity = "Severe"
                                message = "The Severity of your Addiction Disorder is Severe.<br>You can try our Addiction Health Counsellor, but I strongly recommend taking professional help"
                            
                            cursor.execute("UPDATE users SET severity = ? WHERE username = ?", (severity, username))
                            conn.commit()
                            conn.close()
                            return message
                    else:
                        return "Please Provide Answers in Required Format !"
                
                # Add PTSD and Addiction questionnaire logic here as needed...
            
            return "Thank you for using our website. Refresh the page for another diagnosis"
        
        # For counseling workflow
        elif not session['InDiagnosis'] and session['InCounselor']:
            from .ml_models import get_counseling_response, store
            
            # Get AI response from counseling model
            ai_response = get_counseling_response(msg, f"counsel_{username}")
            
            # Save conversation history to database using LangChain store (like original Flask app)
            conn = get_db()
            cursor = conn.cursor()
            
            session_id = f"counsel_{username}"
            if session_id in store:
                messages = store[session_id].messages
                # Separate human and AI messages
                message_list = [msg_obj.content for msg_obj in messages]
                # Combine the messages with '|'
                history = ' | '.join(message_list)
            else:
                # Fallback to manual approach if no LangChain history exists
                cursor.execute("SELECT history FROM users WHERE username = ?", (username,))
                result = cursor.fetchone()
                current_history = result[0] if result and result[0] else ""
                new_entry = f"User: {msg} | AI: {ai_response}"
                history = current_history + " | " + new_entry if current_history else new_entry
            
            # Update database
            cursor.execute(
                "UPDATE users SET history = ? WHERE username = ?",
                (history, username)
            )
            conn.commit()
            conn.close()
            
            return ai_response
        
        else:
            return "Please visit the diagnosis or counseling page to start a session."
        
    except Exception as e:
        logger.error(f"Error in get_response: {e}")
        return "I'm sorry, I'm having trouble responding right now. Please try again later."

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Landing page"""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request, "error": False, "message": ""})

@app.post("/login")
async def login(request: Request):
    """Handle login"""
    form_data = await request.form()
    username = form_data.get("name")
    password = form_data.get("password")

    if not username or not password:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": True,
            "message": "Please enter both username and password"
        })

    # Authenticate user using secure bcrypt verification
    conn = get_db()
    if authenticate_user(username, password, conn):
        conn.close()
        # Create session response with cookie
        return create_session_response(username, "/home")
    else:
        conn.close()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": True,
            "message": "Invalid username or password"
        })

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page"""
    return templates.TemplateResponse("signup.html", {"request": request, "error": False, "message": ""})

@app.post("/signup")
async def signup(request: Request):
    """Handle signup"""
    form_data = await request.form()
    firstname = form_data.get("firstn")
    lastname = form_data.get("lastn")
    username = form_data.get("username")
    password = form_data.get("password")

    if not all([firstname, lastname, username, password]):
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": True,
            "message": "All fields are required"
        })

    # Check if username exists
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": True,
            "message": "Username already exists. Please choose a different username."
        })

    # Hash password using bcrypt (keeping it secure but removing strength validation)
    hashed_password = hash_password(password)

    # Insert user - matching the existing database schema (8 columns)
    try:
        cursor.execute("""
            INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, hashed_password, 'date', firstname, lastname, 'NA', 'Not-Diagnosed', 'Not-Diagnosed'))
        
        conn.commit()
        conn.close()
        
        return create_session_response(username, "/home")
        
    except Exception as e:
        logger.error(f"Error creating user {username}: {e}")
        conn.close()
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": True,
            "message": "Error creating account. Please try again."
        })

@app.get("/diagnosis", response_class=HTMLResponse)
async def diagnosis_page(request: Request):
    """Diagnosis page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    # Initialize/reset diagnosis session
    if username not in user_sessions:
        user_sessions[username] = {}
    
    user_sessions[username].update({
        'InDiagnosis': True,
        'InCounselor': False,
        'total': 1,
        'userScore': 0,
        'userText_diagnosis': " ",
        'predicted_class': None
    })

    return templates.TemplateResponse("diagnosis.html", {"request": request, "username": username})

@app.get("/counsel", response_class=HTMLResponse)
async def counsel_page(request: Request):
    """Counseling page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    # Initialize/reset counseling session
    if username not in user_sessions:
        user_sessions[username] = {}
    
    user_sessions[username].update({
        'InDiagnosis': False,
        'InCounselor': True,
        'total': 0,
        'userScore': 0,
        'userText_diagnosis': "",
        'predicted_class': None
    })

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

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """User history page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT history FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            # Clean up the history string similar to Flask app
            history = result[0]
            # Remove any tuple formatting from database
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

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    """User home page"""
    try:
        username = get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT disorder, severity, date FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    if result:
        disorder, severity, date_val = result
        diagnosed = disorder != "Not-Diagnosed"
        counseled = date_val != 'date'
    else:
        diagnosed = False
        counseled = False
        disorder = "Not-Diagnosed"
        severity = "Not-Diagnosed"
        date_val = "date"

    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username,
        "date": date_val,
        "diagnosed": diagnosed,
        "severity": severity,
        "disorder": disorder,
        "counseled": counseled
    })

@app.get("/doctor", response_class=HTMLResponse)
async def doctor_page(request: Request):
    """Doctor page"""
    return templates.TemplateResponse("doctor.html", {"request": request})

@app.get("/logout")
async def logout(request: Request):
    """Logout"""
    return clear_session_response("/")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
