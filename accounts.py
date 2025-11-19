from argon2 import PasswordHasher
from bson.objectid import ObjectId
from flask import jsonify, redirect, request, render_template, url_for
from pymongo.errors import DuplicateKeyError
from flask_login import login_required, current_user, login_user, logout_user
from aes import aes_forgot_password, aes_send_forgot_password_email, aes_send_registration_email, aes_verify_email, confirm_token
from flask_resources import User
from app_tasks import is_direct_call, upload_file, validate_sanitize, validate_sanitize_bulk
from db import get_db_file, get_db_posts, get_db_users
from regexes import PASS_REGEX, EMAIL_REGEX, TEXT_REGEX, LEGAL_TEXT_REGEX, GEN_REGEX, DATE_REGEX
from security_config import limiter, regenerate_session
from constants import (
    ERROR_INVALID_CREDENTIALS, ERROR_INVALID_INPUT, ERROR_MISSING_FIELDS,
    ERROR_PASSWORDS_MISMATCH, ERROR_USERNAME_EXISTS, ERROR_ACCOUNT_CREATION_FAILED,
    ERROR_LOGIN_FAILED, ERROR_UPDATE_FAILED, ERROR_DIRECT_CALL_DENIED,
    HTTP_OK, HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED, HTTP_FORBIDDEN, HTTP_CONFLICT,
    HTTP_INTERNAL_SERVER_ERROR, PASSWORD_RESET_RATE_LIMIT
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

context = None
ph = PasswordHasher()

def config_app(app):
    global context
    context = app

def get_routes():
    return [
        ('/login', 'login', login, ['GET', 'POST']),
        ('/logout', 'logout', logout, ['POST']),
        ('/create-account', 'create_account', create_account, ['GET','POST']),
        ('/update-account', 'update_account', update_account, ['POST']),
        ('/forgot-password', 'forgot_password', forgot_password, ['GET', 'POST']),
        ('/reset-password', 'reset_password', reset_password, ['GET', 'POST']),
        ('/verify/<token>', 'verify_email', verify_email, ['GET']),
        ('/api/current-user', 'get_current_user', get_current_user, ['POST']),
        ('/api/profile/<string:username>', 'get_profile', get_profile, ['POST'])
    ]

def login():
    """
    Handle user login with username/email and password.
    
    Returns:
        Redirect to home on success, login form with error on failure
    """
    if request.method == 'POST':
        data = request.form
        token = data.get('csrf_token')
        identifier = data.get('loginName', '').lower()
        password = data.get('loginPassword', '')
        
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
            logger.warning(f"Login attempt with invalid input format")
            return render_template('login-form.html', err=ERROR_INVALID_CREDENTIALS), HTTP_UNAUTHORIZED

        try:
            user = get_db_users('read').find_one({
                '$or': [
                    {'username': {"$eq": identifier}},
                    {'email': {"$eq": identifier}}
                ]}, {'username': 1, 'password_hash': 1}
            )

            if not user:
                logger.warning(f"Login attempt for non-existent user")
                return render_template('login-form.html', err=ERROR_INVALID_CREDENTIALS), HTTP_UNAUTHORIZED

            hash = user['password_hash']

            if not ph.verify(hash, password):
                logger.warning(f"Failed login attempt for user: {user.get('username')}")
                return render_template('login-form.html', err=ERROR_INVALID_CREDENTIALS), HTTP_UNAUTHORIZED

            logger.info(f"User logged in successfully: {user.get('username')}")
            user_obj = User(user.get('username'))
            login_user(user_obj)
            regenerate_session(context)

            if ph.check_needs_rehash(hash):
                hash = ph.hash(password)
                get_db_users('write').update_one({'username': {'$eq': current_user.id}}, {'$set': {'password_hash': hash}})
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return render_template('login-form.html', err=ERROR_LOGIN_FAILED), HTTP_INTERNAL_SERVER_ERROR

        return redirect('/')
    else:
        reason = request.args.get('reason')
        if reason == 'timeout':
            message = "Session expired due to inactivity"
        elif reason == 'expired':
            message = "Session expired"
        else:
            message = None
        return render_template('login-form.html', display='d-none' if message is None else '', message=message)

@limiter.limit(PASSWORD_RESET_RATE_LIMIT)
def forgot_password():
    """
    Handle forgot password requests.
    Rate limited to 5 requests per hour to prevent abuse.
    
    Returns:
        Password reset form or success message
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        token = request.form.get('csrf_token').strip()
        if not email:
            return render_template('forgot-password.html', err='Email is required'), 400

        if not validate_sanitize(email, EMAIL_REGEX):
            return render_template('forgot-password.html', err='Invalid email address'), 400

        user = get_db_users('read').find_one({'email': {"$eq": email}}, {'first_name': 1})

        if not user:
            return render_template('forgot-password.html', err='No account associated with this email address'), 400
        message = "If this email exists in our system, a password reset link has been sent."
        aes_send_forgot_password_email(email, user['first_name'])
        return render_template('forgot-password.html', message=message)
    else:
        token = request.args.get('token')
        if token and aes_forgot_password(token):
            return redirect(url_for('sec.reset_password', token=token))
        else:
            return render_template('forgot-password.html')

def reset_password():
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        csrf_token = request.form.get('csrf_token')
        token = request.form.get('token')

        if not password or not confirm_password:
            return render_template('reset-password.html', err='Please fill out all fields', token=token), 400
        if password != confirm_password:
            return render_template('reset-password.html', err='Passwords do not match', token=token), 400
        if not validate_sanitize(password, PASS_REGEX):
            return render_template('reset-password.html', err='Password does not meet requirements', token=token), 400

        email = None

        try:
            email = confirm_token(token).lower()
        except Exception:
            return render_template('reset-password.html', err='Invalid reset token', token=token), 400
        if not email:
            return render_template('reset-password.html', err='Invalid or expired token', token=token), 400

        password_hash = ph.hash(password)
        update_result = get_db_users('write').update_one({'email': {"$eq": email}}, {'$set': {'password_hash': password_hash}})

        if update_result.modified_count == 0:
            return render_template('reset-password.html', err='Could not update password. Contact support.'), 500
        message = 'Your password has been reset successfully.'
        return render_template('reset-password.html', message=message)

    token = request.args.get('token')
    return render_template('reset-password.html', token=token)

def create_account():
    """
    Handle user account creation.
    
    Returns:
        Success message on account creation, error message on failure
    """
    if request.method == 'POST':
        users_collection = get_db_users('write')
        data = request.form
        token = data.get('csrf_token')
        username = data.get('username', '').lower()
        email = data.get('email', '').lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        gender = data.get('gender', '')
        birthday = data.get('birthday', '')
        profile_picture = request.files.get('profile_picture') if request.content_type.startswith('multipart/form-data') else None

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

        if not username or not email or not password or not confirm_password:
            return render_template('create-account.html', err='Missing required fields'), 400

        if password != confirm_password:
            return render_template('create-account.html', err='Passwords do not match'), 400

        if not validate_sanitize_bulk(data_list, 'input'):
            logger.warning("Account creation attempt with invalid input")
            return render_template('create-account.html', err='Invalid input'), 400

        if users_collection.find_one({'$or': [{'username': {"$eq": username}}, {'email': {"$eq": email}}]}):
            logger.warning(f"Account creation attempt with existing username/email: {username}")
            return render_template('create-account.html', err='Username or email already exists'), 400

        password_hash = ph.hash(password)
        profile_picture_id = None

        try:
            if profile_picture and profile_picture.filename:
                profile_picture_id = upload_file(profile_picture)

            user_doc = {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'first_name': first_name,
                'last_name': last_name,
                'gender': gender,
                'birthday': birthday,
                'profile_picture': profile_picture_id,
                'is_verified': False
            }

            aes_send_registration_email(email, first_name)
            users_collection.insert_one(user_doc)
            logger.info(f"New account created: {username}")
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}")
            return render_template('create-account.html', err='An error occurred while creating the account.'), 500

        return render_template('create-account.html', message='Check your email for the verification link'), 200
    else:
        return render_template('create-account.html')

def verify_email(token):
    return aes_verify_email(token)

@login_required
def update_account():
    """
    Handle user account updates.
    
    Returns:
        Redirect to profile on success, error message on failure
    """
    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    if request.form:
        data = request.form
        files = request.files
    else:
        data = request.json or {}
        files = {}

    token = data.get('csrf_token')
    update_fields = {}

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
                logger.warning(f"Invalid input for field {update_obj['field']}")
                return jsonify({'success': False, 'error': 'Invalid input'}), 400
            update_fields[update_obj['field']] = value.lower() if update_obj['field'] == ('username' or 'email') else value


    old_profile_picture_id = data.get('profile_picture_id') if data.get('profile_picture_id') != "None" else None
    remove_old_picture_id = data.get('remove_profile_picture') if data.get('remove_profile_picture') else None
    profile_picture = request.files.get('profile_picture') if request.content_type.startswith('multipart/form-data') else None

    if profile_picture and remove_old_picture_id:
        return jsonify({'success': False, 'message': "These two operations can't happen concurrently"}), 400

    new_password = data.get('password')
    confirm_password = data.get('confirm_password')
    if new_password:
        if not confirm_password or new_password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400

        password_hash = ph.hash(new_password)
        update_fields['password_hash'] = password_hash

    if not update_fields and not profile_picture and not remove_old_picture_id:
        return jsonify({'success': False, 'error': 'No fields to update'}), 400

    new_username = None

    try:
        if profile_picture and profile_picture.filename:
            update_fields['profile_picture'] = upload_file(profile_picture)

            if isinstance(update_fields['profile_picture'], str):
                return jsonify({'error': update_fields['profile_picture']}), 400
        
        if remove_old_picture_id:
            update_fields['profile_picture'] = None

        if 'profile_picture' not in update_fields or update_fields['profile_picture'] is None:
            if not remove_old_picture_id:
                update_fields.pop('profile_picture', None)

        get_db_users('write').update_one({'username': {"$eq": current_user.id}}, {'$set': update_fields})

        if remove_old_picture_id or 'profile_picture' in update_fields:
            if old_profile_picture_id and get_db_file('read').get(ObjectId(old_profile_picture_id)) is not None:
                get_db_file('write').delete(ObjectId(old_profile_picture_id))

        if 'username' in update_fields and current_user.id != update_fields['username']:
            old_username = current_user.id
            new_username = update_fields['username']
            get_db_posts('write').update_many({'username': {"$eq": old_username}}, {'$set': {'username': new_username}})
            logger.info(f"Username changed from {old_username} to {new_username}")
    except DuplicateKeyError:
        logger.warning(f"Update attempt with duplicate username: {update_fields.get('username')}")
        return jsonify({'error': 'Username already taken'}), 409
    except Exception as e:
        logger.error(f"Error updating account: {str(e)}")
        return jsonify({'success': False, 'error': 'Error in updating account'}), 500

    if new_username:
        current_user.id = new_username

    regenerate_session(context)
    return redirect("/" + current_user.id)

@login_required
def get_current_user():

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    return get_profile(current_user.id)

@login_required
def get_profile(username):

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    if not username:
        return None

    if not validate_sanitize(username, TEXT_REGEX):
        return jsonify({'error': 'Invalid username'})

    user = get_db_users('read').find_one({'username': {"$eq": username}}, {'_id': 0, 'password_hash': 0, 'creds': 0})

    if user:
        user['profile_picture_id'] = str(user['profile_picture'])
        user['profile_picture'] = '/api/files/'+str(user['profile_picture']) if user['profile_picture'] is not None else user['profile_picture']
        user.update({'current_user':True}) if username == current_user.id else user.update({'current_user':False})

    return user

@limiter.exempt
def logout():
    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    logout_user()
    regenerate_session(context)
    return redirect(url_for('sec.login'))