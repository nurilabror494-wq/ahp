"""
Vercel Serverless Function Entry Point for Flask
"""

import sys
import os

# Tambahkan direktori root proyek ke sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Pastikan SCRIPT_NAME kosong agar URL publik Flask tidak diawali '/api/index'
class CleanScriptNameMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = ''
        return self.wsgi_app(environ, start_response)

app.wsgi_app = CleanScriptNameMiddleware(app.wsgi_app)
