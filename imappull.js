process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

require('dotenv').config();
const imaps = require('imap-simple');
const fs = require('fs');
const path = require('path');

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

async function downloadLatestAttachment() {
    try {
        const connection = await imaps.connect(config);
        await connection.openBox('INBOX');

        const searchCriteria = ['ALL']; // ← search all messages, not just UNSEEN
        const fetchOptions = {
            bodies: ['HEADER', ''],
            struct: true,
            markSeen: false
        };

        const messages = await connection.search(searchCriteria, fetchOptions);

        if (messages.length === 0) {
            console.log('No messages found.');
            return;
        }

        // Sort messages by internalDate descending
        const sortedMessages = messages.sort(
            (a, b) => b.attributes.date - a.attributes.date
        );

        let found = false;

        for (const msg of sortedMessages) {
            const parts = imaps.getParts(msg.attributes.struct);
            const attachmentPart = parts.find(part =>
                part.disposition && part.disposition.type.toUpperCase() === 'ATTACHMENT'
            );

            if (attachmentPart) {
                const partData = await connection.getPartData(msg, attachmentPart);
                const filename = attachmentPart.disposition.params.filename || 'attachment.bin';
                const savePath = path.join(__dirname, 'latest-attachment-' + filename);

                fs.writeFileSync(savePath, partData);
                console.log(`✅ Latest attachment saved to ${savePath}`);
                found = true;
                break;
            }
        }

        if (!found) {
            console.log('No attachments found in any messages.');
        }

        connection.end();
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

downloadLatestAttachment();
