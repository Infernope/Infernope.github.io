const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
app.use(cors());
app.use(express.json());

app.post('/chat', async (req, res) => {
  try {
    console.log("🔵 Incoming message:", req.body.message);

    const response = await fetch("https://yuntian-deng-chatgpt.hf.space/run/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        inputs: req.body.message,
        top_p: 1,
        temperature: 1,
        chat_counter: 0,
        chatbot: []
      })
    });

    const result = await response.json();
    console.log("🟢 Full AI response:", result);

    const reply = result?.[0]?.[1] || "No reply from AI.";
    res.json({ reply });

  } catch (err) {
    console.error("❌ Server error:", err.message);
    res.status(500).json({ reply: "⚠️ Server Error: " + err.message });
  }
});

app.listen(3000, () => {
  console.log('🟢 Server running at http://localhost:3000');
});
