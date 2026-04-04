"""
HireFlow AI — Production Backend
FastAPI + SQLAlchemy + Ollama + PyMuPDF

Fixes applied vs original:
  - Typed exception handling (no bare except)
  - Configurable model name via env var (OLLAMA_MODEL)
  - Structured score parsing: extracts numeric score from AI response
  - Input validation via Pydantic / FastAPI constraints
  - Scoped CORS origins (env-configurable)
  - GET /history endpoint with pagination
  - GET /history/{id} endpoint for single result
  - DELETE /history/{id} endpoint
  - Proper HTTP error responses (422, 503, 404, etc.)
  - DB session managed via dependency injection (no manual open/close)
  - Logging instead of silent failures
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Optional

import fitz  # PyMuPDF
import requests
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hireflow")

# ---------------------------------------------------------------------------
# Config  (override via environment variables)
# ---------------------------------------------------------------------------
DATABASE_URL  = os.getenv("DATABASE_URL",  "sqlite:///./hireflow.db")
OLLAMA_URL    = os.getenv("OLLAMA_URL",    "http://localhost:11434/api/generate")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL",  "llama3.2")          # change to your local model
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))        # seconds

# Comma-separated list of allowed CORS origins, e.g. "http://localhost:5500,http://localhost:3000"
_raw_origins  = os.getenv("CORS_ORIGINS", "http://localhost:5500,http://localhost:3000,http://127.0.0.1:5500")
CORS_ORIGINS  = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
Base = declarative_base()

class AnalysisResult(Base):
    __tablename__ = "results"

    id             = Column(Integer, primary_key=True, index=True)
    filename       = Column(String,  nullable=False)
    job_snippet    = Column(String,  nullable=False)   # first 200 chars of JD for display
    score          = Column(Integer, nullable=True)    # parsed 0-100
    raw_analysis   = Column(Text,    nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency-injected DB session — always closed after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class AnalysisSummary(BaseModel):
    id:          int
    filename:    str
    job_snippet: str
    score:       Optional[int]
    created_at:  datetime

    class Config:
        from_attributes = True


class AnalysisDetail(AnalysisSummary):
    raw_analysis: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SCORE_PATTERN = re.compile(
    r"""
    (?:match(?:ing)?\s*(?:percentage|score|rate|level)?  # "match percentage", "matching score", etc.
    |score
    |percentage)
    \s*[:\-–]?\s*
    (\d{1,3})\s*%?           # capture the digits
    |(\d{1,3})\s*%           # OR bare "72%" anywhere
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_score(text: str) -> Optional[int]:
    """Return the first numeric score (0-100) found in the AI response, or None."""
    for match in SCORE_PATTERN.finditer(text):
        raw = match.group(1) or match.group(2)
        if raw:
            value = int(raw)
            if 0 <= value <= 100:
                return value
    return None


def extract_resume_text(pdf_bytes: bytes) -> str:
    """Return all text from a PDF given its raw bytes. Raises ValueError on bad input."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc).strip()
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        raise ValueError(f"Could not read PDF: {exc}") from exc


def call_ollama(prompt: str) -> str:
    """Send a prompt to Ollama and return the response text. Raises RuntimeError on failure."""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError as exc:
        logger.error("Ollama connection error: %s", exc)
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_URL}. "
            "Make sure the Ollama app is running and the model is downloaded."
        ) from exc
    except requests.exceptions.Timeout as exc:
        logger.error("Ollama timeout after %ss", OLLAMA_TIMEOUT)
        raise RuntimeError(
            f"Ollama did not respond within {OLLAMA_TIMEOUT} seconds. "
            "Try a smaller/faster model or increase OLLAMA_TIMEOUT."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        logger.error("Ollama HTTP error: %s — %s", exc.response.status_code, exc.response.text)
        raise RuntimeError(
            f"Ollama returned HTTP {exc.response.status_code}. "
            "Check that the model name is correct: "
            f"current value is '{OLLAMA_MODEL}' (set OLLAMA_MODEL env var to change it)."
        ) from exc
    except Exception as exc:
        logger.error("Unexpected Ollama error: %s", exc)
        raise RuntimeError(f"Unexpected error communicating with Ollama: {exc}") from exc


BUILD_PROMPT = """\
You are an expert technical recruiter and resume coach.

Analyze the resume below against the job description and respond in this EXACT format — do not add extra sections:

MATCH_SCORE: [0-100]%

SUMMARY:
[2-3 sentence overall assessment]

STRENGTHS:
1. [Strength one]
2. [Strength two]
3. [Strength three]

GAPS:
1. [Gap one]
2. [Gap two]
3. [Gap three]

RECOMMENDATIONS:
1. [Actionable recommendation one]
2. [Actionable recommendation two]
3. [Actionable recommendation three]

--- JOB DESCRIPTION ---
{job_description}

--- RESUME ---
{resume_text}
"""

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HireFlow AI",
    description="AI-powered resume analyzer",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "model": OLLAMA_MODEL}


@app.post("/analyze", response_model=AnalysisDetail, tags=["analyze"])
async def analyze_resume(
    job_description: str = Form(..., min_length=20, max_length=10_000,
                                description="Paste the job description here."),
    resume: UploadFile = File(..., description="Resume PDF file."),
    db: Session = Depends(get_db),
):
    # --- Validate file type ---
    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    # --- Extract text ---
    pdf_bytes = await resume.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        resume_text = extract_resume_text(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len(resume_text) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough text from the PDF. "
                   "Make sure it's a text-based PDF (not a scanned image)."
        )

    # --- Build prompt and call Ollama ---
    prompt = BUILD_PROMPT.format(
        job_description=job_description[:5000],   # guard against absurdly large inputs
        resume_text=resume_text[:8000],
    )

    try:
        ai_response = call_ollama(prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # --- Parse score ---
    score = extract_score(ai_response)
    logger.info("Analysis complete for '%s' — score: %s", resume.filename, score)

    # --- Persist ---
    entry = AnalysisResult(
        filename     = resume.filename,
        job_snippet  = job_description[:200],
        score        = score,
        raw_analysis = ai_response,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return entry


@app.get("/history", response_model=list[AnalysisSummary], tags=["history"])
def get_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Return paginated list of past analyses (newest first)."""
    return (
        db.query(AnalysisResult)
        .order_by(AnalysisResult.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )


@app.get("/history/{result_id}", response_model=AnalysisDetail, tags=["history"])
def get_result(result_id: int, db: Session = Depends(get_db)):
    """Return full analysis for a single past result."""
    entry = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found.")
    return entry


@app.delete("/history/{result_id}", tags=["history"])
def delete_result(result_id: int, db: Session = Depends(get_db)):
    """Delete a single analysis result."""
    entry = db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found.")
    db.delete(entry)
    db.commit()
    return {"deleted": result_id}