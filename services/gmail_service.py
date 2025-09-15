import os
import base64
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


from logger import logger


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
VERSION = "v1"
GMAIL_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), ".." , "gmail_credentials.json")
GMAIL_TOKEN_PATH = os.path.join(os.path.dirname(__file__), ".." , "gmail_tokens.json")
BATCH_SIZE = 100 # max batch size supported by Gmail API is 500

class GmailService:
    def __init__(self):
        self.client = self._get_client()
        self.labels = self._get_labels()

    def _get_client(self):
        credentials = None
        if os.path.exists(GMAIL_TOKEN_PATH):
            credentials = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_PATH, SCOPES
                )
                credentials = flow.run_local_server(port=0)

            with open(GMAIL_TOKEN_PATH, "w") as token:
                token.write(credentials.to_json())

        try:
            return build("gmail", VERSION, credentials=credentials)
        except HttpError as e:
            logger.error("Not able to create Gmail client: %s", e)
            return None

    def _get_labels(self):
        if not self.client:
            logger.error("Gmail client not initialized")
            return []
        try:
            results = self.client.users().labels().list(userId="me").execute()
            return results.get("labels", [])
        except HttpError as e:
            logger.error("Not able to fetch labels: %s", e)
            return []

    def get_emails_batch(self, max_results=None, days=7, only_unread=False):
        """
        Fetch emails in batches.
        Yields lists of email data, with each list containing up to batch_size emails.
        """
        if not self.client:
            logger.error("Gmail client not initialized")
            return
        emails_processed = 0
        try:
            query = ""
            # Calculate the date range
            if days is not None:
                date_limit = datetime.now() - timedelta(days=days)
                query += f" after:{date_limit.strftime('%Y/%m/%d')}"

            if only_unread:
                query += " is:unread"

            page_token = None

            while True:
                # Get message list for current batch
                messages = (
                    self.client.users()
                    .messages()
                    .list(userId="me", q=query, pageToken=page_token, maxResults=BATCH_SIZE)
                    .execute()
                )

                if "messages" not in messages:
                    logger.info("No more messages found. for query: {query}")
                    break

                # Process messages in current batch
                batch_emails = []
                for message in messages["messages"]:
                    if max_results and emails_processed >= max_results:
                        break
                    email = self._get_email_data(message["id"])
                    if email:
                        batch_emails.append(email)
                        emails_processed += 1

                if max_results and emails_processed >= max_results:
                    if batch_emails:
                        yield batch_emails
                    break

                if batch_emails:
                    yield batch_emails

                # Check if there are more messages to fetch
                page_token = messages.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as e:
            logger.error(f"Error fetching emails: {e}")
            return

    def _get_email_data(self, message_id):
        """Fetch and parse a single email message."""
        try:
            message = (
                self.client.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            headers = message["payload"]["headers"]
            header_data = {
                header["name"].lower(): header["value"] for header in headers
            }

            # Get email body
            body = self._get_email_body(message["payload"])

            # Parse received date
            received_date = parsedate_to_datetime(header_data.get("date", ""))

            return {
                "message_id": message_id,
                "sender": header_data.get("from", ""),
                "recipient": header_data.get("to", ""),
                "subject": header_data.get("subject", ""),
                "body": body,
                "labels": message.get("labelIds", []),
                "received_date": received_date,
                "is_read": "UNREAD" not in message.get("labelIds", []),
            }

        except HttpError as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None

    def _get_email_body(self, payload):
        """Extract email body from the message payload."""
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if "data" in part["body"]:
                        return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )

        return ""

    def mark_as_read(self, message_id, mark_read=True):
        """Mark an email as read or unread."""
        try:
            if mark_read:
                body = {"removeLabelIds": ["UNREAD"]}
            else:
                body = {"addLabelIds": ["UNREAD"]}
            self.client.users().messages().modify(
                userId="me", id=message_id, body=body
            ).execute()
            return True
        except HttpError as e:
            logger.error(
                f"Error marking message {message_id} as {'read' if mark_read else 'unread'}: {e}"
            )
            return False

    def move_message(self, message_id, label_name):
        """Move a message to a different label."""
        try:
            # First, find or create the label
            label_id = self._get_or_create_label(label_name)
            if not label_id:
                return False

            # Modify the message labels
            self.client.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
            ).execute()
            return True
        except HttpError as e:
            logger.error(
                f"Error moving message {message_id} to label {label_name}: {e}"
            )
            return False

    def _get_or_create_label(self, label_name):
        """Get a label ID by name or create it if it doesn't exist."""
        try:
            # Check if label exists
            for label in self.labels:
                if label["name"].lower() == label_name.lower():
                    return label["id"]

            # Create new label
            new_label = (
                self.client.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": label_name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )

            # Update labels cache
            self.labels = self.labels + [new_label]
            return new_label["id"]

        except HttpError as e:
            logger.error(f"Error getting/creating label {label_name}: {e}")
            return None
