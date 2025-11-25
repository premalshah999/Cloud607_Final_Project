"""
REST API Routes Module

This module defines all REST API endpoints for the Lumina application.
The API follows RESTful conventions and uses JSON for request/response bodies.

Blueprints:
    api_blueprint: Photo, comment, message, and friend endpoints
    auth_blueprint: Authentication endpoints (signup, login, logout)

Authentication:
    Session-based authentication using Flask sessions.
    Protected endpoints use the @login_required decorator.

API Endpoints:
    Authentication:
        POST /api/auth/signup  - Create new user account
        POST /api/auth/login   - Authenticate user
        POST /api/auth/logout  - End user session
        GET  /api/auth/me      - Get current user info
    
    Photos:
        GET  /api/photos              - List photos (with scope filter)
        POST /api/photos              - Upload new photo
        DELETE /api/photos/<id>       - Delete a photo
        POST /api/photos/<id>/like    - Like a photo
        GET/POST /api/photos/<id>/comments - Get/add comments
        GET  /api/photos/<id>/image/<variant> - Get image binary
    
    Social:
        GET  /api/users/lookup        - Find user by username
        POST /api/friends/request     - Send friend request
        GET  /api/friends/requests    - List pending requests
        POST /api/friends/respond     - Accept/decline request
        GET  /api/friends             - List friends
        GET/POST /api/messages        - Get/send messages
"""

from __future__ import annotations

from functools import wraps
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file, session, url_for
from PIL import Image

# Blueprint for photo-related API endpoints
api_blueprint = Blueprint('photos_api', __name__)

# Blueprint for authentication endpoints
auth_blueprint = Blueprint('auth_api', __name__)


def _storage():
    """Get the storage instance from Flask app extensions."""
    return _get_app_extension('photo_storage')


def _get_app_extension(key):
    """Helper to access Flask app extensions."""
    from flask import current_app
    return current_app.extensions[key]


def _current_user():
    """
    Get the currently authenticated user from session.
    
    Returns:
        dict: User object if authenticated, None otherwise
    """
    user_id = session.get('user_id')
    if not user_id:
        return None
    return _storage().get_user_by_id(user_id)


