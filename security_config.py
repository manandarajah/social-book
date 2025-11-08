from flask import Blueprint, session, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_cors import CORS
from flask_session import Session
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_resources import User
import os
import hashlib
import binascii

sec_bp = Blueprint('sec', __name__)

res_hash = None

login_manager = LoginManager()
login_manager.session_protection = 'strong'  # Important!
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["3 per 3 hours"],
    storage_uri="memory://localhost:6379"
)

def init_config(app, routes, blueprints):
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'session:'
    app.config["SESSION_PERMANENT"] = True     # Sessions expire when the browser is closed
    app.config["SESSION_TYPE"] = "filesystem"     # Store session data in files
    app.config['SESSION_COOKIE_SAMESITE'] = 'strict'

    # new_secrets = secrets.token_hex(32)
    # print(new_secrets)
    app.secret_key = os.environ.get('SECRETS')

    global res_hash
    res_hash = os.environ.get('RES_HASH')

    csp = {
        'frame-ancestors': 'none',
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            f"'{res_hash}'",
            'https://cdn.jsdelivr.net',
            'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js'
        ],
        'style-src': [
            "'self'",
            f"'{res_hash}'",
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
        force_https=False,
        session_cookie_secure=False, 
        session_cookie_http_only=True
    )

    login_manager.init_app(app)
    limiter.init_app(app)

    # Add all app-level routes from server.py as blueprint routes
    for rule, endpoint, view_func, methods in routes:
        sec_bp.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)

    for bp in blueprints:
        app.register_blueprint(bp)

    app.register_blueprint(sec_bp)

# Regenerate session for logged-in user
def regenerate_session(app):
    # print("session_interface:", type(app.session_interface))
    # print("has regenerate:", hasattr(app.session_interface, "regenerate"))
    # print("dir(session_interface):", [n for n in dir(app.session_interface) if not n.startswith("_")])
    
    session.clear()

    if hasattr(current_user, 'id'):
        session['_user_id'] = current_user.id

    app.session_interface.regenerate(session)

# Password hashing
def hash_password(password):
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)

    return binascii.hexlify(hash_bytes).decode('utf-8'), binascii.hexlify(salt).decode('utf-8')

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@limiter.request_filter
def exempt_render_requests():
    return request.path in ['/health', '/favicon.ico']

@limiter.request_filter
def exempt_api_requests():
    return 'logout' in request.path or (hasattr(current_user, 'id') and current_user.is_authenticated and current_user.is_active)

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

@sec_bp.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = (
        "frame-ancestors 'none';"
        "default-src 'self'; "
        f"style-src 'self' '{res_hash}' https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css; "
        f"script-src 'self' '{res_hash}' https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js;"                             
    )
    
    return response