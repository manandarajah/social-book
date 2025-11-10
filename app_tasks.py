from datetime import datetime
from flask import request, jsonify
from werkzeug.utils import secure_filename
from db import get_db_file
import os
import re
import bleach
import hmac
import hashlib
import magic
import uuid

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_type(file_data):
    # Check actual file content, not just extension
    mime = magic.from_buffer(file_data, mime=True)
    allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime']
    return mime in allowed_mimes, mime

# Uploads file to the directory
def upload_file(file):
    # upload_folder = os.path.join(app.static_folder, dir)

    # if not os.path.exists('/tmp'):
    #     os.makedirs('/tmp')

    # Validate size
    file.seek(0, os.SEEK_END)
    if file.tell() > MAX_FILE_SIZE:
        return 'File too large', 413
    file.seek(0)

    file_data = file.read()

    if len(file_data) == 0:
        return "Empty File"

    filename = secure_filename(file.filename)

    # Validate file extension
    if not allowed_file(filename):
        return "File type not allowed"

    unique_filename = f"{uuid.uuid4()}_{filename}"

    # Save temporarily to validate content
    # temp_path = os.path.join('/tmp', unique_filename)
    # file.save(temp_path)
    
    file_validated, detected_mime = validate_file_type(file_data)

    # Validate actual file type
    if not file_validated:
        return 'Invalid file type', 400

    # file_path = os.path.join(upload_folder, filename)
    # file.save(file_path)

    return get_db_file('write').put(
                                    file_data,
                                    filename=filename,
                                    content_type=detected_mime,
                                    upload_date=datetime.utcnow()
                                )

# Function that accepts an array of JSON objects and field input for bulk input validation and sanitizing
def validate_sanitize_bulk(data_list, index):
    for data in data_list:
        if data[index] is not None:
            if not validate_sanitize(data[index], data['pattern']):
                return False

    return True

# Function that accepts value and regex pattern string for input validation and sanitizing
def validate_sanitize(value, pattern):
    # print(value+" "+pattern)
    # print(re.match(pattern, value))
    # print(bleach.clean(value))
    return True if re.fullmatch(pattern, value) and bleach.clean(value) == value else False

# Checks if URL call is direct call or referred call
def is_direct_call():
    return True if request.headers.get('Referer') is None else False

# def create_signed_token(token, app):
#     """
#     Create a signed version of the token for the HttpOnly cookie.
#     This prevents attackers from creating their own valid tokens.
#     """
#     signature = hmac.new(
#         app.secret_key.encode(),
#         token.encode(),
#         hashlib.sha256
#     ).hexdigest()
#     return f"{token}.{signature}"

# def verify_signed_token(signed_token, token, app):
#     """Verify that the signed token matches the provided token"""
#     try:
#         stored_token, signature = signed_token.rsplit('.', 1)
#         expected_signature = hmac.new(
#             app.secret_key.encode(),
#             stored_token.encode(),
#             hashlib.sha256
#         ).hexdigest()
        
#         # Timing-safe comparison
#         return (hmac.compare_digest(signature, expected_signature) and 
#                 hmac.compare_digest(stored_token, token))
#     except ValueError:
#         return False