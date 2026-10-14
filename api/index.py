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

# Middleware untuk memetakan REQUEST_URI asli ke PATH_INFO Flask di Vercel
class VercelMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Selalu kosongkan SCRIPT_NAME agar url_for() dan redirect() tidak menyisipkan prefix '/api/index'
        environ['SCRIPT_NAME'] = ''

        # 2. Ambil path asli yang diminta client dari REQUEST_URI, RAW_URI, atau HTTP_X_MATCHED_PATH
        req_uri = (
            environ.get('REQUEST_URI') or 
            environ.get('RAW_URI') or 
            environ.get('HTTP_X_MATCHED_PATH') or 
            ''
        )
        path = req_uri.split('?')[0]

        if path and not path.startswith('/api/index'):
            environ['PATH_INFO'] = path
        elif path.startswith('/api/index'):
            environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelMiddleware(app.wsgi_app)
