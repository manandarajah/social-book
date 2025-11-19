"""
Constants and configuration values for the social site application.
Centralizing constants improves maintainability and reduces magic values.
"""

# File upload constraints
ALLOWED_FILE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime']
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# Email configuration
EMAIL_FROM_ADDRESS = "no-reply@social-media.com"
EMAIL_VERIFICATION_SUBJECT = "Verify Email - SocialSite"
EMAIL_PASSWORD_RESET_SUBJECT = "Password Reset - SocialSite"

# Token expiration
TOKEN_EXPIRATION_SECONDS = 900  # 15 minutes

# Gmail API configuration
GMAIL_API_SERVICE = "gmail"
GMAIL_API_VERSION = "v1"
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

# Rate limiting
DEFAULT_RATE_LIMIT = "3 per 3 hours"

# Session configuration
SESSION_COOKIE_MAX_AGE = 3600  # 1 hour

# Database operation types
DB_OPERATION_READ = "read"
DB_OPERATION_WRITE = "write"

# HTTP status codes (for clarity)
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_PAYLOAD_TOO_LARGE = 413
HTTP_INTERNAL_SERVER_ERROR = 500

# Error messages (generic to prevent information leakage)
ERROR_INVALID_CREDENTIALS = "Invalid username/email or password"
ERROR_INVALID_INPUT = "Invalid input"
ERROR_MISSING_FIELDS = "Missing required fields"
ERROR_PASSWORDS_MISMATCH = "Passwords do not match"
ERROR_USERNAME_EXISTS = "Username or email already exists"
ERROR_ACCOUNT_CREATION_FAILED = "An error occurred while creating the account."
ERROR_LOGIN_FAILED = "An error occurred during login"
ERROR_UPDATE_FAILED = "Error in updating account"
ERROR_POST_CREATION_FAILED = "Failed to create post"
ERROR_POST_NOT_FOUND = "Post not found or forbidden"
ERROR_DIRECT_CALL_DENIED = "Direct calls are not allowed. Access denied!"
ERROR_FILE_TOO_LARGE = "File too large"
ERROR_INVALID_FILE_TYPE = "Invalid file type"
ERROR_FILE_TYPE_NOT_ALLOWED = "File type not allowed"
ERROR_EMPTY_FILE = "Empty File"
