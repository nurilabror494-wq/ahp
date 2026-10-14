"""
Vercel Serverless Function Entry Point for Flask
"""

import sys
import os
from urllib.parse import parse_qs, urlencode

# Tambahkan direktori root proyek ke sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Middleware untuk memetakan path asli ke PATH_INFO Flask dan membersihkan SCRIPT_NAME
class VercelMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Selalu bersihkan SCRIPT_NAME agar url_for() dan redirect() tidak menyisipkan prefix '/api/index'
        environ['SCRIPT_NAME'] = ''

        # 2. Ekstrak path yang diteruskan oleh rewrite Vercel via parameter __path
        qs = environ.get('QUERY_STRING', '')
        parsed = parse_qs(qs, keep_blank_values=True)

        if '__path' in parsed and parsed['__path']:
            raw_path = parsed.pop('__path')[0]
            # Bersihkan __path dari QUERY_STRING agar tidak mengotori request.args Flask
            clean_pairs = []
            for k, vs in parsed.items():
                for v in vs:
                    clean_pairs.append((k, v))
            environ['QUERY_STRING'] = urlencode(clean_pairs)

            # Normalisasi path
            if not raw_path.startswith('/'):
                raw_path = '/' + raw_path
            environ['PATH_INFO'] = raw_path
        else:
            # Fallback ke REQUEST_URI atau RAW_URI
            req_uri = (
                environ.get('REQUEST_URI') or 
                environ.get('RAW_URI') or 
                environ.get('HTTP_X_MATCHED_PATH') or 
                ''
            )
            path = req_uri.split('?')[0]
            if path and not path.startswith('/api/index'):
                environ['PATH_INFO'] = path
            else:
                environ['PATH_INFO'] = '/'

        # Pastikan PATH_INFO tidak kosong
        if not environ.get('PATH_INFO'):
            environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelMiddleware(app.wsgi_app)
