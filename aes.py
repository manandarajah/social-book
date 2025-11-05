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
import logging
import os
import base64
import google.auth
import google_auth_oauthlib.flow
import requests

API_SERVICE="gmail"
API_VERSION="v1"
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

load_dotenv()

ADMIN_NAME = os.environ.get('ADMIN_NAME')
KEY = os.environ.get('ENCRYPTED_KEY')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
CLIENT_SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE')
TOKEN_EXPIRATION_SECONDS = 900  # 15 minutes

def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true',prompt='consent')
    print(authorization_url)

    # Store the state so the callback can verify the auth server response.
    session['state'] = state

    return redirect(authorization_url)

def aes_oauth2callback():
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    auth_response = request.url
    flow.fetch_token(authorization_response=auth_response)

    # Store credentials in the database
    credentials = flow.credentials
    get_db_users('write').update_one({"username": {"$eq": ADMIN_NAME}},{"$set": {"creds": credentials_to_dict(credentials)}})

    return ''

def credentials_to_dict(credentials):
    key = Fernet.generate_key()
    print(key.decode())
    cipher = Fernet(key)

    return {
        'token': cipher.encrypt(credentials.token.encode()).decode(),
        'refresh_token': cipher.encrypt(credentials.refresh_token.encode()).decode(),
        'token_uri': credentials.token_uri,
        'scopes': credentials.scopes
    }

def confirm_token(token, expiration=TOKEN_EXPIRATION_SECONDS):
    # Validate the token and extract the email if valid.
    try:
        s = URLSafeTimedSerializer(CLIENT_SECRET)
        return s.loads(token, salt="email-confirm", max_age=expiration)
    except SignatureExpired:
        logging.warning("Verification token expired. Ask the user to request a new verification email.")
        return False
    except BadSignature:
        logging.warning("Invalid verification token.")
        return False

def aes_verify_email(token):
    email = confirm_token(token)

    if not email:
        return jsonify({'success':False, 'message':'Invalid or expired token'}), 400
    
    get_db_users('write').update_one({'email': {"$eq": email}},{'$set': {'is_verified': True}})
    return jsonify({'success': True, 'message': 'Your account has been verified! You can now use this web app'}), 200

def aes_forgot_password(token):
    """
    Handle forgot password functionality given a token.
    Verifies the token, and allows the user to reset the password if valid.
    Returns (success, message/user email) tuple.
    """
    # Confirm and get the email using the provided token
    email = confirm_token(token)
    if not email:
        return jsonify({'success': False, 'message': 'Invalid or expired token.'}), 400
    
    users_collection = get_db_users('read')
    user = users_collection.find_one({'email': {"$eq": email}})
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 400
    
    return True

def aes_send_registration_email(email, first_name):
    try:
        print("a")
        cipher = Fernet(KEY.encode())
        print("b")
        users_collection = get_db_users('read')
        print("c")
        user = users_collection.find_one({'username': {"$eq": ADMIN_NAME}})
        print("d")
        creds = user['creds']
        print("e")

        # Load credentials from the session.
        credentials = google.oauth2.credentials.Credentials(
            cipher.decrypt(creds["token"].encode()).decode(),
            refresh_token = cipher.decrypt(creds["refresh_token"].encode()).decode(),
            token_uri = creds["token_uri"],
            client_id = CLIENT_ID,
            client_secret = CLIENT_SECRET,
            scopes = creds["scopes"]
        )
        print("f")

        # Token Serializer
        s = URLSafeTimedSerializer(CLIENT_SECRET)
        print("g")
        token = s.dumps(email, salt="email-confirm")
        print("h")
        verify_url = url_for("verify_email", token=token, _external=True)
        print("i")

        gmail = build(API_SERVICE, API_VERSION, credentials=credentials)
        print("j")

        message = EmailMessage()
        print("k")

        message.set_content('Hi '+first_name+',<br><br>Thank you for registering with us! <a href='+verify_url+'>Verify your email!</a>', subtype='html')
        print("l")

        message['To'] = email
        print("m")
        message['From'] = "no-reply@dating-social-media.com"
        print("n")
        message['Subject'] = "Verify Email - Dating Social Media"
        print("o")

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()) \
            .decode()
        print("p")

        create_message = {
            'raw': encoded_message
        }
        print("q")
        # pylint: disable=E1101
        send_message = (gmail.users().messages().send
                        (userId="me", body=create_message).execute())
        print("r")
        print(F'Message Id: {send_message["id"]}')
        print("s")
        # return requests.post(
        #     "https://api.mailgun.net/v3/mg.socialmedia.com/messages",
        #     auth=("api", CLIENT_SECRET),
        #     data={"from": "Dating Social Media <no-reply@mg.socialmedia.com>",
        #         "to": email,
        #         "subject": "Verify Email - Dating Social Media",
        #         "template": create_message}
        # )
    except HttpError as error:
        print(F'An error occurred: {error}')
        send_message = None

def aes_send_forgot_password_email(email, first_name):
    """
    Sends a forgot password email with a reset link to the specified user's email address.
    """
    try:
        # Load user credentials for Gmail API
        cipher = Fernet(KEY.encode())
        user = get_db_users('read').find_one({'username': {"$eq": ADMIN_NAME}})
        if not user or 'creds' not in user:
            print("Cannot send reset email. No gmail creds found for email: " + email)
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
        message['From'] = "no-reply@dating-social-media.com"
        message['Subject'] = "Password Reset - Dating Social Media"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {'raw': encoded_message}
        send_message = gmail.users().messages().send(userId="me", body=create_message).execute()
        print(f"Password reset email sent. Message Id: {send_message['id']}")
        return True
    except Exception as error:
        print(f"An error occurred sending password reset email: {error}")
        return False
