const TEST_TYPE_LABELS = {
  A: "Ability & Aptitude",
  B: "Biodata & Situational Judgement",
  C: "Competencies",
  D: "Development & 360",
  E: "Assessment Exercises",
  K: "Knowledge & Skills",
  P: "Personality & Behavior",
  S: "Simulations",
};

const EXAMPLES = [
  "Hiring a mid-level Java developer who works with stakeholders. Add personality too.",
  "We're screening entry-level contact centre agents. Inbound calls, US English.",
  "We need a solution for senior leadership selection against a benchmark.",
];

const messagesEl = document.getElementById("messages");
const composerEl = document.getElementById("composer");
const inputEl = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");
const template = document.getElementById("message-template");

let history = [];

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatTestTypes(code) {
  const letters = [...new Set((code || "").replace(/\s+/g, ""))];
  return letters.map((letter) => TEST_TYPE_LABELS[letter] || letter).join(" · ");
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderWelcome() {
  const chips = EXAMPLES.map(
    (text) =>
      `<button type="button" class="example-chip" data-example="${escapeHtml(text)}">${escapeHtml(text)}</button>`,
  ).join("");

  messagesEl.innerHTML = `
    <div class="welcome-card">
      <h2>How can I help?</h2>
      <p>Describe the role, skills, seniority, or assessment types you need. I recommend only from the SHL Individual Test Solutions catalog.</p>
      <div class="examples" role="list">${chips}</div>
    </div>
  `;

  messagesEl.querySelectorAll(".example-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      inputEl.value = chip.dataset.example || "";
      inputEl.focus();
    });
  });
}

function appendMessage(role, content, recommendations = []) {
  const node = template.content.firstElementChild.cloneNode(true);
  node.classList.add(role);
  node.querySelector(".message-meta").textContent = role === "user" ? "You" : "Recommender";
  node.querySelector(".message-body").textContent = content;

  const list = node.querySelector(".recommendations");
  if (recommendations.length > 0) {
    list.hidden = false;
    for (const item of recommendations) {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = item.name;

      const type = document.createElement("span");
      type.className = "type";
      type.textContent = formatTestTypes(item.test_type);

      li.append(link, type);
      list.appendChild(li);
    }
  }

  messagesEl.querySelector(".welcome-card")?.remove();
  messagesEl.appendChild(node);
  scrollToBottom();
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  resetBtn.disabled = busy;
  inputEl.disabled = busy;
  sendBtn.textContent = busy ? "Sending…" : "Send";
}

async function sendMessage(text) {
  history.push({ role: "user", content: text });
  appendMessage("user", text);

  const status = document.createElement("div");
  status.className = "status-pill";
  status.textContent = "Finding catalog matches…";
  messagesEl.appendChild(status);
  scrollToBottom();
  setBusy(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });

    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }

    const data = await response.json();
    history.push({ role: "assistant", content: data.reply });
    appendMessage("assistant", data.reply, data.recommendations || []);

    if (data.end_of_conversation) {
      inputEl.placeholder = "Refine your request or start a new conversation…";
    }
  } catch (error) {
    const banner = document.createElement("div");
    banner.className = "error-banner";
    banner.textContent =
      error instanceof Error
        ? `Could not reach the API: ${error.message}. If this is a cold start on Render, wait a moment and try again.`
        : "Could not reach the API.";
    messagesEl.appendChild(banner);
    history.pop();
  } finally {
    status.remove();
    setBusy(false);
    inputEl.focus();
  }
}

composerEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  await sendMessage(text);
});

resetBtn.addEventListener("click", () => {
  history = [];
  inputEl.value = "";
  inputEl.placeholder = "Describe the role, skills, seniority, or assessment types you need…";
  renderWelcome();
  inputEl.focus();
});

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    composerEl.requestSubmit();
  }
});

renderWelcome();
