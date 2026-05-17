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

const messagesEl = document.getElementById("messages");
const composerEl = document.getElementById("composer");
const inputEl = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");
const template = document.getElementById("message-template");

/** @type {{ role: "user" | "assistant", content: string }[]} */
let history = [];

function formatTestTypes(code) {
  const letters = [...new Set((code || "").replace(/\s+/g, ""))];
  return letters.map((letter) => TEST_TYPE_LABELS[letter] || letter).join(" · ");
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderWelcome() {
  messagesEl.innerHTML = `
    <div class="welcome">
      <p><strong>Ask about a role or hiring need</strong> and I will recommend SHL Individual Test Solutions from the catalog.</p>
      <p>Example: <em>Hiring a mid-level Java developer who works with stakeholders. Add personality too.</em></p>
    </div>
  `;
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
      li.innerHTML = `
        <a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.name}</a>
        <span class="type">${formatTestTypes(item.test_type)}</span>
      `;
      list.appendChild(li);
    }
  }

  const welcome = messagesEl.querySelector(".welcome");
  if (welcome) {
    welcome.remove();
  }

  messagesEl.appendChild(node);
  scrollToBottom();
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  resetBtn.disabled = busy;
  inputEl.disabled = busy;
}

async function sendMessage(text) {
  history.push({ role: "user", content: text });
  appendMessage("user", text);

  const status = document.createElement("div");
  status.className = "status-pill";
  status.textContent = "Thinking…";
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
      inputEl.placeholder = "Start a new conversation or refine your request…";
    }
  } catch (error) {
    const banner = document.createElement("div");
    banner.className = "error-banner";
    banner.textContent =
      error instanceof Error
        ? `Could not reach the API: ${error.message}`
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
  if (!text) {
    return;
  }
  inputEl.value = "";
  await sendMessage(text);
});

resetBtn.addEventListener("click", () => {
  history = [];
  inputEl.value = "";
  inputEl.placeholder = "Describe the role, skills, or assessment types you need…";
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
