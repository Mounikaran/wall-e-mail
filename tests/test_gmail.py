import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from services.gmail_service import GmailService


@pytest.fixture
def mock_gmail_client():
    """Create a mock Gmail client."""
    client = MagicMock()

    # Mock messages.list
    messages_response = {"messages": [{"id": "msg1"}, {"id": "msg2"}, {"id": "msg3"}]}
    client.users().messages().list().execute.return_value = messages_response

    # Mock messages.get
    message_data = {
        "id": "msg1",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@test.com"},
                {"name": "To", "value": "recipient@test.com"},
                {"name": "Subject", "value": "Test Subject"},
                {
                    "name": "Date",
                    "value": datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"),
                },
            ],
            "body": {"data": "VGVzdCBCb2R5"},  # Base64 encoded "Test Body"
        },
    }
    client.users().messages().get().execute.return_value = message_data

    return client


@pytest.fixture
def gmail_service(mock_gmail_client):
    """Create a Gmail service with mocked client."""
    with patch("services.gmail_service.build", return_value=mock_gmail_client):
        service = GmailService()
        service.client = mock_gmail_client
        return service


def test_get_emails_batch(gmail_service):
    """Test fetching emails in batches."""
    emails = list(gmail_service.get_emails_batch(max_results=3))
    assert len(emails) == 1  # One batch of 3 emails
    assert len(emails[0]) == 3  # Three emails in the batch


def test_get_emails_with_date_filter(gmail_service):
    """Test fetching emails with date filter."""
    emails = list(gmail_service.get_emails_batch(max_results=3, days=7))
    assert len(emails) == 1
    # Verify that the date query was included
    calls = gmail_service.client.users().messages().list.call_args_list
    assert any("after:" in str(call) for call in calls)


def test_get_emails_unread_only(gmail_service):
    """Test fetching only unread emails."""
    emails = list(gmail_service.get_emails_batch(max_results=3, only_unread=True))
    assert len(emails) == 1
    # Verify that the unread filter was included
    calls = gmail_service.client.users().messages().list.call_args_list
    assert any("is:unread" in str(call) for call in calls)


def test_mark_as_read(gmail_service):
    """Test marking an email as read."""
    assert gmail_service.mark_as_read("msg1", True) is True
    # Verify the API call
    gmail_service.client.users().messages().modify.assert_called_with(
        userId="me", id="msg1", body={"removeLabelIds": ["UNREAD"]}
    )


def test_mark_as_unread(gmail_service):
    """Test marking an email as unread."""
    assert gmail_service.mark_as_read("msg1", False) is True
    # Verify the API call
    gmail_service.client.users().messages().modify.assert_called_with(
        userId="me", id="msg1", body={"addLabelIds": ["UNREAD"]}
    )


def test_move_message(gmail_service):
    """Test moving a message to a different label."""
    # Mock the label creation/lookup
    gmail_service.labels = [{"id": "Label_123", "name": "TestLabel"}]

    assert gmail_service.move_message("msg1", "TestLabel") is True
    # Verify the API call
    gmail_service.client.users().messages().modify.assert_called_with(
        userId="me",
        id="msg1",
        body={"addLabelIds": ["Label_123"], "removeLabelIds": ["INBOX"]},
    )


def test_create_new_label(gmail_service):
    """Test creating a new label."""
    gmail_service.labels = []
    new_label = {"id": "Label_New", "name": "NewLabel"}
    gmail_service.client.users().labels().create().execute.return_value = new_label

    assert gmail_service.move_message("msg1", "NewLabel") is True
    # Verify label creation
    gmail_service.client.users().labels().create.assert_called_with(
        userId="me",
        body={
            "name": "NewLabel",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    )
