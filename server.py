from flask import Flask, redirect, request, make_response, render_template, url_for, send_from_directory, jsonify, session, flash
from flask_wtf.csrf import CSRFProtect, generate_csrf, validate_csrf
from flask_cors import CORS
from flask_session import Session
from flask_talisman import Talisman
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_resources import User
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from db import init_db, get_db_users, get_db_posts, get_db_file
from aes import aes_oauth2callback, aes_verify_email, aes_send_registration_email, authorize, aes_send_forgot_password_email, aes_forgot_password, confirm_token
from app_tasks import upload_file, validate_sanitize, validate_sanitize_bulk, is_direct_call
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import os
import hashlib
import base64
import binascii
import secrets

app = Flask(__name__, template_folder='public', static_folder='build', static_url_path='')

app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'session:'
app.config["SESSION_PERMANENT"] = True     # Sessions expire when the browser is closed
app.config["SESSION_TYPE"] = "filesystem"     # Store session data in files
app.config['SESSION_COOKIE_SAMESITE'] = 'strict'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app.secret_key = secrets.token_hex(32)

init_db()

csp = {
    'frame-ancestors': 'none',
    'default-src': ["'self'"],
    'script-src': [
        "'self'",
        "'unsafe-inline'",
        'https://cdn.jsdelivr.net',
        'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js'
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
        'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
    ],
}

Session(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.session_protection = 'strong'  # Important!
Talisman(
    app, 
    frame_options='DENY', 
    content_security_policy=csp, 
    force_https=False, 
    session_cookie_secure=False, 
    session_cookie_http_only=True
)
CORS(
    app, 
    supports_credentials=True, 
    origins=['http://localhost:5000','http://127.0.0.1:5000'],
    allow_headers=['Content-Type', 'X-CSRF-Token', 'X-CSRFToken']
)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["3 per 3 hours"],  # Applied to ALL routes
    storage_uri="memory://localhost:6379"
)

# driver = webdriver.Chrome()

# # For Firefox
# driver = webdriver.Firefox()

# # For Edge
# driver = webdriver.Edge()

# CLIENT_SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE')

# Authorizes Gmail API via OAuth2
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.

# regex patterns
PASS_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|\\;:',\.<>\/?]).{8,}$"
EMAIL_REGEX = r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$"
LEGAL_TEXT_REGEX = r"^[A-Za-z]+$"
TEXT_REGEX = r"^[A-Za-z0-9]+$"
POST_REGEX = r"^[A-Za-z0-9\s\.\,\!\?\-\'\"\n\r]+$"
NUM_REGEX = r"^\d{1,3}(\.\d{1,2})?$"
DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"
GEN_REGEX = r"^(male|female|nonbinary|other|prefer not to say)$"

# Regenerate session for logged-in user
def regenerate_session():
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

@app.after_request
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

@app.after_request
def cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = (
        "frame-ancestors 'none';"
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js;"                             
    )
    
    return response

