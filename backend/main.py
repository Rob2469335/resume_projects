import json
import sqlite3
import uuid
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------
# APP SETUP
# ------------------------------------
app = FastAPI(title="HireFlow AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------
# DATABASE SETUP (SQLite)
# ------------------------------------
conn = sqlite3.connect("jobs.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    description TEXT
)
""")
conn.commit()

# LM Studio endpoint
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"


# ------------------------------------
# CREATE JOB
# ------------------------------------
@app.post("/jobs")
async def create_job(job_description: str = Form(...)):
    job_id = str(uuid.uuid4())

    cursor.execute(
        "INSERT INTO jobs (job_id, description) VALUES (?, ?)",
        (job_id, job_description)
    )
    conn.commit()

    return {
        "job_id": job_id,
        "job_description": job_description
    }


# ------------------------------------
# ANALYZE RESUME
# ------------------------------------
@app.post("/analyze")
async def analyze_resume(
    job_id: str = Form(...),
    file: UploadFile = File(...)
):

    # Validate job exists
    cursor.execute(
        "SELECT description FROM jobs WHERE job_id = ?", (job_id,)
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job ID {job_id} not found."
        )

    job_description = row[0]

    # Read resume text
    resume_bytes = await file.read()
    resume_text = resume_bytes.decode("utf-8", errors="ignore")

    # Build prompt
    prompt = f"""
You are an AI hiring assistant.

Analyze the following resume against the job description.

Job Description:
{job_description}

Resume:
{resume_text}

Return ONLY valid JSON with:
- match_score (0-100)
- strengths (list)
- weaknesses (list)
- recommendations (list)
"""

    # Send to LM Studio
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LM_STUDIO_URL,
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You return ONLY valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LM Studio error: {response.status_code} {response.text}"
        )

    try:
        result = response.json()
        ai_output = result["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse LM Studio JSON: {str(e)}"
        )

    try:
        analysis_json = json.loads(ai_output)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI payload is not valid JSON."
        )

    return {
        "job_id": job_id,
        "analysis": analysis_json
    }
