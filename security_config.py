from flask import Blueprint, session, request
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_cors import CORS
from flask_session import Session
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

sec_bp = Blueprint('sec', __name__)

res_hash_1 = None
res_hash_2 = None

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["3 per 3 hours"],
    default_limits_deduct_when=lambda r: r.status_code >= 400,
    storage_uri="memory://localhost:6379"
)

def init_config(app, routes):
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'session:'
    app.config["SESSION_PERMANENT"] = True     # Sessions expire when the browser is closed
    app.config["SESSION_TYPE"] = "filesystem"     # Store session data in files
    app.config['SESSION_COOKIE_SAMESITE'] = 'strict'

    # new_secrets = secrets.token_hex(32)
    # print(new_secrets)
    app.secret_key = os.environ.get('SECRETS')

    global res_hash_1, res_hash_2
    res_hash_1 = os.environ.get('RES_HASH_1')
    res_hash_2 = os.environ.get('RES_HASH_2')

    csp = {
        'frame-ancestors': 'none',
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            f"'{res_hash_1}' '{res_hash_2}'",
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
            'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js'
        ],
        'style-src': [
            "'self'",
            f"'{res_hash_1}' '{res_hash_2}'",
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
            'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
        ],
    }
    
    Session(app)
    CSRFProtect(app)
    CORS(
        app, 
        supports_credentials=True, 
        origins=['http://localhost:5000','http://127.0.0.1:5000'], 
        allow_headers=['Content-Type', 'X-CSRF-Token', 'X-CSRFToken']
    )
    Talisman(
        app,
        frame_options='DENY', 
        content_security_policy=csp, 
        force_https=False, # false because the current infrastructure (render.com), already forces HTTPS connection, do this configuration is not needed.
        session_cookie_secure=True, 
        session_cookie_http_only=True
    )

    limiter.init_app(app)

    # Add all app-level routes from server.py as blueprint routes
    for rule, endpoint, view_func, methods in routes:
        sec_bp.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)

    app.register_blueprint(sec_bp)

# Regenerate session for logged-in user
def regenerate_session(app):
    session.clear()

    if hasattr(current_user, 'id'):
        session['_user_id'] = current_user.id

    app.session_interface.regenerate(session)

@limiter.request_filter
def exempt_render_requests():
    return request.path in ['/health', '/favicon.ico']

@limiter.request_filter
def exempt_api_requests():
    return hasattr(current_user, 'id') and current_user.is_authenticated and current_user.is_active

@limiter.request_filter
def exempt_reloads():
    return request.method == 'GET' or (request.get_json(silent=True) is not None and 'reload' in request.get_json(silent=True).get('nav_type'))

@sec_bp.after_request
def generate_csrf_cookie(response):

    token = generate_csrf()
    # signed_token = create_signed_token(token, app)
    
    # Cookie 1: HttpOnly cookie with signed token (JavaScript CANNOT read this)
    # response.set_cookie(
    #     'csrf_token_signed',
    #     signed_token,
    #     httponly=True,      # JavaScript cannot access this
    #     samesite='Strict',  # Strict prevents CSRF attacks
    #     secure=False,       # Set to True in production with HTTPS
    #     max_age=3600        # 1 hour
    # )
    
    # Cookie 2: Regular cookie with token (JavaScript CAN read this)
    response.set_cookie(
        'csrf_token',
        token,
        httponly=False,     # JavaScript can read this
        samesite='Strict',  # Same protection
        secure=False,       # Set to True in production with HTTPS
        max_age=3600
    )
    
    # return jsonify({'message':'Generated and Signed CSRF token'})
    return response

@sec_bp.after_request
def cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response