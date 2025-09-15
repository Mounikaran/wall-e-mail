import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "emails.db")


class EmailDatabase:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                message_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                labels TEXT,
                received_date DATETIME NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        """
        )
        self.connection.commit()

    def add_emails_batch(self, emails):
        """Add multiple emails in a single transaction."""
        self.cursor.executemany(
            """
            INSERT OR REPLACE INTO emails 
            (message_id, sender, recipient, subject, body, labels, received_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            [
                (
                    email["message_id"],
                    email["sender"],
                    email["recipient"],
                    email["subject"],
                    email["body"],
                    email["labels"],
                    email["received_date"],
                )
                for email in emails
            ],
        )
        self.connection.commit()

    def add_email(self, **email_data):
        """Add a single email to the database."""
        self.add_emails_batch([email_data])

    def mark_as_read(self, message_id, is_read=True):
        self.cursor.execute(
            """
            UPDATE emails
            SET is_read = ?
            WHERE message_id = ?
        """,
            (is_read, message_id),
        )
        self.connection.commit()

    def update_labels(self, message_id, labels):
        self.cursor.execute(
            """
            UPDATE emails
            SET labels = ?
            WHERE message_id = ?
        """,
            (labels, message_id),
        )
        self.connection.commit()

    def mark_as_processed(self, message_id):
        """Mark a single email as processed."""
        self.mark_as_processed_batch([message_id])

    def mark_as_processed_batch(self, message_ids):
        """Mark multiple emails as processed in a single transaction."""
        self.cursor.executemany(
            """
            UPDATE emails
            SET processed = 1
            WHERE message_id = ?
        """,
            [(message_id,) for message_id in message_ids],
        )
        self.connection.commit()

    def get_emails(self, days=None):
        """Get all emails from the database, optionally filtered by days."""
        query = "SELECT * FROM emails"
        params = []
        if days is not None:
            query += " WHERE received_date >= datetime('now', ?)"
            params.append(f'-{days} days')
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_processed_emails(self, message_ids=None):
        """Get list of all processed email IDs."""
        query = "SELECT message_id FROM emails WHERE processed = 1"
        if message_ids:
            placeholders = ",".join("?" for _ in message_ids)
            query += f" AND message_id IN ({placeholders})"
            params = message_ids
        else:
            params = []
        self.cursor.execute(query, params)
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
