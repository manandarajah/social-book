from bson.objectid import ObjectId
from flask import Blueprint, jsonify, redirect, request
from accounts import get_profile
from flask_login import login_required, current_user
from datetime import datetime, timezone
from security_config import regenerate_session
from regexes import POST_REGEX, TEXT_REGEX
from app_tasks import is_direct_call, upload_file, validate_sanitize
from db import get_db_file, get_db_posts
import base64

posts_bp = Blueprint('posts', __name__)
context = None

def config_app(app):
    global context
    context = app

def get_routes():
    return [
        ('/create-post', 'create_post', create_post, ['POST']),
        ('/update-post', 'update_post', update_post, ['POST']),
        ('/delete-post', 'delete_post', delete_post, ['POST']),
        ('/api/posts', 'get_posts', get_posts, ['POST']),
        ('/api/posts/<string:username>', 'get_posts', get_posts, ['POST'])
    ]

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
            'created_at': datetime.now(timezone.utc),
            'likes': [],
            'comments': []
        }

        inserted_post = get_db_posts('write').insert_one(post)
    except Exception as e:
        print(f"Error creating post: {e}")
        return jsonify({'error': 'Failed to create post'}), 500
        
    print("Posted successfully!")

    regenerate_session(context)
    return redirect('/')

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

    regenerate_session(context)
    return redirect('/')

@login_required
def delete_post():
    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    data = request.form
    post_id = ObjectId(data.get('id'))
    attachment_id = ObjectId(data.get('attachment_id')) if data.get("attachment_id") != "None" else None
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

    regenerate_session(context)
    return redirect('/')

@login_required
def get_posts(username=None):

    if is_direct_call():
        return jsonify({'error': 'Direct calls are not allowed. Access denied!'}), 400

    posts_db = get_db_posts('read')
    posts = posts_db.find().sort('created_at', -1) if not username else posts_db.find({'username': {"$eq": username}}).sort('created_at', -1)
    posts = list(posts)
    
    for post in posts:
        post['_id'] = str(post['_id'])
        post['created_at'] = post['created_at'].replace(tzinfo=timezone.utc).isoformat()
        post['attachment_id'] = str(post['attachment'])
        post['attachment'] = '/api/files/'+str(post['attachment']) if post['attachment'] is not None else post['attachment']

        profile = get_profile(post['username'])
        post['first_name'] = profile['first_name']
        post['last_name'] = profile['last_name']
        post['profile_picture'] = profile['profile_picture']
        post['content'] = post['content'].decode('utf-8') 

    return jsonify({'posts': posts})