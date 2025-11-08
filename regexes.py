# regex patterns
PASS_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|\\;:',\.<>\/?]).{8,}$"
EMAIL_REGEX = r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$"
LEGAL_TEXT_REGEX = r"^[A-Za-z]+$"
TEXT_REGEX = r"^[A-Za-z0-9]+$"
POST_REGEX = r"^[A-Za-z0-9\s\.\,\!\?\-\'\"\n\r]+$"
NUM_REGEX = r"^\d{1,3}(\.\d{1,2})?$"
DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"
GEN_REGEX = r"^(male|female|nonbinary|other|prefer not to say)$"