import os
import ssl
import imaplib
import email
import time
import sqlite3
from datetime import datetime
from email.header import decode_header
from pathlib import Path
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# Disable SSL certificate verification (equivalent to NODE_TLS_REJECT_UNAUTHORIZED = '0')
ssl._create_default_https_context = ssl._create_unverified_context

def init_database():
    """Initialize SQLite database to track processed emails"""
    db_path = Path(__file__).parent / "email_tracker.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table to track last processed email
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS last_processed_email (
            id INTEGER PRIMARY KEY,
            message_id TEXT UNIQUE,
            subject TEXT,
            from_email TEXT,
            timestamp TEXT,
            has_attachment BOOLEAN,
            attachment_filename TEXT,
            processed_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {db_path}")

def get_last_processed_email():
    """Get the last processed email from database"""
    db_path = Path(__file__).parent / "email_tracker.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM last_processed_email ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'message_id': result[1],
            'subject': result[2],
            'from_email': result[3],
            'timestamp': result[4],
            'has_attachment': result[5],
            'attachment_filename': result[6],
            'processed_at': result[7]
        }
    return None

def save_processed_email(message_id, subject, from_email, timestamp, has_attachment=False, attachment_filename=None):
    """Save processed email information to database"""
    db_path = Path(__file__).parent / "email_tracker.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    processed_at = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO last_processed_email 
        (message_id, subject, from_email, timestamp, has_attachment, attachment_filename, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (message_id, subject, from_email, timestamp, has_attachment, attachment_filename, processed_at))
    
    conn.commit()
    conn.close()
    print(f"💾 Saved email info to database: {subject}")

def download_attachment_from_message(mail, message_num):
    """Download attachment from a specific message"""
    try:
        # Fetch the message
        status, msg_data = mail.fetch(message_num, '(RFC822)')
        
        if status != 'OK':
            return False, None
        
        # Parse the email message
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Check for attachments
        if email_message.is_multipart():
            for part in email_message.walk():
                # Check if this part is an attachment
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename:
                    # Decode filename if it's encoded
                    if decode_header(filename)[0][1] is not None:
                        filename = decode_header(filename)[0][0].decode(decode_header(filename)[0][1])
                    
                    # Get attachment data
                    attachment_data = part.get_payload(decode=True)
                    
                    # Create attachments folder if it doesn't exist
                    attachments_dir = Path(__file__).parent / "attachments"
                    attachments_dir.mkdir(exist_ok=True)
                    
                    # Generate timestamp for filename
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
                    
                    # Create filename with timestamp
                    timestamped_filename = f"attachment-{timestamp}-{filename}"
                    
                    # Save the attachment in attachments folder
                    save_path = attachments_dir / timestamped_filename
                    
                    with open(save_path, 'wb') as f:
                        f.write(attachment_data)
                    
                    print(f"✅ New attachment saved to {save_path}")
                    return True, filename
        
        return False, None
        
    except Exception as error:
        print(f"❌ Error processing message: {str(error)}")
        return False, None

def get_email_info(mail, message_num):
    """Extract email information (ID, subject, from, timestamp)"""
    try:
        # Fetch the message
        status, msg_data = mail.fetch(message_num, '(RFC822)')
        
        if status != 'OK':
            return None
        
        # Parse the email message
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Extract email information
        message_id = email_message.get('Message-ID', '')
        subject = email_message.get('Subject', '')
        from_email = email_message.get('From', '')
        date_str = email_message.get('Date', '')
        
        # Decode subject if needed
        if subject:
            decoded_subject = decode_header(subject)
            if decoded_subject[0][1] is not None:
                subject = decoded_subject[0][0].decode(decoded_subject[0][1])
        
        return {
            'message_id': message_id,
            'subject': subject,
            'from_email': from_email,
            'timestamp': date_str
        }
        
    except Exception as error:
        print(f"❌ Error extracting email info: {str(error)}")
        return None

