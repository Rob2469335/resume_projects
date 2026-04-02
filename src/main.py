from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
import sqlite3


app = FastAPI()


@app.post("/analyze")
async def analyze_resume(
    job_id: str = Form(...), file: UploadFile = File(...)
):
    try:
        # Validate job exists
        conn = sqlite3.connect("jobs.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT description FROM jobs WHERE job_id = ?", (job_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job ID {job_id} not found."
            )
        conn.close()
        # Process file
        await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse AI response: {str(e)}"
        )
