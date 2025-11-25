# DynamoDB PK/SK Schema Fix

## Problem
The code was creating DynamoDB items without the required `PK` (Partition Key) and `SK` (Sort Key) fields, causing `ValidationException: Missing the key PK in the item` errors.

## Solution
Updated all DynamoDB operations in `lumina/storage_dynamodb.py` to use the PK/SK schema.

## Apply Fix on EC2

### Option 1: Git Pull (Easiest)
```bash
cd ~/Cloud607_Final_Project
git pull origin main
sudo systemctl restart gunicorn  # or kill and restart gunicorn manually
```

### Option 2: Manual File Copy
Copy the updated `lumina/storage_dynamodb.py` from your local machine to EC2:

```bash
# On your local machine:
scp -i ~/path/to/your-key.pem \
  /Users/premalparagbhaishah/Desktop/Cloud607_Final_Project/lumina/storage_dynamodb.py \
  ec2-user@3.134.81.141:~/Cloud607_Final_Project/lumina/
```

Then on EC2:
```bash
cd ~/Cloud607_Final_Project
# Activate venv if not already
source venv/bin/activate

# Restart gunicorn
pkill gunicorn
gunicorn -w 2 -b 0.0.0.0:8080 app:app
```

## Changes Made

### 1. `add_photo` - Added PK/SK fields to DynamoDB items
**Lines 280-304**: Now creates items with:
- Main photo record: `PK='PHOTO#{photo_id}'`, `SK='META'`
- User index record: `PK='USER#{user_id}'`, `SK='PHOTO#{photo_id}'`

### 2. `delete_photo` - Updated to use PK/SK keys
**Lines 306-336**: Changed from `Key={'id': photo_id}` to:
```python
Key={'PK': f'PHOTO#{photo_id}', 'SK': 'META'}
```

### 3. `get_photo` - Updated to use PK/SK keys
**Lines 338-347**: Changed from `Key={'id': photo_id}` to:
```python
Key={'PK': f'PHOTO#{photo_id}', 'SK': 'META'}
```

### 4. `increment_like` - Updated to use PK/SK keys
**Lines 349-361**: Changed from `Key={'id': photo_id}` to:
```python
Key={'PK': f'PHOTO#{photo_id}', 'SK': 'META'}
```

## Verification
After restarting gunicorn:
1. Navigate to http://3.134.81.141:8080
2. Login
3. Try uploading a photo
4. Should succeed without errors

## What's Next
After photo upload works, we may need to fix:
- `list_photos()` - Currently uses scan, should use Query with PK/SK
- Comment functions - Need to verify PK/SK usage
- Message functions - Need to verify PK/SK usage
