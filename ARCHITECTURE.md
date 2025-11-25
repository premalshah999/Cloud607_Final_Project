# Lumina Architecture Diagrams

This document contains all system architecture diagrams for the Lumina Photo Gallery application.

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Client["🌐 Client Layer"]
        Browser["Web Browser<br/>(app.html)"]
    end

    subgraph Server["🖥️ Application Layer"]
        Flask["Flask App<br/>(Gunicorn)"]
        Routes["API Routes<br/>(lumina/routes.py)"]
        Storage["Storage Layer<br/>(storage.py)"]
    end

    subgraph Data["💾 Data Layer"]
        MySQL[(MySQL<br/>Users & Friends)]
        DynamoDB[(DynamoDB<br/>Photos & Messages)]
        S3[(S3 Bucket<br/>Image Files)]
    end

    Browser -->|HTTP/REST| Flask
    Flask --> Routes
    Routes --> Storage
    Storage -->|User Data| MySQL
    Storage -->|Metadata| DynamoDB
    Storage -->|Images| S3
```

---

## 2. AWS Cloud Architecture

```mermaid
flowchart TB
    subgraph Internet["☁️ Internet"]
        User["👤 User"]
    end

    subgraph AWS["AWS Cloud"]
        subgraph VPC["VPC"]
            subgraph Public["Public Subnet"]
                EC2["EC2 Instance<br/>t2.micro<br/>Flask + Gunicorn"]
            end
            subgraph Private["Private Subnet"]
                RDS["RDS MySQL<br/>db.t3.micro<br/>User Accounts"]
            end
        end
        
        DynamoDB["DynamoDB<br/>Photos, Comments,<br/>Likes, Messages"]
        S3["S3 Bucket<br/>Full Images<br/>Thumbnails"]
    end

    User -->|Port 8080| EC2
    EC2 -->|Port 3306| RDS
    EC2 -->|HTTPS| DynamoDB
    EC2 -->|HTTPS| S3
```

---

## 3. Data Flow - Photo Upload

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Flask API
    participant S as Storage
    participant DB as DynamoDB
    participant S3 as S3 Bucket

    U->>F: Select photo + caption
    F->>A: POST /api/photos<br/>(multipart/form-data)
    A->>S: save_photo(user_id, file, caption)
    S->>S: Resize image (thumb + full)
    S->>S3: Upload full image
    S3-->>S: full_key
    S->>S3: Upload thumbnail
    S3-->>S: thumb_key
    S->>DB: Store metadata<br/>(photo_id, user_id, caption, keys)
    DB-->>S: Success
    S-->>A: photo_id
    A-->>F: 201 {id: photo_id}
    F-->>U: Show success toast
```

---

## 4. Data Flow - User Authentication

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Flask API
    participant M as MySQL

    U->>F: Enter username/password
    F->>A: POST /api/auth/login
    A->>M: SELECT * FROM users<br/>WHERE username = ?
    M-->>A: User record
    A->>A: Verify password hash
    A->>A: Create session
    A-->>F: 200 {user: {id, username}}
    F->>F: Store user in state
    F-->>U: Show gallery
```

---

## 5. Data Flow - Social Features

```mermaid
sequenceDiagram
    participant U1 as User A
    participant F as Frontend
    participant A as Flask API
    participant M as MySQL
    participant DB as DynamoDB

    Note over U1,DB: Friend Request Flow
    U1->>F: Click "Add Friend"
    F->>A: POST /api/friends/add {friend: "UserB"}
    A->>M: INSERT INTO friendships<br/>(user_id, friend_id, 'pending')
    M-->>A: Success
    A-->>F: 200 OK

    Note over U1,DB: Chat Message Flow
    U1->>F: Send message
    F->>A: POST /api/messages/UserB {text: "Hello!"}
    A->>DB: Put item in DynamoDB<br/>PK: CHAT#A#B, SK: MSG#timestamp
    DB-->>A: Success
    A-->>F: 201 Created
