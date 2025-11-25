# Lumina Photo Gallery 📸

A social photo-sharing app built with Flask, MySQL, and AWS services.

**Course:** Cloud607 Final Project

---

## Features

- 📷 Upload and share photos with captions
- ❤️ Like photos from friends
- 💬 Comment on photos
- 👥 Add friends and chat with them
- 🔍 Search photos by topic or username
- 🖼️ Beautiful masonry-style gallery

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, TailwindCSS, JavaScript |
| Backend | Python Flask |
| Database | MySQL (users), DynamoDB (photos) |
| Storage | AWS S3 (images) |
| Deployment | Docker (local), AWS EC2 (cloud) |

---

## Quick Start (Local - Docker)

**Requirements:** Docker and Docker Compose installed

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-USERNAME/Cloud607_Final_Project.git
cd Cloud607_Final_Project

# 2. Create environment file
cp .env.example .env

# 3. Start everything
docker-compose up -d --build

# 4. Open in browser
open http://localhost:8080
```

**Useful commands:**
```bash
docker-compose logs -f web    # View logs
docker-compose restart        # Restart services
docker-compose down           # Stop everything
```

---

## Deploy to AWS

See **[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)** for step-by-step instructions.

**Summary:** Uses EC2 + RDS + DynamoDB + S3 (all AWS Free Tier eligible)

---

## Project Structure

```
Cloud607_Final_Project/
├── app.py              # Application entry point
├── app.html            # Frontend (single-page app)
├── lumina/             # Backend package
│   ├── __init__.py     # App factory
│   ├── config.py       # Configuration
│   ├── routes.py       # API endpoints
│   ├── storage.py      # MongoDB storage
│   └── storage_dynamodb.py  # AWS DynamoDB storage
├── docker-compose.yml  # Local deployment
├── requirements.txt    # Python dependencies
└── REPORT.md          # Project report
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

### Social
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/friends` | List friends |
| POST | `/api/friends/add` | Send friend request |
| POST | `/api/friends/accept` | Accept request |
| GET | `/api/messages/<friend>` | Get chat messages |
| POST | `/api/messages/<friend>` | Send message |

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `STORAGE_BACKEND` | `mongodb` or `dynamodb` | `dynamodb` |
| `MYSQL_HOST` | MySQL server address | `localhost` |
| `MYSQL_USER` | MySQL username | `root` |
| `MYSQL_PASSWORD` | MySQL password | `password` |
| `MYSQL_DB` | MySQL database name | `lumina_db` |
| `MONGO_URI` | MongoDB connection | `mongodb://localhost:27017` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET` | S3 bucket name | `lumina-photos` |
| `DYNAMODB_TABLE` | DynamoDB table | `lumina` |
| `SECRET_KEY` | Flask secret key | `random-string` |

---

## Screenshots

*Add screenshots of your app here*

---

## Authors

- Your Name - Cloud607

---

## License

This project is for educational purposes (Cloud607 Final Project).
