const chatBox = document.getElementById("chat-box");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

sendBtn.addEventListener("click", () => {
  const userText = input.value.trim();
  if (!userText) return;

  const header = document.getElementById("chat-header");
  if (header) header.style.display = "none";

  document.body.style.alignItems = "stretch";
  const container = document.querySelector(".container");
  container.style.height = "100vh";
  container.style.alignItems = "stretch";

  chatBox.style.display = "flex";
  input.value = "";

  const userMsg = document.createElement("div");
  userMsg.classList.add("message", "user-message");
  userMsg.textContent = userText;
  chatBox.appendChild(userMsg);

  const botMsg = document.createElement("div");
  botMsg.classList.add("message", "bot-message");
  botMsg.innerHTML = "Thinking...";
  chatBox.appendChild(botMsg);
  chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });

  fetch("ttps://6099-2401-d006-fc02-8300-2e76-83b5-da3c-2e90.ngrok-free.app/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: userText })
  })
    .then(res => res.json())
    .then(data => {
      const response = data.reply || "No response from AI.";

      // Convert response to safe HTML formatting
      const formatted = response
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>")
        .replace(/•/g, "&bull;");

      // Typing effect with innerHTML support
      let i = 0;
      const typeChar = () => {
        if (i <= formatted.length) {
          botMsg.innerHTML = formatted.slice(0, i);
          chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
          i++;
          setTimeout(typeChar, 20); // Typing speed
        }
      };
      typeChar();
    })
    .catch(err => {
      botMsg.textContent = "⚠️ AI is offline or error occurred.";
      console.error("Frontend fetch error:", err);
    });
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendBtn.click();
  }
});

window.addEventListener('resize', () => {
  const container = document.querySelector('.container');
  container.style.height = `${window.innerHeight}px`;
});
