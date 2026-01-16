#!/usr/bin/env python3
"""
Script to remove duplicate files from Google Drive folder.
Keeps the most recent version (by modified time) and deletes older duplicates.
One-time operation for cleaning up duplicate PDFs.
"""

import os
from datetime import datetime
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration - Move the default inside main() to avoid the global issue
DEFAULT_FOLDER_ID = '1ptiTaB8AWH77gngkLG0LBsF_bn_jh85m' # Example folder ID
DEFAULT_TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

class DriveDuplicateCleaner:
    def __init__(self, token_file: str = DEFAULT_TOKEN_FILE):
        self.drive_service = None
        self.credentials = None
        self.token_file = token_file
    
    def authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    print("Error: credentials.json not found.")
                    print("Please download credentials from Google Cloud Console")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        self.drive_service = build('drive', 'v3', credentials=creds)
        return True
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """List all files in a Google Drive folder"""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = []
            page_token = None
            
            while True:
                response = self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size)',
                    pageToken=page_token,
                    pageSize=1000
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                
                if page_token is None:
                    break
            
            return results
        
        except HttpError as error:
            print(f"Error listing files: {error}")
            return []
    
    def find_duplicates(self, files: List[Dict]) -> Dict[str, List[Dict]]:
        """Group files by name to find duplicates"""
        duplicates = {}
        
        for file in files:
            name = file['name']
            if name not in duplicates:
                duplicates[name] = []
            duplicates[name].append(file)
        
        # Filter to only names with multiple files
        duplicates = {name: files_list for name, files_list in duplicates.items() if len(files_list) > 1}
        return duplicates
    
    def delete_file(self, file_id: str, file_name: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            self.drive_service.files().delete(fileId=file_id).execute()
            print(f"✓ Deleted: {file_name} (ID: {file_id})")
            return True
        except HttpError as error:
            print(f"✗ Failed to delete {file_name}: {error}")
            return False
    
    def cleanup_duplicates(self, folder_id: str, dry_run: bool = True):
        """
        Remove duplicate files, keeping the most recent version
        Args:
            folder_id: Google Drive folder ID
            dry_run: If True, only show what would be deleted without actually deleting
        """
        print(f"Scanning folder {folder_id} for duplicates...")
        
        # Get all files
        files = self.list_files_in_folder(folder_id)
        print(f"Found {len(files)} files in the folder")
        
        # Find duplicates
        duplicates = self.find_duplicates(files)
        
        if not duplicates:
            print("No duplicate files found!")
            return
        
        print(f"\nFound {len(duplicates)} files with duplicates:")
        
        total_to_delete = 0
        for name, files_list in duplicates.items():
            print(f"\n'{name}': {len(files_list)} copies")
            
            # Sort by modified time (newest first)
            files_list.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
            
            # Keep the first one (most recent), mark others for deletion
            keep = files_list[0]
            to_delete = files_list[1:]
            
            print(f"  Keeping: {keep['id']} (Modified: {keep.get('modifiedTime', 'N/A')})")
            
            for file in to_delete:
                total_to_delete += 1
                if dry_run:
                    print(f"  [DRY RUN] Would delete: {file['id']} (Modified: {file.get('modifiedTime', 'N/A')})")
                else:
                    print(f"  Deleting: {file['id']} (Modified: {file.get('modifiedTime', 'N/A')})")
                    self.delete_file(file['id'], name)
        
        print(f"\n{'='*60}")
        print(f"SUMMARY:")
        print(f"  Total files scanned: {len(files)}")
        print(f"  Files with duplicates: {len(duplicates)}")
        print(f"  Files to delete: {total_to_delete}")
        
        if dry_run:
            print(f"\nDRY RUN MODE - No files were actually deleted.")
            print(f"Run with --delete to actually remove duplicates.")
        else:
            print(f"\nSuccessfully removed {total_to_delete} duplicate files.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove duplicate files from Google Drive folder')
    parser.add_argument('--folder-id', type=str, default=DEFAULT_FOLDER_ID,
                       help=f'Google Drive folder ID (default: {DEFAULT_FOLDER_ID})')
    parser.add_argument('--delete', action='store_true',
                       help='Actually delete files (default: dry run)')
    parser.add_argument('--token', type=str, default=DEFAULT_TOKEN_FILE,
                       help=f'Path to token file (default: {DEFAULT_TOKEN_FILE})')
    
    args = parser.parse_args()
    
    print("="*60)
    print("GOOGLE DRIVE DUPLICATE CLEANER")
    print("="*60)
    
    cleaner = DriveDuplicateCleaner(token_file=args.token)
    
    if not cleaner.authenticate():
        print("Authentication failed. Exiting.")
        return
    
    print("Authentication successful!")
    print(f"Target folder ID: {args.folder_id}")
    
    if not args.delete:
        print("\nRUNNING IN DRY RUN MODE")
        print("No files will be deleted. Use --delete flag to actually remove duplicates.")
    
    # Ask for confirmation if deleting
    if args.delete:
        print("\n" + "!"*60)
        print("WARNING: This will PERMANENTLY delete files from Google Drive!")
        print("Make sure you have backups if needed.")
        print("!"*60)
        
        confirm = input("\nType 'YES' to confirm deletion: ")
        if confirm != 'YES':
            print("Operation cancelled.")
            return
    
    cleaner.cleanup_duplicates(args.folder_id, dry_run=not args.delete)
    
    print("\n" + "="*60)
    print("Operation completed!")
    print("="*60)

if __name__ == '__main__':
    main()