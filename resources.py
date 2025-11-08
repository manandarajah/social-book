from flask import Blueprint, make_response
from bson.objectid import ObjectId
from db import get_db_file

res_bp = Blueprint('res', __name__)

def get_routes():
    return [('/api/files/<file_id>', 'serve_file', serve_file, ['GET'])]

def serve_file(file_id):
    """Returns actual file bytes with Content-Disposition"""
    file = get_db_file('read').get(ObjectId(file_id))
    response = make_response(file.read())
    
    # Set Content-Disposition here!
    response.headers['Content-Disposition'] = 'inline'
    response.headers['Content-Type'] = file.content_type
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response