# Email Attachment Monitor

A Node.js application that continuously monitors a Gmail inbox for new emails with attachments and automatically downloads them to a local directory.

## Features

- **Continuous Monitoring**: Automatically checks for new emails at configurable intervals
- **Local Database Tracking**: Uses SQLite to track the last processed email to avoid duplicates
- **Smart Synchronization**: Only processes new emails since the last check
- **Multiple Attachments**: Handles emails with multiple attachments
- **Timestamped Files**: Saves attachments with timestamps to avoid filename conflicts
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

## Usage

### Start Monitoring
```bash
# Start with default 30-second interval
node imap-sync.js

# Start with custom interval (e.g., 60 seconds)
node imap-sync.js --interval=60

# Start with 5-minute interval
node imap-sync.js --interval=300
```

### Reset to Latest Email
If you want to reset the tracking to the most recent email in your inbox (useful for initial setup or if you want to skip old emails):
```bash
node imap-sync.js --reset
```

## How It Works

1. **Initialization**: Creates a SQLite database to track the last processed email
2. **Connection**: Connects to Gmail via IMAP
3. **Search**: Searches for emails since the last processed date
4. **Processing**: For each new email with attachments:
   - Downloads all attachments
   - Saves them with timestamps
   - Updates the database with the latest message info
5. **Continuous Loop**: Repeats the process at the specified interval

## File Structure

```
project/
├── imap-sync.js          # Main synchronized monitor
├── imappull.js           # Original one-time downloader
├── email_tracker.db      # SQLite database (auto-created)
├── attachment-*.pdf      # Downloaded attachments
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
- 📧 Processing messages
- ✅ Successful attachment downloads
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
- Downloaded attachments are saved locally

## Troubleshooting

1. **Authentication Error**: Make sure you're using an App Password, not your regular Gmail password
2. **No Attachments Found**: Check that emails actually have attachments
3. **Permission Errors**: Ensure the script has write permissions in the directory
4. **Database Errors**: Delete `email_tracker.db` to reset tracking (will reprocess all emails)

## Production Deployment

For production use, consider:
- Running as a system service (systemd, PM2, etc.)
- Setting up log rotation
- Monitoring disk space for attachments
- Implementing email notifications for errors
- Using environment-specific configuration 