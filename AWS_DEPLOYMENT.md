# Deploy Lumina to AWS (Step-by-Step)

This guide helps you deploy Lumina to AWS using free tier services. No prior AWS experience needed!

**Time needed:** ~30-45 minutes  
**Cost:** $0 (AWS Free Tier)

---

## What You'll Set Up

| Service | What It Does | Free Tier Limit |
|---------|--------------|-----------------|
| **EC2** | Runs your web app | 750 hours/month |
| **RDS** | Stores user accounts | 750 hours/month |
| **DynamoDB** | Stores photos/comments | 25 GB free |
| **S3** | Stores image files | 5 GB free |

---

## Step 1: Create an AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click **Create an AWS Account**
3. Enter your email and create a password
4. Add a credit card (won't be charged if you stay in free tier)
5. Complete phone verification
6. Select the **Free** support plan

---

## Step 2: Create Access Keys

You need these to let your app talk to AWS.

1. Search **IAM** in the AWS search bar → Click it
2. Click **Users** in the left menu → **Create user**
3. Name it `lumina-app` → Click **Next**
4. Select **Attach policies directly**
5. Search and check these boxes:
   - `AmazonDynamoDBFullAccess`
   - `AmazonS3FullAccess`
6. Click **Next** → **Create user**
7. Click on your new user → **Security credentials** tab
8. Click **Create access key** → Select **Application running outside AWS**
9. **SAVE THESE KEYS!** You won't see them again:
   - Access Key ID: `AKIA...`
   - Secret Access Key: `wJalr...`

---

## Step 3: Create S3 Bucket (Image Storage)

1. Search **S3** in the AWS search bar → Click it
2. Click **Create bucket**
3. Settings:
   - Bucket name: `lumina-photos-YOURNAME` (must be unique worldwide)
   - Region: `US East (N. Virginia)` or closest to you
   - **Uncheck** "Block all public access" (we need images to be viewable)
   - Check the acknowledgment box
4. Click **Create bucket**

---

## Step 4: Create DynamoDB Table (Photo Data)

1. Search **DynamoDB** in the AWS search bar → Click it
2. Click **Create table**
3. Settings:
   - Table name: `lumina`
   - Partition key: `PK` (String)
   - Sort key: `SK` (String)
   - Keep "Default settings" selected
4. Click **Create table**
5. Wait ~30 seconds until status shows "Active"

---

## Step 5: Create RDS Database (User Accounts)

⚠️ This takes 10-15 minutes to create. Start it now, then continue with other steps.

1. Search **RDS** in the AWS search bar → Click it
2. Click **Create database**
3. Settings:
   - Choose **Standard create**
   - Engine: **MySQL**
   - Version: **MySQL 8.0.x** (any 8.0 version)
   - Templates: **Free tier** ← Important!
   - DB instance identifier: `lumina-db`
   - Master username: `admin`
   - Master password: Create one and **SAVE IT!**
   - Instance: `db.t3.micro` (should auto-select)
   - Storage: 20 GB
   - **Public access: Yes** (so EC2 can connect)
4. Click **Create database**
5. Wait 10-15 minutes...

**While waiting, get the endpoint:**
1. Click on your database name
2. Find **Endpoint** under "Connectivity & security"
3. Copy it (looks like: `lumina-db.xxxxx.us-east-1.rds.amazonaws.com`)

---

## Step 6: Launch EC2 Server

1. Search **EC2** in the AWS search bar → Click it
2. Click **Launch instance**
3. Settings:
   - Name: `lumina-web`
   - AMI: **Amazon Linux 2023** (should be default)
   - Instance type: `t2.micro` (Free tier eligible)
   - Key pair: Click **Create new key pair**
     - Name: `lumina-key`
     - Keep defaults → **Create**
     - **SAVE the downloaded .pem file!**
   - Network settings: Click **Edit**
     - Check: Allow SSH
     - Check: Allow HTTP
     - Check: Allow HTTPS
     - Add rule: Custom TCP, Port 8080, Source 0.0.0.0/0
4. Click **Launch instance**

**Get your server's address:**
1. Click on your instance ID
2. Copy the **Public IPv4 address** (like `3.85.123.45`)

---

## Step 7: Connect to Your Server

Open Terminal on your Mac:

```bash
# Make your key file secure
chmod 400 ~/Downloads/lumina-key.pem

# Connect to your server (replace YOUR-IP)
ssh -i ~/Downloads/lumina-key.pem ec2-user@YOUR-IP
```

Type `yes` when asked about fingerprint.

---

## Step 8: Install Software on Server

Run these commands one at a time:

```bash
# Update the system
sudo yum update -y

# Install Python
sudo yum install -y python3.11 python3.11-pip git

# Install MySQL client (to set up database)
sudo yum install -y mysql
```

---

## Step 9: Set Up the Database

Connect to your RDS database:

```bash
# Replace YOUR-RDS-ENDPOINT with your endpoint from Step 5
mysql -h YOUR-RDS-ENDPOINT -u admin -p
```

Enter your password when prompted. Then run:

```sql
CREATE DATABASE lumina_db;
USE lumina_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE friendships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    friend_id INT NOT NULL,
    status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (friend_id) REFERENCES users(id)
);

exit;
```

---

## Step 10: Download and Configure the App

```bash
# Download the code
git clone https://github.com/YOUR-USERNAME/Cloud607_Final_Project.git
cd Cloud607_Final_Project

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create the configuration file:

```bash
nano .env
```

Paste this (replace the placeholders):

```
STORAGE_BACKEND=dynamodb
AWS_REGION=us-east-1
S3_BUCKET=lumina-photos-YOURNAME
DYNAMODB_TABLE=lumina
AWS_ACCESS_KEY_ID=YOUR-ACCESS-KEY
AWS_SECRET_ACCESS_KEY=YOUR-SECRET-KEY
MYSQL_HOST=YOUR-RDS-ENDPOINT
MYSQL_USER=admin
MYSQL_PASSWORD=YOUR-RDS-PASSWORD
MYSQL_DB=lumina_db
SECRET_KEY=any-random-text-here
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

---

## Step 11: Start the App

```bash
# Load your settings
source .env

# Start the server
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:8080 app:app
```

---

## Step 12: Visit Your App! 🎉

Open your browser and go to:
```
http://YOUR-EC2-IP:8080
```

You should see Lumina running!

---

## Keep It Running (Optional)

To keep the app running after you close the terminal:

```bash
# Install screen
sudo yum install -y screen

# Start a screen session
screen -S lumina

# Start the app
source venv/bin/activate
source .env
gunicorn -w 2 -b 0.0.0.0:8080 app:app

# Detach: Press Ctrl+A, then D
# Reattach later: screen -r lumina
```

---

## Troubleshooting

**Can't connect to EC2?**
- Check that your .pem file path is correct
- Make sure your instance is "Running" in EC2 console

**Database connection error?**
- Check your RDS endpoint is correct in .env
- Make sure RDS security group allows MySQL (port 3306)

**App not loading?**
- Check EC2 security group allows port 8080
- Try: `curl http://localhost:8080` from the server

**See error logs:**
```bash
# If app crashes, you'll see the error in the terminal
# Or check: journalctl -xe
```

---

## Cleanup (When Done)

To avoid charges after free tier expires:

1. **EC2**: Stop or terminate your instance
2. **RDS**: Delete your database (create final snapshot if wanted)
3. **S3**: Empty and delete your bucket
4. **DynamoDB**: Delete your table

---

## Quick Reference

| What | Value |
|------|-------|
| EC2 IP | `YOUR-EC2-IP` |
| RDS Endpoint | `lumina-db.xxx.rds.amazonaws.com` |
| S3 Bucket | `lumina-photos-yourname` |
| DynamoDB Table | `lumina` |
| App URL | `http://YOUR-EC2-IP:8080` |
