"""
Vercel Serverless Function Entry Point for Flask with WSGI Path Middleware
"""

import sys
import os

# Tambahkan direktori root proyek ke sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Middleware untuk menormalisasi PATH_INFO di serverless Vercel
class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        raw_uri = environ.get('REQUEST_URI', '').split('?')[0]
        matched_path = (
            environ.get('HTTP_X_MATCHED_PATH') or 
            environ.get('HTTP_X_FORWARDED_URI') or 
            environ.get('HTTP_X_ORIGINAL_URL') or
            (raw_uri if raw_uri and not raw_uri.startswith('/api') else None)
        )
        if matched_path and not matched_path.startswith('/api/index'):
            environ['PATH_INFO'] = matched_path

        path = environ.get('PATH_INFO', '')
        if path.startswith('/api/index.py'):
            environ['PATH_INFO'] = path[len('/api/index.py'):] or '/'
        elif path.startswith('/api/index'):
            environ['PATH_INFO'] = path[len('/api/index'):] or '/'
        elif path in ('/api', '/api/'):
            environ['PATH_INFO'] = '/'

        if not environ.get('PATH_INFO'):
            environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

# Pasang middleware ke app.wsgi_app
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
