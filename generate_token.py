#!/usr/bin/env python3
"""
Simple script to generate token and save both credentials and token as encoded text
"""
import base64
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Read the original credentials file
with open('credentials.json', 'r') as f:
    credentials_data = f.read()

# Encode credentials
credentials_encoded = base64.b64encode(credentials_data.encode('utf-8')).decode('utf-8')

# Save encoded credentials
with open('credentials_encoded.txt', 'w') as f:
    f.write(credentials_encoded)

print("✅ Credentials saved as credentials_encoded.txt")

# Generate token
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Convert token to JSON
token_json = creds.to_json()

# Encode token
token_encoded = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')

# Save encoded token
with open('token_encoded.txt', 'w') as f:
    f.write(token_encoded)

print("✅ Token saved as token_encoded.txt")
print(f"Scopes: {creds.scopes}")

# Verify gmail.send is included
if 'https://www.googleapis.com/auth/gmail.send' in creds.scopes:
    print("✅ gmail.send scope is included!")
else:
    print("❌ ERROR: gmail.send scope is NOT included!")

print("\n📦 Files generated:")
print("  - credentials_encoded.txt (your OAuth credentials)")
print("  - token_encoded.txt (your access token)")