@app.route('/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    aes_oauth2callback()

@app.route('/api/files/<file_id>')
def serve_file(file_id):
    """Returns actual file bytes with Content-Disposition"""
    file = get_db_file('read').get(ObjectId(file_id))
    response = make_response(file.read())
    
    # Set Content-Disposition here!
    response.headers['Content-Disposition'] = 'inline'
    response.headers['Content-Type'] = file.content_type
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response

# Serve React App
@app.route('/')
@app.route('/<string:name>', methods=['GET'])
def serve(name=None):
    # user = get_db_users().find_one({'username':ADMIN_NAME})

    # if user['creds'] is None:
    authorize()

    # logout()

    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    else:
        limiter.reset()
        return send_from_directory(app.static_folder, 'index.html')
    # return ''

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get username/email and password from the form

        data = request.form

        # This token is needed to compare the unsigned CSRF token to the signed CSRF token, which happens automatically. This line is needed for it to work properly
        token = data.get('csrf_token')

        identifier = data.get('loginName')
        password = data.get('loginPassword')

        # if not validate_csrf(token):
        #     return jsonify({'error':'Invalid token. Process terminated!'})

        data_list = [
            {
                'input': identifier,
                'pattern': TEXT_REGEX if '@' not in identifier else EMAIL_REGEX
            },
            {
                'input': password,
                'pattern': PASS_REGEX
            }
        ]

        if not validate_sanitize_bulk(data_list, 'input'):
            # return jsonify({'success': False, 'error': 'Invalid username/email or password'}), 401
            return render_template('login-form.html', err='Invalid username/email or password'), 401

        # Connect to MongoDB
        users_collection = get_db_users('read')

        # Find user by username or email
        user = users_collection.find_one({
            '$or': [
                {'username': {"$eq": identifier}},
                {'email': {"$eq": identifier}}
            ]
        })

        if not user:
            # return jsonify({'success': False, 'error': 'Invalid username/email or password'}), 401
            return render_template('login-form.html', err='Invalid username/email or password'), 401

        # Retrieve salt and hash from db
        salt_hex = user.get('salt')
        password_hash_db = user.get('password_hash')

        if not salt_hex or not password_hash_db:
            # return jsonify({'success': False, 'error': 'Invalid username/email or password'}), 401
            return render_template('login-form.html', err='Invalid username/email or password'), 401

        salt = binascii.unhexlify(salt_hex)
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        password_hash = binascii.hexlify(hash_bytes).decode('utf-8')

        if password_hash != password_hash_db:
            # return jsonify({'success': False, 'error': 'Invalid username/email or password'}), 401
            return render_template('login-form.html', err='Invalid username/email or password'), 401

        # Login successful
        print("Login successful!")

        user_obj = User(user.get('username'))

        # session.regenerate()
        # session.clear()
        # # Create response
        # response = make_response(jsonify({'message': 'Login successful'}))
        
        # # Delete the old session cookie
        # cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
        # response.set_cookie(cookie_name, '', expires=0)

        login_user(user_obj)
        
        regenerate_session()

        limiter.reset()
        return redirect('/')
    else:
        reason = request.args.get('reason')
        
        if reason == 'timeout':
            message = "Session expired due to inactivity"
        elif reason == 'expired':
            message = "Session expired"
        else:
            message = None
        # return send_from_directory(app.static_folder, 'login-form.html')
        limiter.reset()
        return render_template('login-form.html', display='d-none' if message is None else '', message=message)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        token = request.form.get('csrf_token').strip()

        if not email:
            return render_template('forgot-password.html', err='Email is required'), 400

        if not validate_sanitize(email, EMAIL_REGEX):
            return render_template('forgot-password.html', err='Invalid email address'), 400

        user = get_db_users('read').find_one({'email': {"$eq": email}})

        if not user:
            return render_template('forgot-password.html', err='No account associated with this email address'), 400
        # In a complete implementation, generate and email a reset token.
        message = "If this email exists in our system, a password reset link has been sent."

        aes_send_forgot_password_email(email, user['first_name'])

        limiter.reset()
        return render_template('forgot-password.html', message=message)
    else:
        token = request.args.get('token')

        if token and aes_forgot_password(token):
            return redirect(url_for('reset_password', token=token))
        else:
            return render_template('forgot-password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        csrf_token = request.form.get('csrf_token')
        token = request.form.get('token')

        # Basic validation
        if not password or not confirm_password:
            return render_template('reset-password.html', err='Please fill out all fields', token=token), 400
        if password != confirm_password:
            return render_template('reset-password.html', err='Passwords do not match', token=token), 400
        if not validate_sanitize(password, PASS_REGEX):
            return render_template('reset-password.html', err='Password does not meet requirements', token=token), 400

        # Re-extract the user email from token
        email = None
        try:
            # This will not be False because of the earlier check, but re-confirm for safety
            email = confirm_token(token)
        except Exception:
            return render_template('reset-password.html', err='Invalid reset token', token=token), 400
        if not email:
            return render_template('reset-password.html', err='Invalid or expired token', token=token), 400

        password_hash, salt_hex = hash_password(password)

        # Update user's password in DB (hash it first!)
        update_result = get_db_users('write').update_one({'email': {"$eq": email}}, {'$set': {'password_hash': password_hash, 'salt': salt_hex}})

        if update_result.modified_count == 0:
            return render_template('reset-password.html', err='Could not update password. Contact support.'), 500

        # Optionally: Invalidate any existing sessions here

        message = 'Your password has been reset successfully.'
        return render_template('reset-password.html', message=message)

    token = request.args.get('token')

    # GET, render form with token hidden
    return render_template('reset-password.html', token=token)

@app.route('/create-account', methods=['GET','POST'])
def create_account():
    if request.method == 'POST':

        users_collection = get_db_users('write')

        data = request.form
        token = data.get('csrf_token')

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        gender = data.get('gender')
        sexuality = data.get('sexuality')
        birthday = data.get('birthday')
        profile_picture = request.files['profile_picture'] if request.content_type.startswith('multipart/form-data') else None
        height = data.get('height')
        weight = data.get('weight')
        body_type = data.get('body_type')

        data_list = [
            {'input': username, 'pattern': TEXT_REGEX},
            {'input': email, 'pattern': EMAIL_REGEX},
            {'input': password, 'pattern': PASS_REGEX},
            {'input': confirm_password, 'pattern': PASS_REGEX},
            {'input': first_name, 'pattern': LEGAL_TEXT_REGEX},
            {'input': last_name, 'pattern': LEGAL_TEXT_REGEX},
            {"input": gender, "pattern": GEN_REGEX},
            {"input": birthday, "pattern": DATE_REGEX}
        ]

        # Basic validation
        if not username or not email or not password or not confirm_password:
            # return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            return render_template('create-account.html', err='Missing required fields'), 400

        if password != confirm_password:
            # return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
            return render_template('create-account.html', err='Passwords do not match'), 400

        if not validate_sanitize_bulk(data_list, 'input'):
            # return jsonify({'success': False, 'error': 'Invalid input'}), 400
            return render_template('create-account.html', err='Invalid input'), 400

        # Check if user already exists
        if users_collection.find_one({'$or': [{'username': {"$eq": username}}, {'email': {"$eq": email}}]}):
            # return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
            return render_template('create-account.html', err='Username or email already exists'), 400

        password_hash, salt_hex = hash_password(password)

        profile_picture_id = None

        try:
            if profile_picture and profile_picture.filename:
                profile_picture_id = upload_file(profile_picture)

            user_doc = {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'salt': salt_hex,
                'first_name': first_name,
                'last_name': last_name,
                'gender': gender,
                'birthday': birthday,
                'profile_picture': profile_picture_id,
                'is_verified': False
            }

            aes_send_registration_email(email, first_name)

            users_collection.insert_one(user_doc)
        except Exception as e:
            return render_template('create-account.html', err=f'An error occurred while creating the account. {e}'), 500

        limiter.reset()
        return render_template('create-account.html', message='Check your email for the verification link'), 200
    else:
        limiter.reset()    
        return render_template('create-account.html')

@app.route("/verify/<token>")
def verify_email(token):
    # Handles email verification after clicking the link.
    return aes_verify_email(token)

@app.route('/update-account',methods=['GET','POST'])
@login_required
def update_account():

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    # if 'username' not in session:
    #     return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    # username = session['username']

    # Accept both form-data and JSON
    if request.form:
        data = request.form
        files = request.files
    else:
        data = request.json or {}
        files = {}

    token = data.get('csrf_token')
    update_fields = {}

    # List of updatable fields
    updatable_fields = [
        {"field": "username", "pattern": TEXT_REGEX},
        {"field": "email", "pattern": EMAIL_REGEX},
        {"field": "first_name", "pattern": LEGAL_TEXT_REGEX},
        {"field": "last_name", "pattern": LEGAL_TEXT_REGEX},
        {"field": "gender", "pattern": GEN_REGEX},
        {"field": "birthday", "pattern": DATE_REGEX}
    ]

    for update_obj in updatable_fields:
        value = data.get(update_obj['field'])
        if value is not None and value != "":
            if not validate_sanitize(value, update_obj['pattern']):
                return jsonify({'success': False, 'error': 'Invalid input'}), 400
            update_fields[update_obj['field']] = value

    old_profile_picture_id = data.get('profile_picture_id') if data.get('profile_picture_id') != "None" else None
    remove_old_picture_id = data.get('remove_profile_picture') if data.get('remove_profile_picture') else None
    
    profile_picture = request.files['profile_picture'] if request.content_type.startswith('multipart/form-data') else None

    if profile_picture and remove_old_picture_id:
        return jsonify({'success': False, 'message': "These two operations can't happen concurrently"}), 400

    # Handle password update if provided
    new_password = data.get('password')
    confirm_password = data.get('confirm_password')
    if new_password:
        if not confirm_password or new_password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400

        password_hash, salt_hex = hash_password(new_password)
        
        update_fields['password_hash'] = password_hash
        update_fields['salt'] = salt_hex

    if not update_fields:
        return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
    new_username = None

    try:
        # Handle profile picture update
        update_fields['profile_picture'] = upload_file(profile_picture) if profile_picture and profile_picture.filename else None

        if isinstance(update_fields['profile_picture'], str):
            return jsonify({'error': update_fields['profile_picture']}), 400

        get_db_users('write').update_one({'username': {"$eq": current_user.id}}, {'$set': update_fields})

        if remove_old_picture_id or 'profile_picture' in update_fields:

            if old_profile_picture_id and get_db_file('read').get(ObjectId(old_profile_picture_id)) is not None:
                get_db_file('write').delete(ObjectId(old_profile_picture_id))

        if 'username' in update_fields and current_user.id != update_fields['username']:
            old_username = current_user.id
            new_username = update_fields['username']
            get_db_posts('write').update_many({'username': {"$eq": old_username}}, {'$set': {'username': new_username}})
    except DuplicateKeyError:
        return jsonify({'error': 'Username already taken'}), 409
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        # username = session['username']
    # session.regenerate()
    if new_username:
        current_user.id = new_username

    regenerate_session()
    limiter.reset()
    #if result.modified_count > 0:
    return redirect("/"+current_user.id)

@app.route('/logout', methods=['GET'])
def logout():

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    logout_user()

    regenerate_session()
    
    # session.clear()
    # # Create response
    # response = make_response(jsonify({'message': 'Login successful'}))
        
    # # Delete the old session cookie
    # cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
    # response.set_cookie(cookie_name, '', expires=0)

    limiter.reset()
    return redirect(url_for('login'))

@app.route('/create-post', methods=['GET','POST'])
@login_required
def create_post():

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    data = request.form
    token = data.get('csrf_token')
    profile_picture = data.get('profile_picture','').strip()
    content = data.get('content', '').strip()
    attachment = request.files['attachment'] if request.files['attachment'] else None

    # Only require content (text) for a post; photo/video is optional
    if not content:
        return jsonify({'error': 'Post content is required'}), 400

    if not validate_sanitize(content, POST_REGEX):
        return jsonify({'error': 'Invalid data'}), 400

    content = base64.b64encode(content.encode('utf-8'))

    attachment_id = None

    try:
        # Handle file upload if attachment is present
        if attachment and attachment.filename:
            attachment_id = upload_file(attachment)

        post = {
            'username': current_user.id,
            'content': content,
            'attachment': attachment_id,
            'created_at': datetime.now(),
            'likes': [],
            'comments': []
        }

        inserted_post = get_db_posts('write').insert_one(post)
    except Exception as e:
        print(f"Error creating post: {e}")
        return jsonify({'error': 'Failed to create post'}), 500
        
    print("Posted successfully!")

    regenerate_session()
    limiter.reset()
    return redirect('/')

@app.route('/update-post', methods=['GET','POST'])
@login_required
def update_post():

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    data = request.form
    token = data.get('csrf_token')
    post_id = ObjectId(data.get('id'))
    content = data.get('content', '').strip()

    if not post_id:
        return jsonify({'error': 'Post ID is required'}), 400

    # post = get_db_posts('read').find_one({'_id': post_id})
    # if not post:
    #     return jsonify({'error': 'Post not found'}), 404

    # Only allow the owner to update their post
    # if post.get('username') != session['username']:
    #     return jsonify({'error': 'Forbidden'}), 403

    update_fields = {}
    if content and validate_sanitize(content, POST_REGEX):
        update_fields['content'] = base64.b64encode(content.encode('utf-8'))

    if not update_fields:
        return jsonify({'error': 'No update fields provided'}), 400

    result = get_db_posts('write').update_one({'_id': {"$eq": post_id}, 'username': {"$eq": current_user.id}}, {'$set': update_fields})

    if result.matched_count == 0:
        # Either post doesn't exist or user doesn't own it
        return jsonify({'error': 'Post not found or forbidden'}), 403

    regenerate_session()
    limiter.reset()
    return redirect('/')

@app.route('/delete-post', methods=['GET','POST'])
@login_required
def delete_post():
    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    data = request.form
    post_id = ObjectId(data.get('id'))
    attachment_id = ObjectId(data.get('attachment_id'))
    token = data.get('csrf_token')
    if not post_id:
        return jsonify({'error': 'Post ID is required'}), 400

    try:
        post = get_db_posts('read').find_one({'_id': {"$eq": post_id}, 'username': {"$eq": current_user.id}})

        if not post:
            return jsonify({'error': 'Post not found or forbidden'}), 403

        result = get_db_file('write').delete(attachment_id)

        # Only allow the owner to delete their post
        result = get_db_posts('write').delete_one({'_id': {"$eq": post_id}, 'username': {"$eq": current_user.id}})

        if result.deleted_count == 0:
            return jsonify({'error': 'Post not found or forbidden'}), 403
    except Exception as e:
        return jsonify({'error': f'Error while deleting post: {str(e)}'}), 500

    regenerate_session()
    limiter.reset()
    return redirect('/')

@app.route('/api/current-user', methods=['POST'])
@login_required
def get_current_user():

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    return get_profile(current_user.id)

@app.route('/api/profile/<string:username>', methods=['POST'])
@login_required
def get_profile(username):

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    if not username:
        return None

    if not validate_sanitize(username, TEXT_REGEX):
        return jsonify({'error': 'Invalid username'})

    user = get_db_users('read').find_one({'username': {"$eq": username}})

    if user:
        user['profile_picture_id'] = str(user['profile_picture'])
        user['profile_picture'] = '/api/files/'+str(user['profile_picture']) if user['profile_picture'] is not None else user['profile_picture']
        user.pop('password_hash', None)
        user.pop('salt', None)
        user.pop('_id', None)
        user.pop('creds', None)
        user.update({'current_user':True}) if username == current_user.id else user.update({'current_user':False})

    limiter.reset()
    return user

@app.route('/api/posts', methods=['POST'])
@app.route('/api/posts/<string:username>', methods=['POST'])
@login_required
def get_posts(username=None):

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    posts_db = get_db_posts('read')
    posts = posts_db.find().sort('created_at', -1) if not username else posts_db.find({'username': {"$eq": username}}).sort('created_at', -1)
    posts = list(posts)
    
    for post in posts:
        post['_id'] = str(post['_id'])
        post['created_at'] = post['created_at'].isoformat() if 'created_at' in post else None
        post['attachment_id'] = str(post['attachment'])
        post['attachment'] = '/api/files/'+str(post['attachment']) if post['attachment'] is not None else post['attachment']

        profile = get_profile(post['username'])
        post['first_name'] = profile['first_name']
        post['last_name'] = profile['last_name']
        post['profile_picture'] = profile['profile_picture']
        post['content'] = post['content'].decode('utf-8') 

    limiter.reset()
    return jsonify({'posts': posts})

# Example API endpoint
@app.route('/api/hello')
def hello():
    return jsonify(message="Hello from Flask!")

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(port=5000)