def login_required(fn):
    """
    Decorator to protect endpoints requiring authentication.
    
    Checks for valid session and passes user object to the wrapped function.
    Returns 401 Unauthorized if no valid session exists.
    
    Usage:
        @api_blueprint.route('/protected')
        @login_required
        def protected_endpoint(user):
            return jsonify({'user': user['username']})
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            return jsonify({'message': 'authentication required'}), 401
        return fn(*args, **kwargs, user=user)

    return wrapper


def _serialize_photo(photo):
    """
    Convert photo document to JSON-serializable format.
    
    Args:
        photo: MongoDB photo document
        
    Returns:
        dict: Photo data with URLs for thumbnail and full-res images
    """
    return {
        'id': photo['id'],
        'user_id': photo.get('user_id'),
        'username': photo['username'],
        'topic': photo['topic'],
        'caption': photo.get('caption', ''),
        'timestamp': photo['timestamp'],
        'likes': photo.get('likes', 0),
        'thumbnail': url_for('photos_api.get_image', photo_id=photo['id'], variant='thumb'),
        'fullRes': url_for('photos_api.get_image', photo_id=photo['id'], variant='full'),
    }


# =============================================================================
# Authentication Endpoints
# =============================================================================

@auth_blueprint.route('/auth/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'message': 'username and password are required'}), 400
    existing = _storage().get_user_by_username(username)
    if existing:
        return jsonify({'message': 'username already exists'}), 409
    user = _storage().create_user(username, password)
    session['user_id'] = user['id']
    return jsonify({'username': user['username']}), 201


@auth_blueprint.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'message': 'username and password are required'}), 400
    user = _storage().verify_user(username, password)
    if not user:
        return jsonify({'message': 'invalid credentials'}), 401
    session['user_id'] = user['id']
    return jsonify({'username': user['username']})


@auth_blueprint.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return '', 204


@auth_blueprint.route('/auth/me', methods=['GET'])
def me():
    user = _current_user()
    if not user:
        return jsonify({'message': 'not authenticated'}), 401
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'profilePic': url_for('photos_api.profile_picture', user_id=user['id'], variant='full'),
        'profileThumb': url_for('photos_api.profile_picture', user_id=user['id'], variant='thumb'),
    })


@api_blueprint.route('/users/lookup')
@login_required
def lookup_user(user):
    username = (request.args.get('username') or '').strip()
    if not username:
        return jsonify({'message': 'username required'}), 400
    target = _storage().get_user_by_username(username)
    if not target:
        return jsonify({'message': 'not found'}), 404
    return jsonify({'id': target['id'], 'username': target['username']})


@api_blueprint.route('/photos', methods=['GET'])
@login_required
def list_photos(user):
    scope = request.args.get('scope', 'home')
    topic_filter = request.args.get('topic')
    search_query = request.args.get('q', '').lower()

    if scope == 'profile':
        user_ids = [user['id']]
    elif scope == 'home':
        user_ids = [user['id']] + _storage().friend_ids(user['id'])
    elif scope == 'all':
        user_ids = None
    else:
        user_ids = None

    photos = _storage().list_photos(user_ids=user_ids)

    if topic_filter:
        photos = [p for p in photos if p['topic'].lower() == topic_filter.lower()]
    if search_query:
        photos = [
            p for p in photos
            if search_query in p['topic'].lower() or search_query in p['username'].lower()
        ]

    return jsonify([_serialize_photo(photo) for photo in photos])


@api_blueprint.route('/photos', methods=['POST'])
@login_required
def upload_photo(user):
    topic = request.form.get('topic', '').strip()
    caption = request.form.get('caption', '').strip()
    photo_file = request.files.get('photo')

    if not topic or not photo_file:
        return jsonify({'message': 'topic and photo are required'}), 400

    try:
        image = Image.open(photo_file.stream)
        image = image.convert('RGB')
    except Exception:
        return jsonify({'message': 'unable to process the uploaded file'}), 400

    record = _storage().add_photo(user, topic, image, caption)
    return jsonify({'id': record['id']}), 201


@api_blueprint.route('/photos/<photo_id>', methods=['DELETE'])
@login_required
def delete_photo(photo_id, user):
    deleted = _storage().delete_photo(photo_id)
    if not deleted:
        return jsonify({'message': 'photo not found'}), 404
    return '', 204


@api_blueprint.route('/photos/<photo_id>/like', methods=['POST'])
@login_required
def like_photo(photo_id, user):
    likes = _storage().increment_like(photo_id)
    if likes is None:
        return jsonify({'message': 'photo not found'}), 404
    return jsonify({'likes': likes})


@api_blueprint.route('/photos/<photo_id>/comments', methods=['GET', 'POST'])
@login_required
def comments(photo_id, user):
    if request.method == 'GET':
        comments = _storage().list_comments(photo_id)
        clean = []
        for c in comments:
            c.pop('_id', None)
            clean.append(c)
        return jsonify(clean)
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'message': 'text required'}), 400
    if not _storage().get_photo(photo_id):
        return jsonify({'message': 'photo not found'}), 404
    doc = _storage().add_comment(photo_id, user, text)
    doc.pop('_id', None)
    return jsonify(doc), 201


@api_blueprint.route('/photos/<photo_id>/image/<variant>', methods=['GET'])
@login_required
def get_image(photo_id, variant, user):
    if variant not in {'thumb', 'full'}:
        return jsonify({'message': 'invalid variant'}), 400
    data = _storage().get_image_bytes(photo_id, variant)
    if data is None:
        return jsonify({'message': 'not found'}), 404
    return send_file(BytesIO(data), mimetype='image/jpeg')


@api_blueprint.route('/users/profile-picture', methods=['POST'])
@login_required
def upload_profile_picture(user):
    file = request.files.get('photo')
    if not file:
        return jsonify({'message': 'photo is required'}), 400
    try:
        image = Image.open(file.stream)
        image = image.convert('RGB')
    except Exception:
        return jsonify({'message': 'unable to process the uploaded file'}), 400
    _storage().save_profile_picture(user['id'], image)
    return jsonify({'message': 'updated'}), 200


@api_blueprint.route('/users/<int:user_id>/profile-picture/<variant>', methods=['GET'])
@login_required
def profile_picture(user_id, variant, user):
    if variant not in {'thumb', 'full'}:
        return jsonify({'message': 'invalid variant'}), 400
    data = _storage().get_profile_picture(user_id, variant)
    if not data:
        return jsonify({'message': 'not found'}), 404
    return send_file(BytesIO(data), mimetype='image/jpeg')


@api_blueprint.route('/friends/request', methods=['POST'])
@login_required
def send_friend_request(user):
    data = request.get_json() or {}
    target_username = (data.get('username') or '').strip()
    if not target_username:
        return jsonify({'message': 'username required'}), 400
    target = _storage().get_user_by_username(target_username)
    if not target:
        return jsonify({'message': 'user not found'}), 404
    ok = _storage().send_friend_request(user['id'], target['id'])
    if not ok:
        return jsonify({'message': 'request already exists or invalid'}), 400
    return jsonify({'message': 'request sent'}), 201


@api_blueprint.route('/friends/requests', methods=['GET'])
@login_required
def list_requests(user):
    return jsonify(_storage().list_friend_requests(user['id']))


@api_blueprint.route('/friends/respond', methods=['POST'])
@login_required
def respond_request(user):
    data = request.get_json() or {}
    request_id = data.get('request_id')
    action = data.get('action')
    if request_id is None or action not in {'accept', 'decline'}:
        return jsonify({'message': 'invalid payload'}), 400
    ok = _storage().respond_friend_request(int(request_id), user['id'], action == 'accept')
    if not ok:
        return jsonify({'message': 'not found'}), 404
    return jsonify({'message': 'updated'})


@api_blueprint.route('/friends', methods=['GET'])
@login_required
def friends(user):
    return jsonify(_storage().list_friends(user['id']))


@api_blueprint.route('/messages', methods=['GET', 'POST'])
@login_required
def messages(user):
    if request.method == 'POST':
        data = request.get_json() or {}
        to_user_id = data.get('to_user_id')
        text = (data.get('text') or '').strip()
        if not to_user_id or not text:
            return jsonify({'message': 'to_user_id and text required'}), 400
        doc = _storage().send_message(user, int(to_user_id), text)
        doc.pop('_id', None)
        return jsonify(doc), 201
    other_id = request.args.get('user_id')
    if not other_id:
        return jsonify({'message': 'user_id required'}), 400
    msgs = _storage().list_messages(user['id'], int(other_id))
    for m in msgs:
        m.pop('_id', None)
    return jsonify(msgs)
