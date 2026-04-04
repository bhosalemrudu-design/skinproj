// ================= NAVIGATION =================
function login() {
  window.location.href = "/dashboard";
}

function goAnalyze() {
  window.location.href = "/analyze_page";
}

// ================= GLOBAL IMAGE STORAGE =================
let capturedBlob = null;

// ================= CAMERA =================
let stream;

function openCamera() {
  document.getElementById("cameraSection").style.display = "block";
  document.getElementById("uploadSection").style.display = "none";

  navigator.mediaDevices.getUserMedia({ video: true })
    .then(s => {
      stream = s;
      document.getElementById("camera").srcObject = s;
    })
    .catch(err => alert("Camera error: " + err));
}

function captureImage() {
  const video = document.getElementById("camera");
  const canvas = document.getElementById("canvas");

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0);

  // Convert to blob and analyze
  canvas.toBlob(blob => {
    capturedBlob = blob;
    analyzeImage(); // AUTO ANALYZE
  }, "image/jpeg");
}

// ================= UPLOAD =================
function openUpload() {
  document.getElementById("uploadSection").style.display = "block";
  document.getElementById("cameraSection").style.display = "none";
}

function uploadImage(input) {
  const file = input.files[0];
  if (!file) return;

  capturedBlob = file;

  analyzeImage(); // AUTO ANALYZE
}

// ================= ANALYSIS =================
async function analyzeImage() {
  if (!capturedBlob) {
    alert("No image selected ❌");
    return;
  }

  const formData = new FormData();
  formData.append("file", capturedBlob);

  try {
    // Optional loading message
    document.getElementById("resultBox").innerHTML = "<p>Analyzing... ⏳</p>";

    const res = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    // Save result locally
    localStorage.setItem("result", JSON.stringify(data));

    // Redirect to result page
    window.location.href = "/result";

  } catch (err) {
    console.error(err);
    alert("Analysis failed ❌");
  }
}

// ================= RESULT LOAD =================
function loadResult() {
  const data = JSON.parse(localStorage.getItem("result"));

  if (!data) return;

  const resultBox = document.getElementById("resultBox");

  resultBox.innerHTML = `
    <h2>Score: ${data.score}</h2>
    <p><strong>Issues:</strong> ${data.issues}</p>
  `;
}

function goDashboard() {
  window.location.href = "/dashboard";
}
// ================= AUTO LOAD =================
if (window.location.pathname === "/result") {
  loadResult();
}