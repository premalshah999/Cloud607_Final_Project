# EC2 Deployment Commands - Quick Reference

## Problem: Git Pull Failed Due to Local Changes
When you see:
```
error: Your local changes to the following files would be overwritten by merge:
        lumina/storage_dynamodb.py
Please commit your changes or stash them before you merge.
```

## Solution: Discard Broken Local Changes and Pull Clean Version

Run these commands on EC2:

```bash
# 1. Navigate to project directory
cd ~/Cloud607_Final_Project

# 2. Discard local changes to the corrupted file
git checkout -- lumina/storage_dynamodb.py

# 3. Pull the latest changes from GitHub
git pull origin main

# 4. Activate virtual environment (if not already active)
source venv/bin/activate

# 5. Export environment variables
export $(grep -v '^#' .env | xargs)

# 6. Kill any existing gunicorn processes
pkill gunicorn

# 7. Start gunicorn
gunicorn -w 2 -b 0.0.0.0:8080 app:app
```

## Verify It's Working

1. Open browser to: http://3.134.81.141:8080
2. Login with your credentials
3. Try uploading a photo
4. Should work without errors!

## If You Need to Run in Background

```bash
# Option 1: Use nohup
nohup gunicorn -w 2 -b 0.0.0.0:8080 app:app > gunicorn.log 2>&1 &

# Option 2: Use screen (recommended)
screen -S lumina
gunicorn -w 2 -b 0.0.0.0:8080 app:app
# Press Ctrl+A then D to detach
# To reattach: screen -r lumina

# Option 3: Setup as systemd service (permanent solution)
# See AWS_DEPLOYMENT.md for full instructions
```

## Common Issues

### Issue: IndentationError at line 321
**Cause**: Manual editing introduced incorrect indentation  
**Fix**: Use `git checkout -- lumina/storage_dynamodb.py` to restore clean version

### Issue: "Missing the key PK in the item"
**Cause**: Old version of storage_dynamodb.py without PK/SK schema  
**Fix**: Pull latest changes with `git pull origin main`

### Issue: Gunicorn won't start - "Address already in use"
**Cause**: Previous gunicorn process still running  
**Fix**: `pkill gunicorn` then restart

### Issue: 500 errors after deployment
**Cause**: Environment variables not exported  
**Fix**: `export $(grep -v '^#' .env | xargs)`

## File Versions
- **Latest commit**: 57cb9e0 - "Fix DynamoDB PK/SK schema for all photo operations"
- **Key file**: lumina/storage_dynamodb.py (573 lines)
- **Changes**: Added PK/SK schema to add_photo, delete_photo, get_photo, increment_like

## Testing Checklist
- [ ] App loads at http://3.134.81.141:8080
- [ ] Can login successfully
- [ ] Can upload photos (no "Missing the key PK" error)
- [ ] Photos appear in gallery
- [ ] Can like photos
- [ ] Can comment on photos
- [ ] Can send messages

## Environment Variables (.env)
Make sure these are set:
```
STORAGE_BACKEND=dynamodb
AWS_ACCESS_KEY_ID=AKIA4355BWYEOQ5TNWXZ
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_REGION=us-east-2
S3_BUCKET=lumina-photos-cloud650
DYNAMODB_PHOTOS_TABLE=lumina_photos
DYNAMODB_COMMENTS_TABLE=lumina_comments
DYNAMODB_MESSAGES_TABLE=lumina_messages
DB_HOST=lumina-db.cd0acqgy60av.us-east-2.rds.amazonaws.com
DB_USER=admin
DB_PASSWORD=<your-password>
DB_NAME=lumina
SECRET_KEY=<your-secret-key>
```
