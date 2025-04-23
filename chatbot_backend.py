import sys
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask, request, jsonify
from flask_cors import CORS
from gradio_client import Client

app = Flask(__name__)
CORS(app)

client = Client("yuntian-deng/ChatGPT", httpx_kwargs={"timeout": 60})  # Extended timeout to avoid ReadTimeouts

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message", "")
        print("🟢 Sending to Hugging Face:", user_input)

        result = client.predict(
            inputs=user_input,
            top_p=1,
            temperature=1,
            chat_counter=0,
            chatbot=[],
            api_name="/predict"
        )

        print("🧾 Raw API result:", result)  # 👈 THIS SHOWS YOU THE STRUCTURE

        # Try to extract if it's structured as expected
        try:
            reply = result[0][-1][1]
        except Exception as parse_error:
            print("❌ Failed to parse response:", parse_error)
            reply = f"⚠️ Unexpected API format: {result}"

        return jsonify({ "reply": reply })

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({ "reply": f"⚠️ Server Error: {str(e)}" }), 500

if __name__ == "__main__":
    app.run(port=3000, debug=True)
