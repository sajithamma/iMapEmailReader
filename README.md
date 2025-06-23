# PDF Email Attachment Monitor

A Node.js application that continuously monitors a Gmail inbox for new emails with PDF attachments and automatically downloads them to a local `attachments` folder.

## Features

- **Continuous Monitoring**: Automatically checks for new emails at configurable intervals
- **PDF-Only Processing**: Only downloads PDF file attachments, ignores other file types
- **Local Database Tracking**: Uses SQLite to track the last processed email to avoid duplicates
- **Smart Synchronization**: Only processes new emails since the last check
- **Organized Storage**: Saves all PDFs to an `attachments` folder with timestamps
- **Graceful Shutdown**: Handles Ctrl+C and process termination properly

## Setup

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the project root:
   ```
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASS=your-app-password
   ```
   
   **Note**: For Gmail, you'll need to use an App Password instead of your regular password. Enable 2FA and generate an App Password in your Google Account settings.

3. **Database**: The application automatically creates a `email_tracker.db` SQLite database to track processed emails.

4. **Attachments Folder**: The application automatically creates an `attachments` folder to store downloaded PDFs.

## Usage

### Start Monitoring
```bash
# Start with default 30-second interval
npm start

# Start with fast checking (10-second intervals)
npm run start:fast

# Start with slow checking (5-minute intervals)  
npm run start:slow

# Start with custom interval (e.g., 60 seconds)
node imap-sync.js --interval=60
```

### Reset to Latest Email
If you want to reset the tracking to the most recent email in your inbox (useful for initial setup or if you want to skip old emails):
```bash
npm run reset
```

## How It Works

1. **Initialization**: Creates SQLite database and `attachments` folder
2. **Connection**: Connects to Gmail via IMAP
3. **Search**: Searches for emails since the last processed date
4. **PDF Filtering**: Only processes emails with PDF attachments
5. **Download**: Downloads PDFs to the `attachments` folder with timestamps
6. **Database Update**: Updates tracking info after each successful download
7. **Continuous Loop**: Repeats the process at the specified interval

## File Structure

```
project/
├── imap-sync.js          # Main synchronized monitor (PDF-only)
├── attachments/          # Folder for downloaded PDFs
│   ├── attachment-2024-01-15T10-30-45-123Z-document1.pdf
│   └── attachment-2024-01-15T11-15-22-456Z-report.pdf
├── email_tracker.db      # SQLite database (auto-created)
├── .env                  # Environment variables
└── package.json
```

## Database Schema

The `email_tracker` table stores:
- `last_message_id`: Gmail message ID of the last processed email
- `last_message_uid`: IMAP UID of the last processed email
- `last_processed_date`: Date of the last processed email
- `created_at`: When the record was created
- `updated_at`: When the record was last updated

## Logging

The application provides detailed console output:
- 📁 Directory creation
- 📧 Processing messages
- ✅ Successful PDF downloads
- 📊 Summary of processed messages
- ❌ Error messages
- 🚀 Startup information
- 🛑 Shutdown messages

## Error Handling

- Network connection issues
- Authentication failures
- File system errors
- Database errors
- Graceful shutdown on Ctrl+C

## Security Notes

- Uses App Passwords for Gmail (more secure than regular passwords)
- Stores credentials in environment variables
- Database file should be kept secure
- Downloaded PDFs are saved locally in the `attachments` folder

## Troubleshooting

1. **Authentication Error**: Make sure you're using an App Password, not your regular Gmail password
2. **No PDFs Found**: Check that emails actually have PDF attachments
3. **Permission Errors**: Ensure the script has write permissions in the directory
4. **Database Errors**: Delete `email_tracker.db` to reset tracking (will reprocess all emails)
5. **Folder Issues**: The script automatically creates the `attachments` folder if it doesn't exist

## Production Deployment

For production use, consider:
- Running as a system service (systemd, PM2, etc.)
- Setting up log rotation
- Monitoring disk space for PDF attachments
- Implementing email notifications for errors
- Using environment-specific configuration
- Regular cleanup of old PDF files if needed 