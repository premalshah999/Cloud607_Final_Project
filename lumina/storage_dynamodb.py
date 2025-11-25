"""
Storage Layer Module - AWS Native Architecture (DynamoDB + S3)

This module implements AWS-native storage using:
    - MySQL (RDS): User authentication, friendships (relational data)
    - DynamoDB: Photos metadata, comments, messages (NoSQL)
    - S3: Binary image storage (photos, profile pictures)

Design Rationale:
    DynamoDB provides fully managed, serverless NoSQL with automatic scaling.
    S3 provides durable, cost-effective binary storage for images.
    This architecture is fully within AWS Free Tier limits.

AWS Free Tier Limits:
    - DynamoDB: 25 GB storage, 25 WCU/RCU (forever free)
    - S3: 5 GB storage, 20,000 GET, 2,000 PUT (12 months)
    - RDS: 750 hours db.t3.micro (12 months)
"""

from __future__ import annotations

import base64
import uuid
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, List, Optional

import boto3
import pymysql
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from PIL import Image
from pymysql.connections import Connection
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash


class StorageDynamoDB:
    """
    AWS-native storage layer using DynamoDB and S3.
    
    Database Schema:
        MySQL Tables (RDS):
            - users: id, username, email, password_hash, created_at
            - friend_requests: id, requester_id, receiver_id, status, created_at
        
        DynamoDB Tables:
            - lumina_photos: PK=PHOTO#{id}, SK=META, user_id, username, topic, likes, timestamp
            - lumina_comments: PK=PHOTO#{photo_id}, SK=COMMENT#{timestamp}#{comment_id}
            - lumina_messages: PK=CONV#{conversation_id}, SK=MSG#{timestamp}
        
        S3 Bucket:
            - photos/{photo_id}_full.jpg
            - photos/{photo_id}_thumb.jpg
            - profiles/{user_id}_full.jpg (optional, stored directly without DB reference)
            - profiles/{user_id}_thumb.jpg (optional, stored directly without DB reference)
    """

    def __init__(self, config) -> None:
        """Initialize AWS and MySQL connections."""
        self.config = config
        self.max_full_width = config.MAX_FULL_WIDTH
        self.max_thumb_width = config.MAX_THUMB_WIDTH

        # AWS clients
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        self.s3 = boto3.client(
            's3',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        self.bucket_name = config.S3_BUCKET

        # DynamoDB tables
        self.photos_table = self.dynamodb.Table(config.DYNAMODB_PHOTOS_TABLE)
        self.comments_table = self.dynamodb.Table(config.DYNAMODB_COMMENTS_TABLE)
        self.messages_table = self.dynamodb.Table(config.DYNAMODB_MESSAGES_TABLE)

        self._ensure_ready()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def _ensure_ready(self) -> None:
        """Initialize MySQL database and tables."""
        self._ensure_database()
        self._ensure_tables()

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
                        email VARCHAR(255) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
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
    # User management (MySQL)
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
                    "SELECT id, username, email, password_hash, created_at FROM users WHERE username=%s",
                    (username,),
                )
                return cur.fetchone()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, email, created_at FROM users WHERE id=%s",
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
        }

    def save_profile_picture(self, user_id: int, image: Image.Image) -> Dict[str, Any]:
        """Save profile picture to S3 (no database column needed)."""
        thumb_bytes = self._resize_to_bytes(image, 200)
        full_bytes = self._resize_to_bytes(image, 800)
        
        thumb_key = f"profiles/{user_id}_thumb.jpg"
        full_key = f"profiles/{user_id}_full.jpg"
        
        self.s3.put_object(Bucket=self.bucket_name, Key=thumb_key, Body=thumb_bytes, ContentType='image/jpeg')
        self.s3.put_object(Bucket=self.bucket_name, Key=full_key, Body=full_bytes, ContentType='image/jpeg')
        
        return {'full': full_key, 'thumb': thumb_key}

    def get_profile_picture(self, user_id: int, variant: str) -> Optional[bytes]:
        """Get profile picture from S3 (attempts to fetch, returns None if not found)."""
        key = f"profiles/{user_id}_{'thumb' if variant == 'thumb' else 'full'}.jpg"
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError:
            return None

    # ------------------------------------------------------------------
    # Photos (DynamoDB + S3)
    # ------------------------------------------------------------------
    def list_photos(self, user_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """List photos, optionally filtered by user IDs."""
        try:
            if user_ids is None:
                # Scan all photos (for 'all' scope)
                response = self.photos_table.scan()
                items = response.get('Items', [])
            else:
                # Query photos for specific users
                items = []
                for uid in user_ids:
                    response = self.photos_table.query(
                        IndexName='user_id-index',
                        KeyConditionExpression=Key('user_id').eq(uid)
                    )
                    items.extend(response.get('Items', []))
            
            # Convert Decimal to int and sort by timestamp
            photos = [self._deserialize_photo(item) for item in items]
            photos.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            return photos
        except ClientError:
            return []

    def add_photo(self, user: Dict[str, Any], topic: str, image: Image.Image, caption: str = "") -> Dict[str, Any]:
        """Add a new photo."""
        photo_id = uuid.uuid4().hex
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        
        # Resize and upload to S3
        thumb_bytes = self._resize_to_bytes(image, self.max_thumb_width)
        full_bytes = self._resize_to_bytes(image, self.max_full_width)
        
        thumb_key = f"photos/{photo_id}_thumb.jpg"
        full_key = f"photos/{photo_id}_full.jpg"
        
        self.s3.put_object(Bucket=self.bucket_name, Key=thumb_key, Body=thumb_bytes, ContentType='image/jpeg')
        self.s3.put_object(Bucket=self.bucket_name, Key=full_key, Body=full_bytes, ContentType='image/jpeg')
        
        # Store metadata in DynamoDB
        item = {
            'PK': f'PHOTO#{photo_id}',
            'SK': 'META',
            'id': photo_id,
            'user_id': user['id'],
            'username': user['username'],
            'topic': topic,
            'caption': caption,
            'timestamp': timestamp,
            'likes': 0,
            'thumbnail_key': thumb_key,
            'full_key': full_key,
        }
        self.photos_table.put_item(Item=item)
        
        # Also create user index
        self.photos_table.put_item(Item={
            'PK': f'USER#{user["id"]}',
            'SK': f'PHOTO#{photo_id}',
            'photo_id': photo_id,
            'timestamp': timestamp,
        })
        
        return item

    def delete_photo(self, photo_id: str) -> Optional[Dict[str, Any]]:
        """Delete a photo and its associated data."""
        try:
            response = self.photos_table.get_item(Key={
                'PK': f'PHOTO#{photo_id}',
                'SK': 'META'
            })
            item = response.get('Item')
            if not item:
                return None
            
            # Delete from S3
            self.s3.delete_object(Bucket=self.bucket_name, Key=item.get('thumbnail_key', ''))
            self.s3.delete_object(Bucket=self.bucket_name, Key=item.get('full_key', ''))
            
            # Delete from DynamoDB (main photo record)
            self.photos_table.delete_item(Key={
                'PK': f'PHOTO#{photo_id}',
                'SK': 'META'
            })
            
            # Delete user index entry
            user_id = item.get('user_id')
            if user_id:
                self.photos_table.delete_item(Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'PHOTO#{photo_id}'
                })
            
            # Delete comments
            self._delete_comments_for_photo(photo_id)
            
            return self._deserialize_photo(item)
        except ClientError:
            return None

    def get_photo(self, photo_id: str) -> Optional[Dict[str, Any]]:
        """Get a single photo by ID."""
        try:
            response = self.photos_table.get_item(Key={
                'PK': f'PHOTO#{photo_id}',
                'SK': 'META'
            })
            item = response.get('Item')
            return self._deserialize_photo(item) if item else None
        except ClientError:
            return None

    def increment_like(self, photo_id: str) -> Optional[int]:
        """Increment like count for a photo."""
        try:
            response = self.photos_table.update_item(
                Key={
                    'PK': f'PHOTO#{photo_id}',
                    'SK': 'META'
                },
                UpdateExpression='SET likes = if_not_exists(likes, :zero) + :inc',
                ExpressionAttributeValues={':inc': 1, ':zero': 0},
                ReturnValues='UPDATED_NEW'
            )
            return int(response['Attributes'].get('likes', 0))
        except ClientError:
            return None

    def get_image_bytes(self, photo_id: str, variant: str) -> Optional[bytes]:
        """Get image bytes from S3."""
        photo = self.get_photo(photo_id)
        if not photo:
            return None
        key = photo.get('thumbnail_key') if variant == 'thumb' else photo.get('full_key')
        if not key:
            return None
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError:
            return None

    # ------------------------------------------------------------------
    # Comments (DynamoDB)
    # ------------------------------------------------------------------
    def list_comments(self, photo_id: str) -> List[Dict[str, Any]]:
        """List comments for a photo."""
        try:
            response = self.comments_table.query(
                KeyConditionExpression=Key('photo_id').eq(photo_id),
                ScanIndexForward=False  # Descending order
            )
            return [self._deserialize_item(item) for item in response.get('Items', [])]
        except ClientError:
            return []

    def add_comment(self, photo_id: str, user: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Add a comment to a photo."""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        comment_id = uuid.uuid4().hex
        
        item = {
            'photo_id': photo_id,
            'sort_key': f"{timestamp}#{comment_id}",
            'comment_id': comment_id,
            'user_id': user['id'],
            'username': user['username'],
            'text': text,
            'timestamp': timestamp,
        }
        self.comments_table.put_item(Item=item)
        return self._deserialize_item(item)

    def _delete_comments_for_photo(self, photo_id: str) -> None:
        """Delete all comments for a photo."""
        try:
            response = self.comments_table.query(
                KeyConditionExpression=Key('photo_id').eq(photo_id)
            )
            for item in response.get('Items', []):
                self.comments_table.delete_item(
                    Key={'photo_id': photo_id, 'sort_key': item['sort_key']}
                )
        except ClientError:
            pass

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
                    SELECT u.id, u.username, u.profile_pic_thumb_key as profile_pic_thumb_id
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
    # Messages (DynamoDB)
    # ------------------------------------------------------------------
    def send_message(self, from_user: Dict[str, Any], to_user_id: int, text: str) -> Dict[str, Any]:
        """Send a message to another user."""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        message_id = uuid.uuid4().hex
        
        # Create conversation ID (smaller user ID first for consistency)
        user1, user2 = sorted([from_user['id'], to_user_id])
        conversation_id = f"{user1}#{user2}"
        
        item = {
            'conversation_id': conversation_id,
            'sort_key': f"{timestamp}#{message_id}",
            'message_id': message_id,
            'from_user_id': from_user['id'],
            'from_username': from_user['username'],
            'to_user_id': to_user_id,
            'text': text,
            'timestamp': timestamp,
        }
        self.messages_table.put_item(Item=item)
        return self._deserialize_item(item)

    def list_messages(self, user_id: int, other_user_id: int) -> List[Dict[str, Any]]:
        """List messages between two users."""
        try:
            user1, user2 = sorted([user_id, other_user_id])
            conversation_id = f"{user1}#{user2}"
            
            response = self.messages_table.query(
                KeyConditionExpression=Key('conversation_id').eq(conversation_id),
                ScanIndexForward=True,  # Ascending order (oldest first)
                Limit=100
            )
            return [self._deserialize_item(item) for item in response.get('Items', [])]
        except ClientError:
            return []

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _deserialize_photo(self, item: Dict) -> Dict[str, Any]:
        """Convert DynamoDB item to standard dict, handling Decimals."""
        if not item:
            return {}
        result = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                result[key] = int(value)
            else:
                result[key] = value
        # Map keys for compatibility
        if 'thumbnail_key' in result:
            result['thumbnail_id'] = result['thumbnail_key']
        if 'full_key' in result:
            result['full_id'] = result['full_key']
        return result

    def _deserialize_item(self, item: Dict) -> Dict[str, Any]:
        """Convert DynamoDB item to standard dict."""
        if not item:
            return {}
        result = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                result[key] = int(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _resize_to_bytes(image: Image.Image, max_width: int) -> bytes:
        """Resize image and convert to JPEG bytes."""
        img = image.copy()
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            img = img.resize((max_width, int(height * ratio)), Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        return buffer.getvalue()
