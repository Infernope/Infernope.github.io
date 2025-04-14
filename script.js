const chatBox = document.getElementById("chat-box");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

sendBtn.addEventListener("click", () => {
    const userText = input.value.trim();
    if (!userText) return;

    // Hide the header if it's visible
    const header = document.getElementById("chat-header");
    if (header) {
        header.style.display = "none";
    }

    // Switch layout: stretch container + fix input at bottom
    document.body.style.alignItems = "stretch"; // stop vertical centering
    const container = document.querySelector(".container");
    container.style.height = "100vh";
    container.style.alignItems = "stretch";

     // Show chat box
     chatBox.style.display = "flex";

    // Clear input
    input.value = "";

    // Append user message
    const userMsg = document.createElement("div");
    userMsg.classList.add("message", "user-message");
    userMsg.textContent = userText;
    chatBox.appendChild(userMsg);

    // Scroll to bottom smoothly
    chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });

    // Fake bot reply
    const botText = "Sure! Here's your answer...";
    const botMsg = document.createElement("div");
    botMsg.classList.add("message", "bot-message");
    chatBox.appendChild(botMsg);

    // Typing effect
    let i = 0;
    const typeChar = () => {
        if (i < botText.length) {
            botMsg.textContent += botText.charAt(i);
            i++;
            chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
            setTimeout(typeChar, 30); // typing speed
        }
    };
    typeChar();
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