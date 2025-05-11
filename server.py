from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app) 

client = openai.OpenAI()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        assistant_reply = response.choices[0].message.content
        return jsonify({"reply": assistant_reply})
    except Exception as e:
        print("Error:", e)
        return jsonify({"reply": "⚠️ Error contacting OpenAI."})

if __name__ == "__main__":
    app.run(port=5000) 
