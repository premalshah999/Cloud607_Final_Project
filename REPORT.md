# Lumina Photo Gallery – Final Report

## Abstract
Lumina is a cloud-ready web application that enables users to upload, browse, and curate photographic artifacts tagged by topic. The system couples a modern single-page frontend with a minimalist Flask backend that performs authentication, storage, metadata management, and media processing. This report documents the design rationale, implementation details, evaluation outcomes, and future research directions for the project.

## 1. Introduction
Modern creative communities rely on frictionless tools to share visual content. The objective of this project was to deliver an end-to-end photo gallery that supports uploads, topical discovery, search, and lightweight engagement (likes) with authenticated access. Emphasis was placed on rapid development, architectural clarity, and ease of deployment for academic demonstration purposes.

## 2. System Architecture
### 2.1 High-Level Overview
The system comprises two principal components:
1. **Frontend (Presentation Layer)** – `app.html` contains the entire user interface implemented with TailwindCSS and vanilla JavaScript. It provides masonry-style rendering, modal dialogs, search, topic filters, and client-side state management. The gallery is hidden until the user authenticates.
2. **Backend (Application + Data Layer)** – Flask application created via `lumina.create_app()`. It exposes RESTful endpoints under `/api` and serves static assets. Key submodules:
   - `lumina.config.Config`: resolves filesystem locations, database credentials, and constants.
   - `lumina.storage.Storage`: handles MySQL (users) and MongoDB GridFS (photo binaries + metadata).
   - `lumina.routes`: blueprints defining upload, list, delete, like, image streaming, and authentication endpoints.

### 2.2 Data Flow
1. User signs up or logs in (session cookie).
2. User selects a file and topic; frontend submits multipart POST to `/api/photos` with the session cookie.
3. `Storage` resizes images with Pillow, stores binaries in MongoDB GridFS, and records metadata (including MySQL user_id) in the `photos` collection.
4. Client refreshes its in-memory gallery via `GET /api/photos`; image URLs point to streaming endpoints backed by GridFS.
5. Likes and deletions are issued via their respective endpoints.

## 3. Implementation
### 3.1 Technology Stack
- **Backend**: Python 3, Flask 3.x, Pillow for image processing, PyMySQL for user persistence, PyMongo + GridFS for photo storage.
- **Frontend**: HTML5, TailwindCSS (CDN), Lucide icons, vanilla JS modules.
- **Persistence**: MySQL (users) and MongoDB (photos + binaries).

### 3.2 Key Design Decisions
- **Split persistence**: MySQL for users/authentication; MongoDB GridFS for photo binaries and metadata. This avoids filesystem coupling and supports concurrent access.
- **App Factory Pattern**: Provides clean separation between configuration, storage services, and blueprints, aligning with production Flask practices.
- **Session Authentication**: Users must sign up or log in to view the gallery and perform mutations; sessions are cookie-backed.
- **Client-Side State**: The frontend maintains topic filters, search queries, and cached photo arrays, reducing server complexity and keeping the UX responsive.

### 3.3 Notable Modules
- `lumina/storage.py`: Contains `Storage`, responsible for MySQL user management, MongoDB GridFS operations, resizing images to thumb/full, and metadata CRUD.
- `lumina/routes.py`: Implements validation and serialization helpers, photo/image endpoints, and authentication endpoints; streams images from GridFS.
- `app.html`: Orchestrates the UI, fetches data, handles modals (login, upload, view), and gates gallery visibility by authentication.

## 4. Evaluation
### 4.1 Functional Testing
Planned tests (to run once MySQL/Mongo are configured): use Flask’s test client to validate signup/login, upload → list → like → delete, and image streaming. Example:
```python
from io import BytesIO
from PIL import Image
from app import app
client = app.test_client()
client.post('/api/auth/signup', json={'username':'tester','password':'secret'})
img = Image.new('RGB', (50, 50), color='green')
buf = BytesIO(); img.save(buf, format='JPEG'); buf.seek(0)
r = client.post('/api/photos', data={'topic':'testing','photo':(buf,'demo.jpg')}, content_type='multipart/form-data')
assert r.status_code == 201
```

### 4.2 Usability Assessment
Manual exploratory testing confirms:
- Responsive gallery rendering across desktop breakpoints.
- Topic filters and search combinations operate instantly on cached data.
- Upload modal provides immediate thumbnail previews, and the UI recovers gracefully after server responses.
- Gallery is hidden until authentication, reducing anonymous access issues.

## 5. Discussion
### 5.1 Strengths
- Clear modular architecture: configuration, storage, and routing responsibilities are isolated.
- Minimal deployment footprint: `pip install -r requirements.txt` and `python app.py` (after MySQL/Mongo are running).
- Frontend delivers a polished user experience with modern UI components and informative toast notifications.

### 5.2 Limitations
- Any authenticated user can delete any photo; finer-grained ownership checks are not yet implemented.
- Image validation is coarse (presence check only); production systems should enforce MIME, size, and security scanning policies.
- Requires both MySQL and MongoDB services; failure of either disrupts the app. Remote deployments need credential hardening and SSL.

## 6. Future Work
1. Enforce per-user ownership on destructive actions; add rate limiting.
2. Add MIME/size limits and image scanning; move image processing to async workers for heavy loads.
3. Introduce pagination and caching headers to support large galleries.
4. Deploy to managed DB services (RDS/Aurora + Atlas) and serve frontend via CDN/S3; explore serverless API.
5. Integrate automated tests (pytest) and CI pipelines for regression prevention.

## 7. Conclusion
Lumina now demonstrates an authenticated, full-stack photo gallery that separates user identity (MySQL) from media storage (MongoDB GridFS). With the listed enhancements—authorization hardening, validation, and scalability work—the application can move from an academic prototype toward production readiness.
