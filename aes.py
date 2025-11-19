from flask import request, url_for, redirect, jsonify, session, flash
from dotenv import load_dotenv
from db import get_db_users
from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from constants import (
    GMAIL_API_SERVICE, GMAIL_API_VERSION, GMAIL_SCOPES,
    TOKEN_EXPIRATION_SECONDS, EMAIL_FROM_ADDRESS,
    EMAIL_VERIFICATION_SUBJECT, EMAIL_PASSWORD_RESET_SUBJECT,
    HTTP_BAD_REQUEST, HTTP_OK
)
import logging
import os
import base64
import google.auth
import google_auth_oauthlib.flow
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_SERVICE = GMAIL_API_SERVICE
API_VERSION = GMAIL_API_VERSION
SCOPES = GMAIL_SCOPES

load_dotenv()

# Load and validate required environment variables
ADMIN_NAME = os.environ.get('ADMIN_NAME')
if not ADMIN_NAME:
    raise ValueError("ADMIN_NAME environment variable is required")

KEY = os.environ.get('ENCRYPTED_KEY')
if not KEY:
    raise ValueError("ENCRYPTED_KEY environment variable is required")

CLIENT_ID = os.environ.get('CLIENT_ID')
if not CLIENT_ID:
    raise ValueError("CLIENT_ID environment variable is required")

CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
if not CLIENT_SECRET:
    raise ValueError("CLIENT_SECRET environment variable is required")

CLIENT_SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE')
if not CLIENT_SECRETS_FILE:
    raise ValueError("CLIENT_SECRETS_FILE environment variable is required")

def get_routes():
    return [
        ('/oauth2callback', 'oauth2callback', oauth2callback, ['GET'])
    ]

def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('sec.oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true',prompt='consent')
    print(authorization_url)

    # Store the state so the callback can verify the auth server response.
    session['state'] = state

    return redirect(authorization_url)

def oauth2callback():
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('sec.oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    auth_response = request.url
    flow.fetch_token(authorization_response=auth_response)

    # Store credentials in the database
    credentials = flow.credentials
    get_db_users('write').update_one({"username": {"$eq": ADMIN_NAME}},{"$set": {"creds": credentials_to_dict(credentials)}})

    return ''

def credentials_to_dict(credentials):
    # Use the KEY from environment instead of generating a new one each time
    # This ensures credentials can be decrypted later
    cipher = Fernet(KEY.encode())

    return {
        'token': cipher.encrypt(credentials.token.encode()).decode(),
        'refresh_token': cipher.encrypt(credentials.refresh_token.encode()).decode(),
        'token_uri': credentials.token_uri,
        'scopes': credentials.scopes
    }

def confirm_token(token, expiration=TOKEN_EXPIRATION_SECONDS):
    """
    Validate the token and extract the email if valid.
    
    Args:
        token: The token to validate
        expiration: Token expiration time in seconds
        
    Returns:
        The email address if valid, False otherwise
    """
    try:
        s = URLSafeTimedSerializer(CLIENT_SECRET)
        return s.loads(token, salt="email-confirm", max_age=expiration)
    except SignatureExpired:
        logger.warning("Verification token expired.")
        return False
    except BadSignature:
        logger.warning("Invalid verification token.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating token: {str(e)}")
        return False

def aes_verify_email(token):
    email = confirm_token(token)

    if not email:
        return jsonify({'success':False, 'message':'Invalid or expired token'}), HTTP_BAD_REQUEST
    
    get_db_users('write').update_one({'email': {"$eq": email}},{'$set': {'is_verified': True}})
    return jsonify({'success': True, 'message': 'Your account has been verified! You can now use this web app'}), HTTP_OK

def aes_forgot_password(token):
    """
    Handle forgot password functionality given a token.
    Verifies the token, and allows the user to reset the password if valid.
    Returns (success, message/user email) tuple.
    """
    # Confirm and get the email using the provided token
    email = confirm_token(token)
    if not email:
        return jsonify({'success': False, 'message': 'Invalid or expired token.'}), HTTP_BAD_REQUEST
    
    users_collection = get_db_users('read')
    user = users_collection.find_one({'email': {"$eq": email}})
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), HTTP_BAD_REQUEST
    
    return True

