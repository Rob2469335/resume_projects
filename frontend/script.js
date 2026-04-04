document.addEventListener("DOMContentLoaded", () => {
  const jobDescriptionInput = document.getElementById("jobDescription");
  const createJobBtn = document.getElementById("createJobBtn");
  const resumeInput = document.getElementById("resumeInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const outputBox = document.getElementById("output");

  // Use the standard Localhost address
  const API_BASE = "http://localhost:8000";

  let currentJobId = null;

  // -------------------------------
  // CREATE JOB (Sending the "Order")
  // -------------------------------
  createJobBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    const description = jobDescriptionInput.value.trim();
    
    if (!description) return alert("Please enter a description!");

    // MATCH CHECK: The backend looks for "job_description"
    const formData = new FormData();
    formData.append("job_description", description); 

    outputBox.textContent = "Creating job...";

    try {
      const response = await fetch(`${API_BASE}/jobs`, {
          method: "POST", 
          body: formData 
      });
      const data = await response.json();
      currentJobId = data.job_id;
      outputBox.textContent = `✅ Job Created! ID: ${currentJobId}`;
    } catch (err) {
      outputBox.textContent = "❌ Error: Is the Backend running?";
    }
  });

  // -------------------------------
  // ANALYZE RESUME (The "Deep Dive")
  // -------------------------------
  analyzeBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    const file = resumeInput.files[0];

    if (!currentJobId) return alert("Create a job first!");
    if (!file) return alert("Upload a file!");

    // MATCH CHECK: Backend looks for "job_id" and "file"
    const formData = new FormData();
    formData.append("job_id", currentJobId);
    formData.append("file", file);

    outputBox.textContent = "🤖 AI is analyzing... (Ollama is thinking)";

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
          method: "POST",
          body: formData
      });
      const data = await response.json();
      outputBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      outputBox.textContent = "❌ Analysis failed. Check Ollama!";
    }
  });
});