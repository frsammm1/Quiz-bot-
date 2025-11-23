from flask import Flask
import threading
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SSC Quiz Bot is running!", 200

@app.route('/health')
def health():
    return {"status": "alive", "bot": "SSC Quiz Bot"}, 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Health server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def start_health_server():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Health check server started")