def aes_send_registration_email(email, first_name):
    """
    Send a registration verification email to the user.
    
    Args:
        email: User's email address
        first_name: User's first name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cipher = Fernet(KEY.encode())
        users_collection = get_db_users('read')
        user = users_collection.find_one({'username': {"$eq": ADMIN_NAME}}, {'creds': 1})
        
        if not user or 'creds' not in user:
            logger.error("Cannot send registration email. No gmail creds found.")
            return False
            
        creds = user['creds']

        # Load credentials from the session.
        credentials = google.oauth2.credentials.Credentials(
            cipher.decrypt(creds["token"].encode()).decode(),
            refresh_token = cipher.decrypt(creds["refresh_token"].encode()).decode(),
            token_uri = creds["token_uri"],
            client_id = CLIENT_ID,
            client_secret = CLIENT_SECRET,
            scopes = creds["scopes"]
        )

        # Token Serializer
        s = URLSafeTimedSerializer(CLIENT_SECRET)
        token = s.dumps(email, salt="email-confirm")
        verify_url = url_for("sec.verify_email", token=token, _external=True)

        gmail = build(API_SERVICE, API_VERSION, credentials=credentials)

        message = EmailMessage()

        message.set_content('Hi '+first_name+',<br><br>Thank you for registering with us! <a href='+verify_url+'>Verify your email!</a>', subtype='html')

        message['To'] = email
        message['From'] = EMAIL_FROM_ADDRESS
        message['Subject'] = EMAIL_VERIFICATION_SUBJECT

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {
            'raw': encoded_message
        }
        
        send_message = (gmail.users().messages().send
                        (userId="me", body=create_message).execute())
        logger.info(f'Registration email sent. Message Id: {send_message["id"]}')
        return True
    except HttpError as error:
        logger.error(f'HTTP error occurred sending registration email: {error}')
        return False
    except Exception as error:
        logger.error(f'Unexpected error occurred sending registration email: {error}')
        return False

def aes_send_forgot_password_email(email, first_name):
    """
    Send a password reset email with a reset link to the specified user's email address.
    
    Args:
        email: User's email address
        first_name: User's first name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load user credentials for Gmail API
        cipher = Fernet(KEY.encode())
        user = get_db_users('read').find_one({'username': {"$eq": ADMIN_NAME}})
        if not user or 'creds' not in user:
            logger.error("Cannot send reset email. No gmail creds found for email: " + email)
            return False

        creds = user['creds']

        credentials = google.oauth2.credentials.Credentials(
            cipher.decrypt(creds["token"].encode()).decode(),
            refresh_token = cipher.decrypt(creds["refresh_token"].encode()).decode(),
            token_uri = creds["token_uri"],
            client_id = CLIENT_ID,
            client_secret = CLIENT_SECRET,
            scopes = creds["scopes"]
        )
        
        s = URLSafeTimedSerializer(CLIENT_SECRET)
        token = s.dumps(email, salt="email-confirm")
        reset_url = url_for("forgot_password", token=token, _external=True)

        gmail = build(API_SERVICE, API_VERSION, credentials=credentials)

        message = EmailMessage()
        message.set_content(
            f'Hi {first_name},<br><br>'
            f'You requested a password reset. '
            f'<a href="{reset_url}">Click here to reset your password!</a><br><br>'
            'If you did not request this, please ignore this email.',
            subtype='html'
        )

        message['To'] = email
        message['From'] = EMAIL_FROM_ADDRESS
        message['Subject'] = EMAIL_PASSWORD_RESET_SUBJECT

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {'raw': encoded_message}
        send_message = gmail.users().messages().send(userId="me", body=create_message).execute()
        logger.info(f"Password reset email sent. Message Id: {send_message['id']}")
        return True
    except HttpError as error:
        logger.error(f"HTTP error occurred sending password reset email: {error}")
        return False
    except Exception as error:
        logger.error(f"Unexpected error occurred sending password reset email: {error}")
        return False
