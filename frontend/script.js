const API_BASE = "https://openims-backend.onrender.com";

const pdfInput = document.getElementById("pdfInput");
const storeBtn = document.getElementById("storeBtn");
const docList = document.getElementById("docList");
const chatBox = document.getElementById("chatBox");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");

let selectedFiles = [];

pdfInput.addEventListener("change", () => {
  selectedFiles = Array.from(pdfInput.files);
  renderSelectedFiles();
});

function renderSelectedFiles() {
  docList.innerHTML = "";
  selectedFiles.forEach(file => {
    const div = document.createElement("div");
    div.className = "doc-item";
    div.innerHTML = `<span>${file.name}</span><span>📄</span>`;
    docList.appendChild(div);
  });
}

async function loadDocuments() {
  try {
    const res = await fetch(`${API_BASE}/documents`);
    const data = await res.json();
    if (!selectedFiles.length && data.documents) {
      docList.innerHTML = "";
      data.documents.forEach(name => {
        const div = document.createElement("div");
        div.className = "doc-item";
        div.innerHTML = `<span>${name}</span><span>📄</span>`;
        docList.appendChild(div);
      });
    }
  } catch (err) {}
}

storeBtn.addEventListener("click", async () => {
  if (!selectedFiles.length) {
    alert("Please choose PDF files first.");
    return;
  }

  storeBtn.textContent = "Storing...";
  storeBtn.disabled = true;

  try {
    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
    }
    addBotMessage("PDF stored successfully. Now ask me questions from your documents.");
    selectedFiles = [];
    pdfInput.value = "";
    await loadDocuments();
  } catch (error) {
    addBotMessage("Upload error: " + error.message);
  } finally {
    storeBtn.textContent = "Store Document";
    storeBtn.disabled = false;
  }
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  addUserMessage(message);
  messageInput.value = "";
  const thinking = addThinking();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();
    thinking.remove();

    if (!res.ok) {
      addBotMessage(data.detail || "Something went wrong.");
      return;
    }

    let sourceText = "";
    if (data.sources && data.sources.length) {
      const unique = [...new Map(data.sources.map(s => [`${s.filename}-${s.page}`, s])).values()];
      sourceText = "\n\nSources: " + unique.map(s => `${s.filename}, page ${s.page}`).join(" | ");
    }
    addBotMessage(data.answer + sourceText);
  } catch (error) {
    thinking.remove();
    addBotMessage("Backend not connected. Make sure FastAPI is running on http://127.0.0.1:8000");
  }
});

function addUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user-row";
  row.innerHTML = `<div class="bubble user-bubble">${escapeHtml(text)}</div><div class="avatar user-avatar">YOU</div>`;
  chatBox.appendChild(row);
  scrollBottom();
}

function addBotMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row bot-row";
  row.innerHTML = `<img src="assets/bot_icon.svg" class="avatar" alt="bot" /><div class="bubble bot-bubble">${escapeHtml(text)}</div>`;
  chatBox.appendChild(row);
  scrollBottom();
}

function addThinking() {
  const row = document.createElement("div");
  row.className = "message-row bot-row thinking";
  row.innerHTML = `<img src="assets/bot_icon.svg" class="avatar" alt="bot" /><div class="bubble bot-bubble">Thinking...</div>`;
  chatBox.appendChild(row);
  scrollBottom();
  return row;
}

function scrollBottom() { chatBox.scrollTop = chatBox.scrollHeight; }
function escapeHtml(text) {
  return text.replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c]));
}

loadDocuments();
