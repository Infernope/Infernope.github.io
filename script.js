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
  botMsg.textContent = "Thinking...";
  chatBox.appendChild(botMsg);
  chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });

  fetch("https://a02f-137-111-13-200.ngrok-free.app/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: userText })
  })
    .then(res => res.json())
    .then(data => {
      const response = data.reply || "No response from AI.";
      botMsg.textContent = "";
      let i = 0;
      const typeChar = () => {
        if (i < response.length) {
          botMsg.textContent += response.charAt(i);
          i++;
          chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
          setTimeout(typeChar, 30);
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