```

---

## 6. DynamoDB Data Model

```mermaid
erDiagram
    PHOTO {
        string PK "PHOTO#{photo_id}"
        string SK "META"
        string user_id
        string caption
        string timestamp
        list likes
        string s3_key
        string thumb_key
    }
    
    COMMENT {
        string PK "PHOTO#{photo_id}"
        string SK "COMMENT#{timestamp}#{user_id}"
        string user_id
        string username
        string text
        string timestamp
    }
    
    MESSAGE {
        string PK "CHAT#{user1}#{user2}"
        string SK "MSG#{timestamp}"
        string sender_id
        string text
        string timestamp
    }
    
    USER_INDEX {
        string PK "USER#{user_id}"
        string SK "PHOTO#{photo_id}"
        string photo_id
        string timestamp
    }

    PHOTO ||--o{ COMMENT : has
    PHOTO ||--o{ USER_INDEX : indexed_by
```

---

## 7. MySQL Data Model

```mermaid
erDiagram
    USERS {
        int id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        timestamp created_at
    }
    
    FRIENDSHIPS {
        int id PK
        int user_id FK
        int friend_id FK
        enum status "pending|accepted|rejected"
        timestamp created_at
    }
    
    USERS ||--o{ FRIENDSHIPS : "sends"
    USERS ||--o{ FRIENDSHIPS : "receives"
```

---

## 8. Application Module Structure

```mermaid
flowchart TB
    subgraph Entry["Entry Point"]
        app["app.py"]
    end

    subgraph Lumina["lumina/ Package"]
        init["__init__.py<br/>create_app()"]
        config["config.py<br/>Configuration"]
        routes["routes.py<br/>API Endpoints"]
        storage["storage.py<br/>MongoDB Backend"]
        dynamo["storage_dynamodb.py<br/>AWS Backend"]
    end

    subgraph Frontend["Frontend"]
        html["app.html<br/>Single Page App"]
    end

    app --> init
    init --> config
    init --> routes
    init --> storage
    init --> dynamo
    routes --> storage
    routes --> dynamo
    html -->|REST API| routes
```

---

## 9. API Endpoint Map

```mermaid
flowchart LR
    subgraph Auth["/api/auth"]
        signup["POST /signup"]
        login["POST /login"]
        logout["POST /logout"]
        me["GET /me"]
    end

    subgraph Photos["/api/photos"]
        list["GET /"]
        upload["POST /"]
        delete["DELETE /:id"]
        like["POST /:id/like"]
        image["GET /:id/image/:size"]
        comments["GET|POST /:id/comments"]
    end

    subgraph Social["/api"]
        friends["GET /friends"]
        addFriend["POST /friends/add"]
        acceptFriend["POST /friends/accept"]
        messages["GET|POST /messages/:friend"]
    end

    Client((Client)) --> Auth
    Client --> Photos
    Client --> Social
```

---

## 10. Docker Local Deployment

```mermaid
flowchart TB
    subgraph Docker["Docker Compose"]
        subgraph Web["web container"]
            Flask["Flask App<br/>Port 8080"]
        end
        
        subgraph DB["mysql container"]
            MySQL["MySQL 8.0<br/>Port 3307"]
        end
        
        subgraph Mongo["mongo container"]
            MongoDB["MongoDB<br/>Port 27018"]
        end
    end

    Host["Host Machine<br/>localhost"] -->|:8080| Flask
    Flask -->|:3306| MySQL
    Flask -->|:27017| MongoDB
```

---

## 11. Request Lifecycle

```mermaid
flowchart TB
    A[HTTP Request] --> B{Authenticated?}
    B -->|No| C[Return 401]
    B -->|Yes| D{Route Type}
    
    D -->|Auth| E[Auth Blueprint]
    D -->|Photos| F[API Blueprint]
    D -->|Social| G[API Blueprint]
    
    E --> H[MySQL Query]
    F --> I{Storage Backend}
    G --> I
    
    I -->|mongodb| J[MongoDB + GridFS]
    I -->|dynamodb| K[DynamoDB + S3]
    
    H --> L[Response]
    J --> L
    K --> L
    
    L --> M[JSON Response]
```

---

## 12. Image Processing Pipeline

```mermaid
flowchart LR
    A[Original Image] --> B[Pillow Load]
    B --> C{Size Check}
    C -->|Width > 1200| D[Resize Full<br/>max 1200px]
    C -->|Width ≤ 1200| E[Keep Original]
    D --> F[Create Thumbnail<br/>300x300]
    E --> F
    F --> G[Convert to JPEG]
    G --> H[Upload to S3]
    H --> I[Store Keys in DynamoDB]
```

---

## How to View These Diagrams

### Option 1: GitHub
GitHub automatically renders Mermaid diagrams in markdown files.

### Option 2: VS Code
Install the "Markdown Preview Mermaid Support" extension.

### Option 3: Online
Copy the mermaid code to [mermaid.live](https://mermaid.live)

### Option 4: Export to PNG
Use [mermaid-cli](https://github.com/mermaid-js/mermaid-cli):
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i ARCHITECTURE.md -o architecture.png
```
