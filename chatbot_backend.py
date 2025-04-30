import sys
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask, request, jsonify
from flask_cors import CORS
from gradio_client import Client

app = Flask(__name__)
CORS(app)

client = Client("sudo-soldier/chat", httpx_kwargs={"timeout": 120})  # Extended timeout to avoid ReadTimeouts

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message", "")
        print("🟢 Sending to Research AI:", user_input)

        result = client.predict(
            message=user_input,
            system_message="You are a Chatbot that is an expert on the platform Notion. You give short but insightful answers. You don't ramble on. Most of your answers are 1-2 sentences long",  # You can customize this system message
            max_tokens=512,
            temperature=0.7,
            top_p=0.95,
            api_name="/chat"
        )

        print("🧾 Raw API result:", result)  # New API returns a simple string

        # No need for complex parsing now
        reply = result

        return jsonify({ "reply": reply })

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({ "reply": f"⚠️ Server Error: {str(e)}" }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
