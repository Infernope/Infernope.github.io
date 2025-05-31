const chatBox = document.getElementById("chat-box");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

sendBtn.addEventListener("click", handleSend);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendBtn.click();
  }
});
window.addEventListener("resize", () => {
  document.querySelector(".container").style.height = `${window.innerHeight}px`;
});

function handleSend() {
  const userText = input.value.trim();
  if (!userText) return;

  prepareLayout();
  displayMessage(userText, "user");

  input.value = "";
  const botMessageEl = displayMessage("Thinking...", "bot");

  fetch("https://d3a3-2401-d006-fc02-8300-307d-fbdd-9cb1-d31e.ngrok-free.app/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: userText }),
  })
    .then((res) => res.json())
    .then((data) => {
      const rawResponse = data.reply || "No response from AI.";
      const formattedResponse = formatResponse(rawResponse); // ⏱ Pre-format the entire HTML up front
      animateTyping(botMessageEl, formattedResponse);         // 🌀 Then animate it (no pause)
    })
    .catch((err) => {
      console.error("Frontend fetch error:", err);
      botMessageEl.textContent = "⚠️ AI is offline or error occurred.";
    });
}

function prepareLayout() {
  const header = document.getElementById("chat-header");
  if (header) header.style.display = "none";

  const container = document.querySelector(".container");
  container.style.height = "100vh";
  container.style.alignItems = "stretch";

  chatBox.style.display = "flex";
}

function displayMessage(text, type) {
  const msg = document.createElement("div");
  msg.classList.add("message", `${type}-message`);
  msg.innerHTML = type === "user" ? escapeHtml(text) : text;
  chatBox.appendChild(msg);
  chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
  return msg;
}

function animateTyping(el, htmlContent) {
  const tokens = tokenizeHTML(htmlContent);
  let i = 0;

  const interval = setInterval(() => {
    el.innerHTML = tokens.slice(0, i).join('');
    chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
    i++;
    if (i > tokens.length) clearInterval(interval);
  }, 10); // slightly faster animation
}

function tokenizeHTML(html) {
  const tokens = [];
  const regex = /(<[^>]+>|[^<])/g; // match tags OR single characters
  let match;

  while ((match = regex.exec(html)) !== null) {
    tokens.push(match[0]);
  }

  return tokens;
}



function formatResponse(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>') // Convert markdown [text](url) to link
    .replace(/\n/g, "<br>")
    .replace(/•/g, "&bull;");
}


function escapeAndLinkifyMarkdown(str) {
  // Match markdown links separately first
  return str.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, (match, text, url) => {
    const safeText = escapeHtml(text);
    const safeUrl = escapeHtml(url);
    return `<a href="${safeUrl}" target="_blank">${safeText}</a>`;
  }).split(/(<a[^>]*>.*?<\/a>)/g) // split into chunks to preserve already-escaped links
    .map(chunk => {
      return chunk.startsWith("<a") ? chunk : escapeHtml(chunk);
    })
    .join('');
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

