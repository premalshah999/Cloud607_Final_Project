# Lumina Photo Gallery 📸

A cloud-native social photo-sharing application built with Flask and deployed on AWS.

**Course:** DATA/MSML 650 - Cloud Computing Final Project

---

## Features

- 📷 Upload and share photos with captions
- ❤️ Like photos from friends
- 💬 Comment on photos
- 👥 Add friends and send direct messages
- 🔍 Browse photos by scope (Home/Profile/All)
- 🖼️ Beautiful responsive gallery layout

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, TailwindCSS, Vanilla JavaScript |
| Backend | Python 3.11, Flask 3.x, Gunicorn |
| Database | AWS RDS MySQL 8.0, AWS DynamoDB |
| Storage | AWS S3 |
| Compute | AWS EC2 (t2.micro) |
| Region | us-east-2 (Ohio) |

---

## Live Demo

**URL:** http://3.134.81.141:8080

---

## Project Structure

```
Cloud607_Final_Project/
├── app.py                  # Application entry point
├── app.html                # Frontend (single-page application)
├── requirements.txt        # Python dependencies
├── lumina/                 # Backend package
│   ├── __init__.py         # App factory
│   ├── config.py           # Configuration
│   ├── routes.py           # API endpoints (15+)
│   └── storage_dynamodb.py # AWS storage layer (30+ methods)
├── DEMO_PHOTOS/            # Sample photos for testing
├── REPORT.md               # Project report
└── ARCHITECTURE_DIAGRAMS.md # System architecture diagrams
```

---

## AWS Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Cloud (us-east-2)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    EC2      │  │   RDS       │  │     DynamoDB        │  │
│  │  Flask App  │──│  MySQL 8.0  │  │  - lumina_photos    │  │
│  │  Gunicorn   │  │  (users)    │  │  - lumina_comments  │  │
│  └──────┬──────┘  └─────────────┘  │  - lumina_messages  │  │
│         │                          └─────────────────────┘  │
│         │         ┌─────────────────────────────────────┐   │
│         └────────▶│  S3: lumina-photos-cloud650         │   │
│                   │  (image storage)                    │   │
│                   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Photos
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/photos` | List all photos |
| POST | `/api/photos` | Upload a photo |
| DELETE | `/api/photos/<id>` | Delete a photo |
| POST | `/api/photos/<id>/like` | Like a photo |
| GET | `/api/photos/<id>/image/thumb` | Get thumbnail |
| GET | `/api/photos/<id>/image/full` | Get full image |
| POST | `/api/photos/<id>/comments` | Add comment |
| GET | `/api/photos/<id>/comments` | Get comments |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/login` | Log in |
| POST | `/api/auth/logout` | Log out |
| GET | `/api/auth/me` | Get current user |

### Friends & Messaging
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/friends/request` | Send friend request |
| GET | `/api/friends/requests` | View pending requests |
| POST | `/api/friends/respond` | Accept/decline request |
| GET | `/api/friends/list` | List all friends |
| GET | `/api/messages` | Get messages with a friend |
| POST | `/api/messages` | Send a message |

---

## Environment Variables

Create a `.env` file based on `.env.example`:

| Variable | Description |
|----------|-------------|
| `STORAGE_BACKEND` | Set to `dynamodb` for AWS |
| `AWS_REGION` | AWS region (us-east-2) |
| `S3_BUCKET` | S3 bucket name |
| `DYNAMODB_PHOTOS_TABLE` | Photos table name |
| `DYNAMODB_COMMENTS_TABLE` | Comments table name |
| `DYNAMODB_MESSAGES_TABLE` | Messages table name |
| `DB_HOST` | RDS MySQL endpoint |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_NAME` | Database name |
| `SECRET_KEY` | Flask session secret |

---

## Documentation

- **[REPORT.md](REPORT.md)** - Project report with implementation details
- **[ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md)** - System architecture diagrams (Mermaid)

---

## Author

**Premal Shah** - DATA/MSML 650 Cloud Computing

---

## License

This project is for educational purposes (DATA/MSML 650 Final Project).
