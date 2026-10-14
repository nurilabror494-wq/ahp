"""
Vercel Serverless Function Entry Point for Flask
"""

import sys
import os

# Tambahkan direktori root proyek ke sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import Flask instance
from app import app

# Vercel serverless function mencari WSGI callable bernama 'app'
