process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

require('dotenv').config();
const imaps = require('imap-simple');
const fs = require('fs');
const path = require('path');
const Database = require('better-sqlite3');

// Database setup
const db = new Database('email_tracker.db');

// Initialize database table
function initializeDatabase() {
    const createTable = `
        CREATE TABLE IF NOT EXISTS email_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_message_id TEXT,
            last_message_uid TEXT,
            last_processed_date TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `;

    db.exec(createTable);

    // Insert initial record if table is empty
    const count = db.prepare('SELECT COUNT(*) as count FROM email_tracker').get();
    if (count.count === 0) {
        db.prepare(`
            INSERT INTO email_tracker (last_message_id, last_message_uid, last_processed_date) 
            VALUES (?, ?, ?)
        `).run('', '', '');
    }
}

// Get last processed email info
function getLastProcessedEmail() {
    return db.prepare('SELECT * FROM email_tracker ORDER BY id DESC LIMIT 1').get();
}

// Update last processed email info
function updateLastProcessedEmail(messageId, messageUid, processedDate) {
    db.prepare(`
        UPDATE email_tracker 
        SET last_message_id = ?, last_message_uid = ?, last_processed_date = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT MAX(id) FROM email_tracker)
    `).run(messageId, messageUid, processedDate);
}

const config = {
    imap: {
        user: process.env.EMAIL_USER,
        password: process.env.EMAIL_PASS,
        host: 'imap.gmail.com',
        port: 993,
        tls: true,
        authTimeout: 3000,
        tlsOptions: { rejectUnauthorized: false }
    }
};

async function checkForNewAttachments() {
    try {
        const connection = await imaps.connect(config);
        await connection.openBox('INBOX');

        const lastProcessed = getLastProcessedEmail();
        let searchCriteria = ['ALL'];

        // If we have a last processed message, search for messages after that date
        if (lastProcessed.last_processed_date) {
            const lastDate = new Date(lastProcessed.last_processed_date);
            searchCriteria = ['SINCE', lastDate];
        }

        const fetchOptions = {
            bodies: ['HEADER', ''],
            struct: true,
            markSeen: false
        };

        const messages = await connection.search(searchCriteria, fetchOptions);

        if (messages.length === 0) {
            console.log('No new messages found.');
            connection.end();
            return;
        }

        // Sort messages by date ascending (oldest first to process in order)
        const sortedMessages = messages.sort(
            (a, b) => a.attributes.date - b.attributes.date
        );

        let processedCount = 0;
        let lastMessageId = lastProcessed.last_message_id;
        let lastMessageUid = lastProcessed.last_message_uid;
        let lastProcessedDate = lastProcessed.last_processed_date;

        for (const msg of sortedMessages) {
            const messageId = msg.attributes['x-gm-msgid'] || msg.attributes.uid?.toString() || '';
            const messageUid = msg.attributes.uid?.toString() || '';
            const messageDate = msg.attributes.date;

            // Skip if we've already processed this message
            if (lastProcessed.last_message_id && messageId === lastProcessed.last_message_id) {
                continue;
            }

            const parts = imaps.getParts(msg.attributes.struct);
            const attachmentParts = parts.filter(part =>
                part.disposition && part.disposition.type.toUpperCase() === 'ATTACHMENT'
            );

            if (attachmentParts.length > 0) {
                console.log(`📧 Processing message: ${messageId} (${messageDate})`);

                for (let i = 0; i < attachmentParts.length; i++) {
                    const attachmentPart = attachmentParts[i];
                    const partData = await connection.getPartData(msg, attachmentPart);
                    const filename = attachmentPart.disposition.params.filename || `attachment-${i}.bin`;
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                    const savePath = path.join(__dirname, `attachment-${timestamp}-${filename}`);

                    fs.writeFileSync(savePath, partData);
                    console.log(`✅ Attachment saved: ${savePath}`);
                }

                processedCount++;
            }

            // Update tracking info for this message
            lastMessageId = messageId;
            lastMessageUid = messageUid;
            lastProcessedDate = messageDate.toISOString();
        }

        if (processedCount > 0) {
            updateLastProcessedEmail(lastMessageId, lastMessageUid, lastProcessedDate);
            console.log(`📊 Processed ${processedCount} messages with attachments`);
        } else {
            console.log('No new messages with attachments found.');
        }

        connection.end();
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

// Function to reset the needle to the latest email
async function resetToLatestEmail() {
    try {
        const connection = await imaps.connect(config);
        await connection.openBox('INBOX');

        const searchCriteria = ['ALL'];
        const fetchOptions = {
            bodies: ['HEADER', ''],
            struct: true,
            markSeen: false
        };

        const messages = await connection.search(searchCriteria, fetchOptions);

        if (messages.length === 0) {
            console.log('No messages found in inbox.');
            connection.end();
            return;
        }

        // Get the most recent message
        const sortedMessages = messages.sort(
            (a, b) => b.attributes.date - a.attributes.date
        );

        const latestMessage = sortedMessages[0];
        const messageId = latestMessage.attributes['x-gm-msgid'] || latestMessage.attributes.uid?.toString() || '';
        const messageUid = latestMessage.attributes.uid?.toString() || '';
        const messageDate = latestMessage.attributes.date.toISOString();

        updateLastProcessedEmail(messageId, messageUid, messageDate);
        console.log(`🔄 Reset needle to latest message: ${messageId} (${messageDate})`);

        connection.end();
    } catch (error) {
        console.error('❌ Error resetting to latest email:', error.message);
    }
}

// Main monitoring function
async function startMonitoring(checkInterval = 30000) { // 30 seconds default
    console.log('🚀 Starting email attachment monitor...');
    console.log(`⏰ Check interval: ${checkInterval / 1000} seconds`);

    // Initial check
    await checkForNewAttachments();

    // Set up periodic checking
    setInterval(async () => {
        await checkForNewAttachments();
    }, checkInterval);
}

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down email monitor...');
    db.close();
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 Shutting down email monitor...');
    db.close();
    process.exit(0);
});

// Initialize and start
initializeDatabase();

// Check command line arguments
const args = process.argv.slice(2);
if (args.includes('--reset')) {
    resetToLatestEmail().then(() => {
        console.log('✅ Reset completed. Exiting.');
        db.close();
        process.exit(0);
    });
} else {
    const interval = args.find(arg => arg.startsWith('--interval='));
    const checkInterval = interval ? parseInt(interval.split('=')[1]) * 1000 : 30000;

    startMonitoring(checkInterval);
}

module.exports = {
    checkForNewAttachments,
    resetToLatestEmail,
    startMonitoring
}; 