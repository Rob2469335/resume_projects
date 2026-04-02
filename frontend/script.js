document.addEventListener("DOMContentLoaded", () => {
  console.log("🔥 HireFlow script loaded");

  // -------------------------------
  // DOM ELEMENTS
  // -------------------------------
  const jobDescriptionInput = document.getElementById("jobDescription");
  const createJobBtn = document.getElementById("createJobBtn");
  const resumeInput = document.getElementById("resumeInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const outputBox = document.getElementById("output");

  // Backend URL
  const API_BASE = "http://127.0.0.1:8000";

  // -------------------------------
  // STATE
  // -------------------------------
  let currentJobId = null;

  // -------------------------------
  // HELPERS
  // -------------------------------
  function setOutput(message, status = "info") {
    outputBox.textContent = message;
    outputBox.dataset.status = status;
  }

  function setButtonLoading(btn, isLoading, loadingLabel = "Loading...") {
    if (isLoading) {
      btn.dataset.originalLabel = btn.textContent;
      btn.textContent = loadingLabel;
      btn.disabled = true;
    } else {
      btn.textContent = btn.dataset.originalLabel || btn.textContent;
      btn.disabled = false;
    }
  }

  function formatOutput(data) {
    return JSON.stringify(data, null, 2);
  }

  // -------------------------------
  // CREATE JOB
  // -------------------------------
  createJobBtn.addEventListener("click", async (event) => {
    event.preventDefault(); // 🔥 prevents page reload
    console.log("🔥 Create Job button CLICKED");

    const description = jobDescriptionInput.value.trim();
    if (!description) {
      setOutput("⚠️ Please enter a job description.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("job_description", description);

    setButtonLoading(createJobBtn, true, "Creating...");
    setOutput("Creating job...", "info");

    try {
      const response = await fetch(`${API_BASE}/jobs`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        setOutput(`❌ Failed to create job. Server said: ${response.status}`, "error");
        return;
      }

      const data = await response.json();
      currentJobId = data.job_id;

      setOutput(`✅ Job created!\nJob ID: ${currentJobId}`, "success");

    } catch (err) {
      console.error(err);
      setOutput("❌ Failed to create job. Is the backend running?", "error");
    } finally {
      setButtonLoading(createJobBtn, false);
    }
  });

  // -------------------------------
  // ANALYZE RESUME
  // -------------------------------
  analyzeBtn.addEventListener("click", async (event) => {
    event.preventDefault(); // 🔥 prevents reload
    console.log("📄 Analyze Resume button CLICKED");

    if (!currentJobId) {
      setOutput("⚠️ Please create a job first.", "error");
      return;
    }

    const file = resumeInput.files[0];
    if (!file) {
      setOutput("⚠️ Please upload a resume file.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("job_id", currentJobId);
    formData.append("file", file);

    setButtonLoading(analyzeBtn, true, "Analyzing...");
    setOutput(`Analyzing resume for Job ID: ${currentJobId}...`, "info");

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        setOutput(`❌ Failed to analyze resume. Server said: ${response.status}`, "error");
        return;
      }

      const data = await response.json();
      setOutput(formatOutput(data), "success");

    } catch (err) {
      console.error(err);
      setOutput("❌ Failed to analyze resume. Is the backend running?", "error");
    } finally {
      setButtonLoading(analyzeBtn, false);
    }
  });
});
  