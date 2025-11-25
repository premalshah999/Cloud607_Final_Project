# Lumina - Architecture & Design Documentation

This document contains comprehensive architecture diagrams for the Lumina photo-sharing application deployed on AWS.

## Table of Contents
1. [AWS Infrastructure Architecture](#1-aws-infrastructure-architecture)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Backend Architecture](#3-backend-architecture)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Database Schema Design](#5-database-schema-design)
6. [Authentication Flow](#6-authentication-flow)
7. [Photo Upload Flow](#7-photo-upload-flow)
8. [Messaging System Flow](#8-messaging-system-flow)
9. [Friend Request Flow](#9-friend-request-flow)
10. [Data Flow Architecture](#10-data-flow-architecture)
11. [API Request Flow](#11-api-request-flow)
12. [Deployment Architecture](#12-deployment-architecture)

---

## 1. AWS Infrastructure Architecture

```mermaid
graph TB
    subgraph "AWS Cloud - us-east-2"
        subgraph "VPC"
            subgraph "Public Subnet"
                EC2[EC2 Instance<br/>t2.micro<br/>Amazon Linux 2023<br/>IP: 3.134.81.141:8080]
            end
            
            subgraph "Private Subnet"
                RDS[(RDS MySQL 8.0<br/>db.t3.micro<br/>lumina-db)]
            end
        end
        
        S3[S3 Bucket<br/>lumina-photos-cloud650<br/>Public Read Access]
        
        DDB1[(DynamoDB<br/>lumina_photos<br/>PK + SK)]
        DDB2[(DynamoDB<br/>lumina_comments<br/>PK + SK)]
        DDB3[(DynamoDB<br/>lumina_messages<br/>PK + SK)]
        
        IAM[IAM Role<br/>EC2 Instance Profile<br/>S3 + DynamoDB Access]
    end
    
    Internet((Internet<br/>Users))
    
    Internet -->|HTTP :8080| EC2
    EC2 -->|SQL Queries| RDS
    EC2 -->|Upload/Download| S3
    EC2 -->|Read/Write| DDB1
    EC2 -->|Read/Write| DDB2
    EC2 -->|Read/Write| DDB3
    IAM -.->|Credentials| EC2
    
    style EC2 fill:#ff9900,stroke:#232f3e,stroke-width:3px
    style RDS fill:#527fff,stroke:#232f3e,stroke-width:2px
    style S3 fill:#569a31,stroke:#232f3e,stroke-width:2px
    style DDB1 fill:#3b48cc,stroke:#232f3e,stroke-width:2px
    style DDB2 fill:#3b48cc,stroke:#232f3e,stroke-width:2px
    style DDB3 fill:#3b48cc,stroke:#232f3e,stroke-width:2px
```

**Key Components:**
- **EC2**: Application server running Gunicorn with Flask
- **RDS MySQL**: User accounts and friendship relationships
- **S3**: Photo storage (full resolution + thumbnails)
- **DynamoDB**: Photos metadata, comments, and messages
- **IAM**: Secure access control for AWS services

---

## 2. System Architecture Overview

```mermaid
graph LR
    subgraph "Client Layer"
        Browser[Web Browser<br/>HTML/CSS/JavaScript]
    end
    
    subgraph "Application Layer - EC2"
        Gunicorn[Gunicorn WSGI<br/>2 Workers<br/>Port 8080]
        Flask[Flask 3.x<br/>Application Factory]
        Routes[Routes Module<br/>API Endpoints]
        Storage[Storage Module<br/>Backend Abstraction]
    end
    
    subgraph "Data Layer"
        MySQL[(MySQL<br/>Users + Friends)]
        DynamoDB[(DynamoDB<br/>Photos + Comments<br/>+ Messages)]
        S3[(S3<br/>Image Files)]
    end
    
    Browser <-->|HTTP/JSON| Gunicorn
    Gunicorn <--> Flask
    Flask <--> Routes
    Routes <--> Storage
    Storage <-->|PyMySQL| MySQL
    Storage <-->|boto3| DynamoDB
    Storage <-->|boto3| S3
    
    style Browser fill:#61dafb,stroke:#333,stroke-width:2px
    style Gunicorn fill:#499848,stroke:#333,stroke-width:2px
    style Flask fill:#000,stroke:#fff,stroke-width:2px,color:#fff
    style MySQL fill:#00758f,stroke:#333,stroke-width:2px
    style DynamoDB fill:#3b48cc,stroke:#333,stroke-width:2px
    style S3 fill:#569a31,stroke:#333,stroke-width:2px
```

**Architecture Pattern**: Three-tier architecture with clear separation of concerns
- **Presentation**: HTML/CSS/JavaScript frontend
- **Application**: Flask backend with modular design
- **Data**: Hybrid storage (SQL + NoSQL + Object Storage)

---

## 3. Backend Architecture

```mermaid
graph TB
    subgraph "Flask Application"
        App[app.py<br/>Application Factory]
        Config[config.py<br/>Environment Config]
        
        subgraph "lumina Package"
            Init[__init__.py<br/>Blueprint Registration]
            Routes[routes.py<br/>API Endpoints]
            StorageInterface[Storage Interface<br/>Abstract Methods]
            
            subgraph "Storage Implementations"
                DynamoDBStorage[storage_dynamodb.py<br/>AWS Backend]
            end
        end
    end
    
    subgraph "External Services"
        MySQL[(MySQL<br/>Relational Data)]
        DynamoDB[(DynamoDB<br/>Document Data)]
        S3[(S3<br/>Binary Data)]
    end
    
    App --> Config
    App --> Init
    Init --> Routes
    Routes -->|Authentication| StorageInterface
    Routes -->|Business Logic| StorageInterface
    StorageInterface --> DynamoDBStorage
    
    DynamoDBStorage -->|User Management| MySQL
    DynamoDBStorage -->|Photo Metadata| DynamoDB
    DynamoDBStorage -->|Comments| DynamoDB
    DynamoDBStorage -->|Messages| DynamoDB
    DynamoDBStorage -->|Image Upload| S3
    
    style App fill:#000,stroke:#fff,stroke-width:2px,color:#fff
    style Routes fill:#ff6b6b,stroke:#333,stroke-width:2px
    style DynamoDBStorage fill:#4ecdc4,stroke:#333,stroke-width:2px
```

**Backend Modules:**
- **app.py**: Entry point, Flask app factory
- **routes.py**: 15+ RESTful API endpoints
- **storage_dynamodb.py**: 30+ methods for data operations
- **config.py**: Environment-based configuration

---

## 4. Frontend Architecture

```mermaid
graph TB
    subgraph "Static HTML Pages"
        Index[index.html<br/>Landing Page]
        AppHTML[app.html<br/>Main Application]
    end
    
    subgraph "JavaScript Modules - Embedded in app.html"
        API[API Layer<br/>fetch() wrapper]
        Auth[Authentication<br/>Session Management]
        PhotoUI[Photo Management<br/>Upload/Display/Delete]
        CommentUI[Comments UI<br/>Add/View Comments]
        MessageUI[Messaging UI<br/>Real-time Chat]
        FriendsUI[Friends UI<br/>Requests/List]
        Gallery[Gallery Views<br/>Home/Profile/All]
    end
    
    subgraph "UI Components"
        Modal[Modal Dialogs<br/>Upload/Comments/Messages]
        Tabs[Tab Navigation<br/>Home/Profile/All/Friends/Chat]
        Cards[Photo Cards<br/>Grid Layout]
    end
    
    Index -->|Login/Signup| API
    AppHTML --> Auth
    AppHTML --> Gallery
    AppHTML --> Tabs
    
    Auth --> API
    PhotoUI --> API
    CommentUI --> API
    MessageUI --> API
    FriendsUI --> API
    
    Gallery --> PhotoUI
    Tabs --> Gallery
    Tabs --> FriendsUI
    Tabs --> MessageUI
    
    PhotoUI --> Modal
    CommentUI --> Modal
    MessageUI --> Modal
    Gallery --> Cards
    
    API -->|HTTP Requests| Backend[Flask Backend API]
    
    style AppHTML fill:#61dafb,stroke:#333,stroke-width:2px
    style API fill:#ff6b6b,stroke:#333,stroke-width:2px
    style Auth fill:#ffd93d,stroke:#333,stroke-width:2px
    style Backend fill:#6bcf7f,stroke:#333,stroke-width:2px
```

**Frontend Features:**
- Single Page Application (SPA) architecture
- RESTful API integration
- Session-based authentication
- Responsive grid layout
- Modal-based interactions

---

## 5. Database Schema Design

```mermaid
erDiagram
    USERS ||--o{ FRIEND_REQUESTS : creates
    USERS ||--o{ FRIEND_REQUESTS : receives
    USERS ||--o{ PHOTOS : uploads
    PHOTOS ||--o{ COMMENTS : has
    USERS ||--o{ MESSAGES : sends
    USERS ||--o{ MESSAGES : receives
    
    USERS {
        int id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        timestamp created_at
    }
    
    FRIEND_REQUESTS {
        int id PK
        int requester_id FK
        int receiver_id FK
        enum status
        timestamp created_at
    }
    
    PHOTOS {
        string PK "PHOTO#id"
        string SK "META or USER#id"
        string photo_id
        int user_id
        string username
        string caption
        string full_key
        string thumbnail_key
        int likes
        timestamp created_at
    }
    
    COMMENTS {
        string PK "PHOTO#photo_id"
        string SK "COMMENT#timestamp#id"
        string comment_id
        string photo_id
        int user_id
        string username
        string text
        timestamp created_at
    }
    
    MESSAGES {
        string PK "CONV#user1#user2"
        string SK "MSG#timestamp#id"
        string message_id
        string conversation_id
        int from_user_id
        string from_username
        int to_user_id
        string text
        timestamp timestamp
    }
```

**Storage Strategy:**
- **MySQL (RDS)**: Users and friend relationships (ACID compliance)
- **DynamoDB**: Photos, comments, messages (scalability and performance)
- **S3**: Image files (cost-effective object storage)

**DynamoDB Key Design:**
- **Photos**: `PK=PHOTO#{id}, SK=META` (main item) + `PK=USER#{user_id}, SK=PHOTO#{id}` (index)
- **Comments**: `PK=PHOTO#{photo_id}, SK=COMMENT#{timestamp}#{id}`
- **Messages**: `PK=CONV#{user1}#{user2}, SK=MSG#{timestamp}#{id}`

---

## 6. Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant MySQL
    
    rect rgb(200, 220, 240)
        Note over User,MySQL: User Signup Flow
        User->>Browser: Enter username + password
        Browser->>Flask: POST /api/auth/signup
        Flask->>Flask: Hash password (werkzeug)
        Flask->>Flask: Auto-generate email
        Flask->>MySQL: INSERT INTO users
        MySQL-->>Flask: User created (id)
        Flask->>Flask: Create session
        Flask-->>Browser: 201 Created + Set-Cookie
        Browser-->>User: Redirect to app
    end
    
    rect rgb(220, 240, 200)
        Note over User,MySQL: User Login Flow
        User->>Browser: Enter credentials
        Browser->>Flask: POST /api/auth/login
        Flask->>MySQL: SELECT user by username
        MySQL-->>Flask: User data
        Flask->>Flask: Verify password hash
        Flask->>Flask: Create session
        Flask-->>Browser: 200 OK + Set-Cookie
        Browser-->>User: Redirect to app
    end
    
    rect rgb(240, 220, 200)
        Note over User,MySQL: Authenticated Request
        Browser->>Flask: GET /api/photos (with session cookie)
        Flask->>Flask: @login_required decorator
        Flask->>Flask: Validate session
        Flask->>MySQL: Get user from session
        MySQL-->>Flask: User data
        Flask-->>Browser: 200 OK + photos data
    end
```

**Security Features:**
- Password hashing with werkzeug.security
- Session-based authentication (Flask sessions)
- Decorator-based route protection
- Automatic email generation for compatibility

---

## 7. Photo Upload Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant S3
    participant DynamoDB
    
    User->>Browser: Select photo + caption
    Browser->>Browser: Validate file (type/size)
    Browser->>Flask: POST /api/photos<br/>(multipart/form-data)
    
    Flask->>Flask: Generate UUID for photo
    Flask->>Flask: Validate file extension
    
    par Upload to S3
        Flask->>Flask: Resize image (Pillow)
        Flask->>S3: Upload full image<br/>(photo_id_full.jpg)
        S3-->>Flask: Upload successful
        Flask->>Flask: Create thumbnail (200x200)
        Flask->>S3: Upload thumbnail<br/>(photo_id_thumb.jpg)
        S3-->>Flask: Upload successful
    end
    
    Flask->>DynamoDB: Put main item<br/>PK=PHOTO#id, SK=META
    DynamoDB-->>Flask: Item created
    
    Flask->>DynamoDB: Put user index<br/>PK=USER#id, SK=PHOTO#id
    DynamoDB-->>Flask: Index created
    
    Flask-->>Browser: 201 Created + photo metadata
    Browser->>Browser: Update gallery UI
    Browser-->>User: Show new photo
```

**Image Processing:**
- Original image stored as-is
- Thumbnail generated at 200x200px
- JPEG compression for optimization
- Unique S3 keys: `{uuid}_full.jpg` and `{uuid}_thumb.jpg`

---

## 8. Messaging System Flow

```mermaid
sequenceDiagram
    participant User1
    participant Browser1
    participant Flask
    participant DynamoDB
    participant Browser2
    participant User2
    
    User1->>Browser1: Select friend + type message
    Browser1->>Flask: GET /api/users/lookup?username=friend
    Flask-->>Browser1: Friend user_id
    
    Browser1->>Flask: POST /api/messages<br/>{to_user_id, text}
    
    Flask->>Flask: Create conversation_id<br/>CONV#user1#user2 (sorted)
    Flask->>Flask: Generate message_id (UUID)
    Flask->>Flask: Create sort key<br/>MSG#timestamp#id
    
    Flask->>DynamoDB: PutItem<br/>PK=CONV#user1#user2<br/>SK=MSG#timestamp#id
    DynamoDB-->>Flask: Message stored
    
    Flask-->>Browser1: 201 Created
    Browser1-->>User1: Message sent confirmation
    
    rect rgb(230, 230, 250)
        Note over Browser2,User2: Polling for new messages
        Browser2->>Flask: GET /api/messages?user_id=1<br/>(every 3 seconds)
        Flask->>DynamoDB: Query PK=CONV#user1#user2<br/>SK begins_with MSG#
        DynamoDB-->>Flask: Messages list
        Flask-->>Browser2: 200 OK + messages
        Browser2-->>User2: Display new message
    end
```

**Messaging Features:**
- Conversation-based storage (sorted users for consistency)
- Chronological ordering via timestamp in sort key
- Polling-based message retrieval (3-second intervals)
- Efficient queries using composite keys

---

## 9. Friend Request Flow

```mermaid
stateDiagram-v2
    [*] --> NoRelationship: Initial State
    
    NoRelationship --> PendingRequest: User A sends request
    PendingRequest --> Accepted: User B accepts
    PendingRequest --> Declined: User B declines
    PendingRequest --> NoRelationship: User A cancels
    
    Declined --> NoRelationship: Auto-cleanup
    Accepted --> Friends: Mutual friendship
    
    Friends --> NoRelationship: Unfriend action
    
    state PendingRequest {
        [*] --> Visible_To_Receiver
        Visible_To_Receiver --> Notified
    }
    
    state Accepted {
        [*] --> Both_Can_See
        Both_Can_See --> Chat_Enabled
        Chat_Enabled --> View_Photos
    }
    
    note right of NoRelationship
        Users can search for
        each other but no
        special permissions
    end note
    
    note right of Friends
        - See each other's photos in "Home" feed
        - Send direct messages
        - View friend list
    end note
```

**Friend Request Process:**
1. **Send Request**: POST /api/friends/request
2. **View Requests**: GET /api/friends/requests
3. **Accept/Decline**: POST /api/friends/respond
4. **View Friends**: GET /api/friends/list

---

## 10. Data Flow Architecture

```mermaid
flowchart TD
    Start([User Action]) --> Auth{Authenticated?}
    
    Auth -->|No| LoginPage[Redirect to Login]
    Auth -->|Yes| Action{Action Type?}
    
    Action -->|Upload Photo| PhotoFlow[Photo Upload Flow]
    Action -->|View Gallery| GalleryFlow[Gallery Flow]
    Action -->|Send Message| MessageFlow[Message Flow]
    Action -->|Comment| CommentFlow[Comment Flow]
    
    PhotoFlow --> ValidateFile{Valid File?}
    ValidateFile -->|No| Error1[Return 400 Error]
    ValidateFile -->|Yes| ProcessImage[Resize + Create Thumbnail]
    ProcessImage --> UploadS3[Upload to S3]
    UploadS3 --> SaveMetaDDB[Save Metadata to DynamoDB]
    SaveMetaDDB --> Success1[Return 201 + Photo Data]
    
    GalleryFlow --> CheckScope{Scope?}
    CheckScope -->|Home| GetFriends[Get Friend IDs from MySQL]
    CheckScope -->|Profile| GetUserID[Get Current User ID]
    CheckScope -->|All| AllUsers[All Photos]
    GetFriends --> QueryPhotos[Query DynamoDB Photos]
    GetUserID --> QueryPhotos
    AllUsers --> QueryPhotos
    QueryPhotos --> EnrichData[Add Username, Image URLs]
    EnrichData --> Success2[Return 200 + Photos Array]
    
    MessageFlow --> ValidateUser{Friend Exists?}
    ValidateUser -->|No| Error2[Return 404 Error]
    ValidateUser -->|Yes| CreateConv[Create Conversation ID]
    CreateConv --> SaveDDB[Save to DynamoDB Messages]
    SaveDDB --> Success3[Return 201 + Message]
    
    CommentFlow --> PhotoExists{Photo Exists?}
    PhotoExists -->|No| Error3[Return 404 Error]
    PhotoExists -->|Yes| SaveComment[Save to DynamoDB Comments]
    SaveComment --> Success4[Return 201 + Comment]
    
    Success1 --> End([Response to Client])
    Success2 --> End
    Success3 --> End
    Success4 --> End
    Error1 --> End
    Error2 --> End
    Error3 --> End
    LoginPage --> End
    
    style Start fill:#90EE90,stroke:#333,stroke-width:2px
    style End fill:#FFB6C1,stroke:#333,stroke-width:2px
    style Auth fill:#FFD700,stroke:#333,stroke-width:2px
    style Action fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 11. API Request Flow

```mermaid
graph TB
    Request[HTTP Request] --> Gunicorn[Gunicorn Worker]
    Gunicorn --> Flask[Flask App]
    Flask --> Route{Route Exists?}
    
    Route -->|No| NotFound[404 Not Found]
    Route -->|Yes| AuthCheck{@login_required?}
    
    AuthCheck -->|Yes| Session{Valid Session?}
    AuthCheck -->|No| Handler[Route Handler]
    
    Session -->|No| Unauthorized[401 Unauthorized]
    Session -->|Yes| Handler
    
    Handler --> Business[Business Logic]
    Business --> Storage[Storage Layer]
    
    Storage --> DataSource{Data Source?}
    
    DataSource -->|Users/Friends| MySQL[(MySQL Query)]
    DataSource -->|Photos/Comments| DynamoDB[(DynamoDB Query)]
    DataSource -->|Images| S3[(S3 Get/Put)]
    
    MySQL --> Process[Process Results]
    DynamoDB --> Process
    S3 --> Process
    
    Process --> Response{Success?}
    
    Response -->|Yes| Success[200/201 + JSON]
    Response -->|No| Error[400/500 + Error Message]
    
    Success --> Return[HTTP Response]
    Error --> Return
    NotFound --> Return
    Unauthorized --> Return
    
    Return --> Gunicorn
    Gunicorn --> Client[Client Browser]
    
    style Request fill:#61dafb,stroke:#333,stroke-width:2px
    style Flask fill:#000,stroke:#fff,stroke-width:2px,color:#fff
    style MySQL fill:#00758f,stroke:#333,stroke-width:2px
    style DynamoDB fill:#3b48cc,stroke:#333,stroke-width:2px
    style S3 fill:#569a31,stroke:#333,stroke-width:2px
    style Client fill:#90EE90,stroke:#333,stroke-width:2px
```

**API Endpoints (15 total):**

**Authentication:**
- POST /api/auth/signup
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me

**Photos:**
- POST /api/photos
- GET /api/photos (with scope parameter)
- DELETE /api/photos/:id
- GET /api/photos/:id/image/:size
- POST /api/photos/:id/like

**Comments:**
- GET /api/photos/:id/comments
- POST /api/photos/:id/comments

**Friends:**
- POST /api/friends/request
- GET /api/friends/requests
- POST /api/friends/respond

**Messages:**
- GET /api/messages
- POST /api/messages

**Users:**
- GET /api/users/lookup

---

## 12. Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DevMachine[Local MacBook]
        Git[Git Repository<br/>GitHub]
    end
    
    subgraph "AWS Production Environment"
        subgraph "EC2 Instance"
            Python[Python 3.11<br/>Virtual Environment]
            Gunicorn[Gunicorn WSGI<br/>2 Workers<br/>0.0.0.0:8080]
            App[Flask Application]
            Env[.env File<br/>Environment Variables]
        end
        
        RDS[(RDS MySQL<br/>lumina-db)]
        DDB[(DynamoDB Tables<br/>3 tables)]
        S3[(S3 Bucket<br/>lumina-photos-cloud650)]
        
        SecurityGroup[Security Group<br/>Port 8080 Open]
    end
    
    Internet((Internet))
    
    DevMachine -->|git push| Git
    Git -->|git pull| Python
    
    Python --> App
    Env --> App
    Gunicorn --> App
    
    App --> RDS
    App --> DDB
    App --> S3
    
    Internet -->|HTTP :8080| SecurityGroup
    SecurityGroup --> Gunicorn
    
    style DevMachine fill:#61dafb,stroke:#333,stroke-width:2px
    style EC2 Instance fill:#ff9900,stroke:#232f3e,stroke-width:3px
    style App fill:#000,stroke:#fff,stroke-width:2px,color:#fff
    style Gunicorn fill:#499848,stroke:#333,stroke-width:2px
```

**Deployment Steps:**
1. **Local Development**: Code changes on MacBook
2. **Version Control**: Push to GitHub repository
3. **EC2 Deployment**: Pull latest code on EC2 instance
4. **Environment Setup**: Configure .env with AWS credentials
5. **Process Management**: Restart Gunicorn workers
6. **Service Access**: Application available at http://3.134.81.141:8080

**Environment Variables:**
```bash
STORAGE_BACKEND=dynamodb
AWS_REGION=us-east-2
S3_BUCKET=lumina-photos-cloud650
DYNAMODB_PHOTOS_TABLE=lumina_photos
DYNAMODB_COMMENTS_TABLE=lumina_comments
DYNAMODB_MESSAGES_TABLE=lumina_messages
DB_HOST=lumina-db.cd0acqgy60av.us-east-2.rds.amazonaws.com
DB_USER=admin
DB_PASSWORD=***
DB_NAME=lumina
```

---

## Technology Stack Summary

### Frontend
- **HTML5/CSS3**: Responsive layout
- **Vanilla JavaScript**: DOM manipulation, fetch API
- **No Frameworks**: Lightweight, fast loading

### Backend
- **Flask 3.x**: Web framework
- **Gunicorn 23.0.0**: WSGI server (2 workers)
- **Python 3.11**: Runtime environment
- **PyMySQL**: MySQL database driver
- **boto3 1.28+**: AWS SDK for Python
- **Pillow**: Image processing library

### Data Storage
- **MySQL 8.0**: User accounts, friendships (RDS db.t3.micro)
- **DynamoDB**: Photos, comments, messages (on-demand billing)
- **S3**: Image file storage (standard storage class)

### Infrastructure
- **EC2**: t2.micro Amazon Linux 2023
- **VPC**: Default VPC with public/private subnets
- **Security Groups**: Port 8080 (HTTP) open to 0.0.0.0/0
- **IAM**: Instance profile with S3 and DynamoDB permissions

### Development Tools
- **Git/GitHub**: Version control
- **SSH**: Remote server access
- **vim/nano**: Server-side editing

---

## Cost Optimization

**AWS Free Tier Usage:**
- ✅ EC2 t2.micro (750 hours/month)
- ✅ RDS db.t3.micro (750 hours/month, 20GB storage)
- ✅ S3 (5GB storage, 20,000 GET, 2,000 PUT)
- ✅ DynamoDB (25GB storage, 25 WCU, 25 RCU)

**Estimated Monthly Cost**: $0 (within Free Tier limits)

---

## Performance Characteristics

- **Photo Upload**: ~2-3 seconds (includes resizing + S3 upload)
- **Gallery Load**: ~500ms-1s (optimized single scan query)
- **Message Delivery**: ~3 seconds (polling interval)
- **Authentication**: ~200ms (MySQL query + session creation)
- **API Response Time**: Avg 300ms (excluding S3 image delivery)

---

## Scalability Considerations

**Current Bottlenecks:**
1. Single EC2 instance (no horizontal scaling)
2. Polling-based messaging (not real-time)
3. Gunicorn with only 2 workers

**Future Improvements:**
1. **Add Load Balancer**: Distribute traffic across multiple EC2 instances
2. **Implement WebSockets**: Real-time messaging with Socket.IO
3. **Add CloudFront CDN**: Cache S3 images globally
4. **Use ElastiCache**: Session store and query caching
5. **Implement Auto Scaling**: Dynamic EC2 scaling based on load
6. **Add API Gateway**: Rate limiting and request throttling

---

**Last Updated**: November 25, 2025  
**Version**: 1.0  
**Author**: Lumina Development Team
