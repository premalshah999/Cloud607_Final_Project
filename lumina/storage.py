"""
Storage Layer Module - Dual Database Architecture

This module implements a hybrid storage solution using:
    - MySQL: User authentication, friendships (relational data)
    - MongoDB: Photos (GridFS), comments, messages (document data)

Design Rationale:
    MySQL is used for structured relational data (users, friendships) where
    ACID transactions and referential integrity are important.
    
    MongoDB with GridFS is used for binary photo storage and flexible
    document structures (comments, messages) where horizontal scaling
    and schema flexibility are beneficial.

Classes:
    Storage: Main storage class handling all database operations
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import gridfs
import pymongo
import pymysql
from PIL import Image
from bson import ObjectId
from pymysql.connections import Connection
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash


class Storage:
    """
    Hybrid storage layer for the Lumina application.
    
    This class provides a unified interface for data storage using both
    MySQL (relational) and MongoDB (document) databases.
    
    Database Schema:
        MySQL Tables:
            - users: id, username, password_hash, profile_pic_id, created_at
            - friend_requests: id, requester_id, receiver_id, status, created_at
        
        MongoDB Collections:
            - photos: id, user_id, username, topic, caption, likes, timestamp
            - comments: photo_id, user_id, username, text, timestamp
            - messages: from_user_id, to_user_id, text, timestamp
            - fs.files/fs.chunks: GridFS binary storage for images
    
    Attributes:
        config: Application configuration object
        mongo_client: PyMongo client instance
        mongo_db: MongoDB database instance
        photos_col: Photos collection
        comments_col: Comments collection
        messages_col: Messages collection
        fs: GridFS instance for binary file storage
    """

    def __init__(self, config) -> None:
        """
        Initialize storage connections.
        
        Args:
            config: Configuration object with database connection details
        """
        self.config = config
        self.max_full_width = config.MAX_FULL_WIDTH
        self.max_thumb_width = config.MAX_THUMB_WIDTH

        self.mongo_client = pymongo.MongoClient(config.MONGO_URI)
        self.mongo_db = self.mongo_client[config.MONGO_DB]
        self.photos_col = self.mongo_db['photos']
        self.comments_col = self.mongo_db['comments']
        self.messages_col = self.mongo_db['messages']
        self.fs = gridfs.GridFS(self.mongo_db)

        self._ensure_ready()

    # ------------------------------------------------------------------
    # Initialization / connections
    # ------------------------------------------------------------------
    def _ensure_ready(self) -> None:
        self._ensure_database()
        self._ensure_tables()
        self.photos_col.create_index('timestamp')
        self.photos_col.create_index('topic')
        self.comments_col.create_index('photo_id')
        self.comments_col.create_index('timestamp')
        self.messages_col.create_index([('from_user_id', 1), ('to_user_id', 1), ('timestamp', -1)])

    def _ensure_database(self) -> None:
        with self._raw_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.config.DB_NAME}` CHARACTER SET utf8mb4")

    def _ensure_tables(self) -> None:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        profile_pic_id VARCHAR(64) NULL,
                        profile_pic_thumb_id VARCHAR(64) NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS friend_requests (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        requester_id INT NOT NULL,
                        receiver_id INT NOT NULL,
                        status ENUM('pending','accepted','declined') NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                try:
                    cur.execute("ALTER TABLE users ADD COLUMN profile_pic_id VARCHAR(64) NULL")
                except Exception:
                    pass
                try:
                    cur.execute("ALTER TABLE users ADD COLUMN profile_pic_thumb_id VARCHAR(64) NULL")
                except Exception:
                    pass

    @contextmanager
    def _raw_connection(self) -> Connection:
        conn = pymysql.connect(
            host=self.config.DB_HOST,
            port=self.config.DB_PORT,
            user=self.config.DB_USER,
            password=self.config.DB_PASSWORD,
            autocommit=True,
            cursorclass=DictCursor,
        )
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def connection(self) -> Connection:
        conn = pymysql.connect(
            host=self.config.DB_HOST,
            port=self.config.DB_PORT,
            user=self.config.DB_USER,
            password=self.config.DB_PASSWORD,
            database=self.config.DB_NAME,
            autocommit=True,
            cursorclass=DictCursor,
        )
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    def create_user(self, username: str, password: str) -> Dict[str, Any]:
        password_hash = generate_password_hash(password)
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, password_hash),
                )
                user_id = cur.lastrowid
        return {'id': user_id, 'username': username}

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, password_hash, profile_pic_id, profile_pic_thumb_id FROM users WHERE username=%s",
                    (username,),
                )
                return cur.fetchone()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, profile_pic_id, profile_pic_thumb_id FROM users WHERE id=%s",
                    (user_id,),
                )
                return cur.fetchone()

    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not check_password_hash(user['password_hash'], password):
            return None
        return {
            'id': user['id'],
            'username': user['username'],
            'profile_pic_id': user.get('profile_pic_id'),
            'profile_pic_thumb_id': user.get('profile_pic_thumb_id'),
        }

    def save_profile_picture(self, user_id: int, image: Image.Image) -> Dict[str, Any]:
        thumb_bytes = self._resize_to_bytes(image, 200)
        full_bytes = self._resize_to_bytes(image, 800)
        thumb_id = self.fs.put(thumb_bytes, filename=f"profile_{user_id}_thumb.jpg", content_type='image/jpeg')
        full_id = self.fs.put(full_bytes, filename=f"profile_{user_id}_full.jpg", content_type='image/jpeg')
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET profile_pic_id=%s, profile_pic_thumb_id=%s WHERE id=%s",
                    (str(full_id), str(thumb_id), user_id),
                )
        return {'full': str(full_id), 'thumb': str(thumb_id)}

    def get_profile_picture(self, user_id: int, variant: str) -> Optional[bytes]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        key = 'profile_pic_thumb_id' if variant == 'thumb' else 'profile_pic_id'
        file_id = user.get(key)
        if not file_id:
            return None
        try:
            grid_out = self.fs.get(ObjectId(file_id))
            return grid_out.read()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Photos (Mongo)
    # ------------------------------------------------------------------
    def list_photos(self, user_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        query = {}
        if user_ids is not None:
            query['user_id'] = {'$in': user_ids}
        return list(self.photos_col.find(query).sort('timestamp', -1))

    def add_photo(self, user: Dict[str, Any], topic: str, image: Image.Image, caption: str = "") -> Dict[str, Any]:
        photo_id = uuid.uuid4().hex
        thumb_bytes = self._resize_to_bytes(image, self.max_thumb_width)
        full_bytes = self._resize_to_bytes(image, self.max_full_width)

        thumb_id = self.fs.put(thumb_bytes, filename=f"{photo_id}_thumb.jpg", content_type='image/jpeg')
        full_id = self.fs.put(full_bytes, filename=f"{photo_id}_full.jpg", content_type='image/jpeg')

        doc = {
            'id': photo_id,
            'user_id': user['id'],
            'username': user['username'],
            'topic': topic,
            'caption': caption,
            'timestamp': int(datetime.utcnow().timestamp() * 1000),
            'likes': 0,
            'thumbnail_id': thumb_id,
            'full_id': full_id,
        }
        self.photos_col.insert_one(doc)
        return doc

    def delete_photo(self, photo_id: str) -> Optional[Dict[str, Any]]:
        doc = self.photos_col.find_one({'id': photo_id})
        if not doc:
            return None
        self.photos_col.delete_one({'id': photo_id})
        self._remove_file(doc.get('thumbnail_id'))
        self._remove_file(doc.get('full_id'))
        self.comments_col.delete_many({'photo_id': photo_id})
        return doc

    def get_photo(self, photo_id: str) -> Optional[Dict[str, Any]]:
        return self.photos_col.find_one({'id': photo_id})

    def increment_like(self, photo_id: str) -> Optional[int]:
        updated = self.photos_col.find_one_and_update(
            {'id': photo_id},
            {'$inc': {'likes': 1}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if not updated:
            return None
        return updated.get('likes', 0)

    def get_image_bytes(self, photo_id: str, variant: str) -> Optional[bytes]:
        doc = self.get_photo(photo_id)
        if not doc:
            return None
        file_id = doc.get('thumbnail_id') if variant == 'thumb' else doc.get('full_id')
        if not file_id:
            return None
        try:
            grid_out = self.fs.get(ObjectId(file_id))
            return grid_out.read()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Comments (Mongo)
    # ------------------------------------------------------------------
    def list_comments(self, photo_id: str) -> List[Dict[str, Any]]:
        return list(self.comments_col.find({'photo_id': photo_id}).sort('timestamp', -1))

    def add_comment(self, photo_id: str, user: Dict[str, Any], text: str) -> Dict[str, Any]:
        doc = {
            'photo_id': photo_id,
            'user_id': user['id'],
            'username': user['username'],
            'text': text,
            'timestamp': int(datetime.utcnow().timestamp() * 1000),
        }
        self.comments_col.insert_one(doc)
        return doc

    # ------------------------------------------------------------------
    # Friendships (MySQL)
    # ------------------------------------------------------------------
    def send_friend_request(self, requester_id: int, receiver_id: int) -> bool:
        if requester_id == receiver_id:
            return False
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM friend_requests WHERE requester_id=%s AND receiver_id=%s AND status='pending'",
                    (requester_id, receiver_id),
                )
                if cur.fetchone():
                    return False
                cur.execute(
                    "INSERT INTO friend_requests (requester_id, receiver_id) VALUES (%s, %s)",
                    (requester_id, receiver_id),
                )
        return True

    def list_friend_requests(self, user_id: int) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT fr.id, fr.requester_id, u.username AS requester_username, fr.status, fr.created_at
                    FROM friend_requests fr
                    JOIN users u ON u.id = fr.requester_id
                    WHERE fr.receiver_id=%s AND fr.status='pending'
                    ORDER BY fr.created_at DESC
                    """,
                    (user_id,),
                )
                return list(cur.fetchall())

    def respond_friend_request(self, request_id: int, receiver_id: int, accept: bool) -> bool:
        new_status = 'accepted' if accept else 'declined'
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE friend_requests SET status=%s WHERE id=%s AND receiver_id=%s",
                    (new_status, request_id, receiver_id),
                )
                return cur.rowcount > 0

    def list_friends(self, user_id: int) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.username, u.profile_pic_thumb_id
                    FROM friend_requests fr
                    JOIN users u ON u.id = CASE WHEN fr.requester_id=%s THEN fr.receiver_id ELSE fr.requester_id END
                    WHERE fr.status='accepted' AND (fr.requester_id=%s OR fr.receiver_id=%s)
                    """,
                    (user_id, user_id, user_id),
                )
                return list(cur.fetchall())

    def friend_ids(self, user_id: int) -> List[int]:
        return [f['id'] for f in self.list_friends(user_id)]

    # ------------------------------------------------------------------
    # Messages (Mongo)
    # ------------------------------------------------------------------
    def send_message(self, from_user: Dict[str, Any], to_user_id: int, text: str) -> Dict[str, Any]:
        doc = {
            'from_user_id': from_user['id'],
            'from_username': from_user['username'],
            'to_user_id': to_user_id,
            'text': text,
            'timestamp': int(datetime.utcnow().timestamp() * 1000),
        }
        self.messages_col.insert_one(doc)
        return doc

    def list_messages(self, user_id: int, other_user_id: int) -> List[Dict[str, Any]]:
        return list(
            self.messages_col.find(
                {
                    '$or': [
                        {'from_user_id': user_id, 'to_user_id': other_user_id},
                        {'from_user_id': other_user_id, 'to_user_id': user_id},
                    ]
                }
            ).sort('timestamp', 1).limit(100)
        )

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _remove_file(self, file_id):
        if not file_id:
            return
        try:
            self.fs.delete(ObjectId(file_id))
        except Exception:
            pass

    @staticmethod
    def _resize_to_bytes(image: Image.Image, max_width: int) -> bytes:
        img = image.copy()
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            img = img.resize((max_width, int(height * ratio)), Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        return buffer.getvalue()