def monitor_emails_continuously():
    """Monitor emails continuously and download new attachments"""
    print("🚀 Starting continuous email monitoring...")
    print("📧 Will check for new emails every 30 seconds")
    print("Press Ctrl+C to stop")
    
    # Initialize database
    init_database()
    
    while True:
        try:
            # Email configuration
            email_user = os.getenv('EMAIL_USER')
            email_pass = os.getenv('EMAIL_PASS')
            
            if not email_user or not email_pass:
                print("❌ Error: EMAIL_USER and EMAIL_PASS must be set in .env file")
                return
            
            # Connect to Gmail IMAP server
            mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            mail.login(email_user, email_pass)
            mail.select('INBOX')
            
            # Get last processed email from database
            last_email = get_last_processed_email()
            
            # Search for all messages
            status, messages = mail.search(None, 'ALL')
            
            if status == 'OK' and messages[0]:
                message_numbers = messages[0].split()
                new_emails_found = 0
                
                # Process messages from newest to oldest
                for num in reversed(message_numbers):
                    # Get email info
                    email_info = get_email_info(mail, num)
                    
                    if not email_info:
                        continue
                    
                    # Check if this email is newer than the last processed one
                    if last_email and email_info['message_id'] == last_email['message_id']:
                        print(f"⏰ Reached last processed email: {email_info['subject']}")
                        break
                    
                    # This is a new email
                    print(f"📬 New email found: {email_info['subject']}")
                    print(f"   From: {email_info['from_email']}")
                    print(f"   Date: {email_info['timestamp']}")
                    
                    # Try to download attachment
                    has_attachment, attachment_filename = download_attachment_from_message(mail, num)
                    
                    # Save email info to database
                    save_processed_email(
                        email_info['message_id'],
                        email_info['subject'],
                        email_info['from_email'],
                        email_info['timestamp'],
                        has_attachment,
                        attachment_filename
                    )
                    
                    new_emails_found += 1
                    
                    # Only process the most recent new email to avoid spam
                    if new_emails_found >= 1:
                        break
                
                if new_emails_found == 0:
                    print("⏰ No new emails found")
                else:
                    print(f"✅ Processed {new_emails_found} new email(s)")
            
            else:
                print("⏰ No messages found in inbox")
            
            # Close connection
            mail.close()
            mail.logout()
            
            # Wait 30 seconds before checking again
            print("⏳ Waiting 30 seconds before next check...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping email monitoring...")
            break
        except Exception as error:
            print(f"❌ Error during monitoring: {str(error)}")
            print("⏳ Retrying in 30 seconds...")
            time.sleep(30)

def download_latest_attachment():
    """Download the latest attachment from Gmail inbox (one-time run)"""
    try:
        # Email configuration
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        
        if not email_user or not email_pass:
            print("❌ Error: EMAIL_USER and EMAIL_PASS must be set in .env file")
            return
        
        # Connect to Gmail IMAP server
        print("📧 Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        
        # Login
        mail.login(email_user, email_pass)
        print("✅ Successfully logged in")
        
        # Select inbox
        mail.select('INBOX')
        
        # Search for all messages (equivalent to ['ALL'] in JavaScript)
        print("🔍 Searching for messages...")
        status, messages = mail.search(None, 'ALL')
        
        if status != 'OK' or not messages[0]:
            print("No messages found.")
            return
        
        # Get message numbers
        message_numbers = messages[0].split()
        
        if not message_numbers:
            print("No messages found.")
            return
        
        # Sort messages by date (newest first)
        # We'll process them in reverse order to get the latest first
        message_numbers.reverse()
        
        found = False
        
        for num in message_numbers:
            success, filename = download_attachment_from_message(mail, num)
            if success:
                found = True
                break
        
        if not found:
            print("No attachments found in any messages.")
        
        # Close connection
        mail.close()
        mail.logout()
        print("📤 Disconnected from Gmail")
        
    except Exception as error:
        print(f"❌ Error: {str(error)}")

if __name__ == "__main__":
    # Uncomment the line below to run continuously
    monitor_emails_continuously()
    
    # Comment out the line below if you want continuous monitoring
    # download_latest_attachment()
