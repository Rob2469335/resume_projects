# Resume Projects — AI‑Powered Resume Parsing & Job Tracking

A modular, full‑stack project designed to parse resumes, extract structured data, and manage job applications through a clean frontend dashboard. Built with FastAPI, JavaScript, and SQLite, this project demonstrates practical workflow automation, backend API design, and frontend integration.

## Features

### Resume Parsing
- Extracts key fields (name, email, phone, skills, experience, education)
- Normalizes skills into consistent categories
- Returns clean JSON for downstream automation

### Job Management
- Add job entries
- Store job descriptions
- Link parsed resumes to job records
- SQLite database for lightweight persistence

### Frontend Dashboard
- Simple, responsive UI
- Upload resumes
- Trigger parsing
- View structured results instantly

### Backend API (FastAPI)
- /parse-resume endpoint
- /jobs CRUD endpoints
- CORS enabled
- Clean, modular Python code

## Tech Stack

- FastAPI (Python)
- HTML, CSS, JavaScript
- SQLite
- Git & GitHub
- Local LLM parsing workflow

## Project Structure


## How to Run

### 1. Install dependencies
pip install -r requirements.txt

### 2. Start the backend
uvicorn backend.main:app --reload

### 3. Open the frontend
Open frontend/index.html in your browser.

## Future Enhancements

- Add authentication
- Add analytics dashboard
- Add PDF text extraction fallback
- Add Docker support
