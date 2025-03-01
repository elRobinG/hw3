from flask import Flask, request, jsonify
import json
import requests
import time
import re
import os
from datetime import datetime
from flask_cors import CORS  # Import Flask-CORS
app = Flask(__name__)

import traceback
@app.errorhandler(500)
def internal_error(exception):
   return "<pre>"+traceback.format_exc()+"</pre>"
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
        
# Constants for message limiting
MAX_MESSAGES = 100
MAX_AGE_SECONDS = 86400

class ConfigClass(object):
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

# Create Flask app and enable CORS for all routes
app = Flask(__name__)
CORS(app)  # This will add Access-Control-Allow-Origin: * to all responses
app.config.from_object(__name__ + '.ConfigClass')
app.app_context().push()

# Hub and Channel configuration
HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "CalcWizard: The Math Helper"
CHANNEL_ENDPOINT = "http://localhost:5001"
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT
    response = requests.post(HUB_URL + '/channels',
                             headers={'Authorization': 'authkey ' + CHANNEL_AUTHKEY},
                             data=json.dumps({
                                "name": CHANNEL_NAME,
                                "endpoint": CHANNEL_ENDPOINT,
                                "authkey": CHANNEL_AUTHKEY,
                                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))
    if response.status_code != 200:
        print("Error creating channel: " + str(response.status_code))
        print(response.text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    if app.debug:
        return True
    if 'Authorization' not in request.headers:
        return False
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name': CHANNEL_NAME}), 200

@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    messages = enforce_message_limits(read_messages())
    return jsonify(messages)

@app.route('/', methods=['POST'])
def send_message():
    if not check_authorization(request):
        return "Invalid authorization", 400

    message = request.json
    if not message:
        return "No message", 400
    if 'content' not in message:
        return "No content", 400
    if 'sender' not in message:
        return "No sender", 400
    if 'timestamp' not in message:
        return "No timestamp", 400

    extra = message.get('extra', None)
    original_content = message['content']

    # --- Filtering ---
    # For a math-help channel, we filter messages that do not contain any math symbols or digits.
    if not re.search(r"[0-9+\-*/().]", original_content):
        filtered_content = "[Filtered] Off-topic message for CalcWizard."
    else:
        filtered_content = original_content

    new_message = {
        'content': filtered_content,
        'sender': message['sender'],
        'timestamp': message['timestamp'],
        'extra': extra
    }

    messages = read_messages()
    messages.append(new_message)

    # --- Active Response ---
    # Instead of only processing messages that are entirely math expressions,
    # try to extract a math expression from the input.
    math_match = re.search(r'([\d\.\(\)]+(?:\s*[\+\-\*/]\s*[\d\.\(\)]+)+)', original_content)
    if math_match:
        math_expr = math_match.group(1)
        try:
            # Evaluate the extracted math expression in a restricted environment.
            result = eval(math_expr, {"__builtins__": None}, {})
            response_text = f"Result: {result}"
        except Exception as e:
            response_text = "Error: Unable to evaluate the expression. Please check your math syntax."
        active_response = {
            'content': response_text,
            'sender': "CalcWizard",
            'timestamp': time.time(),
            'extra': None
        }
        messages.append(active_response)

    # Enforce message limits (by age and total count) before saving.
    messages = enforce_message_limits(messages)
    save_messages(messages)
    return "OK", 200

def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

def enforce_message_limits(messages):
    current_time = time.time()
    messages = [msg for msg in messages if current_time - parse_timestamp(msg["timestamp"]) <= MAX_AGE_SECONDS]
    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]
    return messages

def initialize_channel():
    if not os.path.exists(CHANNEL_FILE) or not read_messages():
        welcome_message = {
            'content': "Welcome to CalcWizard: The Math Helper! Send me a math expression, and I'll compute it for you.",
            'sender': "System",
            'timestamp': time.time(),
            'extra': None
        }
        save_messages([welcome_message])

if __name__ == '__main__':
    initialize_channel()
    app.run(port=5001, debug=True)
