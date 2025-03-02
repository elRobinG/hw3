#!/usr/bin/env python3
import sys
import os

# 1) If you have a virtualenv, activate it:
venv_path = "/home/u093/public_html/hw3/venv/bin/activate_this.py"
if os.path.isfile(venv_path):
    with open(venv_path) as f:
        code = compile(f.read(), venv_path, "exec")
        exec(code, dict(__file__=venv_path))

# 2) Ensure the hw3 folder is on Python’s import path:
sys.path.insert(0, "/home/u093/public_html/hw3")

# 3) Now import the Flask app object from channel.py
from channel import app as application

# (Optionally call initialize_channel() if you want to run that every time.)
# from channel import initialize_channel
# initialize_channel()
