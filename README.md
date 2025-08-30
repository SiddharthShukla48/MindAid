# MindAid - AI-Powered Mental Health Platform

> **🧠 AI-powered mental health diagnosis and counseling platform built with FastAPI, BERT, and LangChain**

## Inspiration


The inspiration for <ins>**MindAid**</ins> comes from our experiences living in small cities, where access to good counsellors, psychiatrist and mental health support is often limited or nonexistent. Despite the growing awareness and recognition of mental health issues globally, millions of people still face significant barriers to accessing the care they need due to stigma, lack of resources, geographic limitations, and financial constraints.
Moreover, many people hesitate to visit doctors due to fear, further widening the gap between those in need and the support they require. This deeply concerns us, and we believe technology can offer a solution.
MindAid was conceived out of a deep concern for these challenges and a strong belief in the transformative potential of technology. We recognized that artificial intelligence could play a pivotal role in bridging the gap between those in need and the mental health support they require. Our aim is to create a platform that can provide immediate, accessible, and reliable mental health assistance to anyone, anywhere, regardless of their circumstances.
By addressing the shortcomings of traditional mental health care, MindAid aspires to contribute to a world where mental health support is not a privilege, but a readily available resource for all.
Our mission is to empower individuals to take control of their mental health, break down the stigma associated with mental health issues, and promote a culture of understanding and support.

## Features

### AI Diagnosis
- **BERT-based Mental Health Classification**: Fine-tuned multilingual BERT model for accurate disorder prediction
- **Interactive Questionnaires**: Step-by-step assessment for Anxiety, Depression, PTSD, and Addiction
- **Severity Assessment**: Comprehensive scoring system with professional recommendations
- **Medical-grade Accuracy**: Trained on clinical datasets for reliable diagnoses

### AI Counseling
- **RAG-powered Conversations**: Retrieval Augmented Generation using LangChain and FAISS
- **Professional Counseling Techniques**: Trained on real counseling session data
- **Contextual Memory**: Maintains conversation history for meaningful interactions
- **Multi-session Support**: Persistent conversation tracking across sessions

### Security & Authentication
- **Secure Authentication**: bcrypt password hashing with session management
- **Cookie-based Sessions**: Secure user session handling

### Healthcare Integration
- **Doctor Portal**: Dedicated interface for healthcare professionals
- **Patient History**: Complete medical history and session tracking

## 🏗️ Architecture

```
src/mindaid/
├── main.py              # FastAPI application entry point
├── auth.py              # Authentication & session management
├── ml_models.py         # ML model loading and inference
├── diagnosis.py         # Diagnosis workflow and questionnaires
├── counseling.py        # AI counseling and RAG implementation
├── database.py          # Database operations
└── models.py            # Pydantic data models
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Manas-7854/MediHacks.git
   cd MediHacks
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -e .
   ```

4. **Generate secret key**
   ```bash
   uv run python generate_secret.py
   ```

5. **Run the application**
   ```bash
   # Using the provided script
   ./run_uv.sh

   # Or manually
   uv run uvicorn src.mindaid.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   - Main App: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### AI Models

1. **Diagnosis Model**: `SiddharthShukla48/MindAid_Diagnosis_bert-base-multilingual-cased`
   - We employed the Google`s BERT-base-multilingual-cased model from Hugging Face, fine-tuning it to predict various mental health disorders. The dataset used for fine-tuning was sourced from Zenodo, providing a robust foundation for accurate diagnostics. We also used clinically authorized questionnaire to measure the severity of disorder.

2. **Counseling Model**: LLaMA 3 (70B) via Groq API
   - For the AI-powered counselor, we used LLaMA3-70B-8192 via Groq. To enhance the quality of counseling responses, we applied Retrieval-Augmented Generation (RAG) using LangChain, which allows the model to generate more informed and contextually relevant responses.

### 🗄️ Database Schema

```sql
-- Users table
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    date TEXT,
    firstname TEXT,
    lastname TEXT,
    history TEXT,
    disorder TEXT,
    severity TEXT
);

-- Doctors table  
CREATE TABLE doctors (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    firstname TEXT,
    lastname TEXT,
    fees TEXT,
    qualification TEXT
);
```

## Project Structure

```
MediHacks/
├── src/mindaid/           # Main application code
├── static/               # CSS, images, and frontend assets
├── templates/            # HTML templates
├── context_for_RAG/      # Counseling training data
├── Severity Questionnaires/ # Medical questionnaires (PDFs)
├── pyproject.toml        # Project dependencies and config
├── uv.lock              # Dependency lock file
├── run_uv.sh            # Application runner script
├── generate_secret.py    # Secret key generator
```

## Security Features

- **Password Security**: bcrypt hashing with salt
- **Session Management**: Secure cookie-based sessions
- **Input Validation**: Pydantic models for data validation
- **SQL Injection Prevention**: Parameterized queries
- **CORS Protection**: Configurable CORS middleware


##  Acknowledgments

- **HuggingFace**: For the BERT model infrastructure
- **Groq**: For LLaMA model API access
- **LangChain**: For RAG implementation framework
- **FastAPI**: For the modern backend framework


<div align="center">

**⚠️ Important Disclaimer**: This application is for educational and research purposes. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified healthcare providers.

</div>
