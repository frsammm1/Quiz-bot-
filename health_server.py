from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SSC Quiz Bot is running!", 200

@app.route('/health')
def health():
    return {"status": "alive", "bot": "SSC Quiz Bot"}, 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

def start_health_server():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
