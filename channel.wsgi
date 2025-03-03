#!/usr/bin/env python3
import sys
import os

# 1) If you have a virtualenv, activate it:
venv_path = "/home/u093/public_html/hw3/venv/bin/activate_this.py"
if os.path.isfile(venv_path):
    with open(venv_path) as f:
        code = compile(f.read(), venv_path, "exec")
        exec(code, dict(__file__=venv_path))
    print("✅ Virtual environment activated from:", venv_path)
else:
    print("⚠️  No virtual environment found at:", venv_path)

# 2) Ensure the hw3 folder is on Python’s import path:
project_path = "/home/u093/public_html/hw3"
if project_path not in sys.path:
    sys.path.insert(0, project_path)
print("✅ Project path added to sys.path:", project_path)

# 3) Now import the Flask app object from channel.py
try:
    from channel import app as application
    # If you need to initialize anything each time the app loads, uncomment:
    # from channel import initialize_channel
    # initialize_channel()
    print("✅ Successfully imported app from channel.py")
except Exception as e:
    print("❌ Error importing channel.py:", e)
    raise
