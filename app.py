"""
Lumina Photo Gallery - Main Application Entry Point

A full-stack photo sharing application built with Flask, MySQL, and MongoDB.
This module serves as the WSGI entry point for both development and production.

Course: Cloud 607 - Cloud Computing
Project: Final Project - Photo Gallery Application

Architecture:
    - Flask: Web framework and REST API
    - MySQL: User authentication and social features (friends)
    - MongoDB: Photo storage using GridFS, comments, and messages
    - Gunicorn: Production WSGI server

Author: [Your Name]
Date: November 2025
"""

from lumina import create_app

# Create the Flask application instance
# This is used by Gunicorn in production: gunicorn app:app
app = create_app()


if __name__ == '__main__':
    # Development server - use only for local testing
    # In production, use: gunicorn --bind 0.0.0.0:5000 app:app
    app.run(debug=True)
