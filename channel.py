"""
channel.py - A simple channel server for CalcWizard
"""

import os
import json
import re
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

print("LOADED channel.py!")

# Constants
MAX_MESSAGES = 100
MAX_AGE_SECONDS = 86400

class ConfigClass(object):
    SECRET_KEY = "This is an INSECURE secret!! DO NOT use this in production!!"

def parse_timestamp(ts):
    try:
        return float(ts)
    except ValueError:
        try:
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception as e:
            print("Error parsing timestamp:", ts, e)
            return 0

# Create Flask app
app = Flask(__name__)
CORS(app)
app.config.from_object(__name__ + ".ConfigClass")
app.app_context().push()

# Hub config
HUB_URL = "http://vm146.rz.uni-osnabrueck.de/hub"
HUB_AUTHKEY = "Crr-K24d-2N"  # For registering with the hub

# Channel config
CHANNEL_AUTHKEY = "0987654321"   # For clients calling your channel
CHANNEL_NAME = "CalcWizard: The Math Helper"
CHANNEL_ENDPOINT = "https://vm146.rz.uni-osnabrueck.de/u093/hw3/channel.wsgi"

HUB_URL = 'http://vm146.rz.uni-osnabrueck.de/hub'

CHANNEL_FILE = "messages.json"
CHANNEL_TYPE_OF_SERVICE = "aiweb24:chat"

@app.cli.command("register")
def register_command():
    """
    Registers this channel with the hub using the HUB_AUTHKEY
    """
    response = requests.post(
        HUB_URL + "/channels",
        headers={"Authorization": "authkey " + HUB_AUTHKEY},
        json={
            "name": CHANNEL_NAME,
            "endpoint": CHANNEL_ENDPOINT,
            "authkey": CHANNEL_AUTHKEY,
            "type_of_service": CHANNEL_TYPE_OF_SERVICE,
        }
    )
    if response.status_code != 200:
        print("Error creating channel:", response.status_code)
        print(response.text)
    else:
        print("✅ Channel registered successfully!")

def check_authorization(req):
    if "Authorization" not in req.headers:
        print("❌ No Authorization header found.")
        return False

    raw_auth = req.headers["Authorization"]
    expected = "authkey " + CHANNEL_AUTHKEY

    # Print with repr() to catch hidden chars
    print("Received (raw):", repr(raw_auth))
    print("Expected:", repr(expected))

    # Also strip to remove trailing spaces/newlines
    stripped_auth = raw_auth.strip()
    print("Received (stripped):", repr(stripped_auth))

    # Print code points for each character
    print("Received code points:", [ord(c) for c in stripped_auth])
    print("Expected code points:", [ord(c) for c in expected])

    if stripped_auth != expected:
        print("❌ Mismatch.")
        return False

    return True


@app.route("/health", methods=["GET"])
def health_check():
    # Must send the channel authkey in the header to pass
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({"name": CHANNEL_NAME}), 200

@app.route("/", methods=["GET"])
def home_page():
    # Must have correct Authorization
    if not check_authorization(request):
        return "Invalid authorization", 400

    messages = enforce_message_limits(read_messages())
    return jsonify(messages)

@app.route("/", methods=["POST"])
def send_message():
    print("we got to send_message")
    # Must have correct Authorization
    if not check_authorization(request):
        return "Invalid authorization", 400

    message = request.json
    if not message:
        return "No message", 400
    if "content" not in message:
        return "No content", 400
    if "sender" not in message:
        return "No sender", 400
    if "timestamp" not in message:
        return "No timestamp", 400

    extra = message.get("extra", None)
    original_content = message["content"]

    # Filtering: only math-related
    if not re.search(r"[0-9+\-*/().]", original_content):
        filtered_content = "[Filtered] Off-topic message for CalcWizard."
    else:
        filtered_content = original_content

    new_message = {
        "content": filtered_content,
        "sender": message["sender"],
        "timestamp": message["timestamp"],
        "extra": extra
    }

    messages = read_messages()
    messages.append(new_message)

    # Active response: if expression found, evaluate
    math_match = re.search(r"([\d.\(\)]+(?:\s*[\+\-\*/]\s*[\d.\(\)]+)+)", original_content)
    if math_match:
        math_expr = math_match.group(1)
        try:
            result = eval(math_expr, {"__builtins__": None}, {})
            response_text = f"Result: {result}"
        except Exception:
            response_text = "Error: Unable to evaluate the expression. Please check your math syntax."

        active_response = {
            "content": response_text,
            "sender": "CalcWizard",
            "timestamp": time.time(),
            "extra": None
        }
        messages.append(active_response)

    # Enforce message limits
    messages = enforce_message_limits(messages)
    save_messages(messages)
    return "OK", 200

def read_messages():
    try:
        with open(CHANNEL_FILE, "r") as f:
            messages = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        messages = []
    return messages

def save_messages(messages):
    with open(CHANNEL_FILE, "w") as f:
        json.dump(messages, f)

def enforce_message_limits(messages):
    now = time.time()
    # Remove old messages
    messages = [m for m in messages if now - parse_timestamp(m["timestamp"]) <= MAX_AGE_SECONDS]
    # Trim if over max
    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]
    return messages

def initialize_channel():
    if not os.path.exists(CHANNEL_FILE) or not read_messages():
        welcome_message = {
            "content": "Welcome to CalcWizard: The Math Helper! Send me a math expression...",
            "sender": "System",
            "timestamp": time.time(),
            "extra": None
        }
        save_messages([welcome_message])

if __name__ == "__main__":
    initialize_channel()
    app.run(port=5001, debug=True)
