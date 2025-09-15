import os
import pytest
from datetime import datetime, timedelta
from database.emails import EmailDatabase

@pytest.fixture
def test_db_path(tmpdir):
    """Create a temporary database path."""
    return str(tmpdir.join("test.db"))

@pytest.fixture
def email_db(test_db_path):
    """Create a test database instance."""
    db = EmailDatabase(test_db_path)
    yield db
    db.close()
    try:
        os.remove(test_db_path)
    except OSError:
        pass

@pytest.fixture
def sample_email():
    """Create a sample email data."""
    return {
        'message_id': 'test123',
        'sender': 'sender@test.com',
        'recipient': 'recipient@test.com',
        'subject': 'Test Subject',
        'body': 'Test Body',
        'labels': 'INBOX',
        'received_date': datetime.now()
    }

def test_create_database(email_db, test_db_path):
    """Test database creation and table setup."""
    assert os.path.exists(test_db_path)

def test_add_single_email(email_db, sample_email):
    """Test adding a single email to the database."""
    email_db.add_email(**sample_email)
    emails = email_db.get_emails()
    assert len(emails) == 1
    assert emails[0][0] == sample_email['message_id']

def test_add_emails_batch(email_db):
    """Test adding multiple emails in a batch."""
    emails = []
    for i in range(3):
        emails.append({
            'message_id': f'batch{i}',
            'sender': 'sender@test.com',
            'recipient': 'recipient@test.com',
            'subject': f'Batch Subject {i}',
            'body': f'Batch Body {i}',
            'labels': 'INBOX',
            'received_date': datetime.now()
        })
    
    email_db.add_emails_batch(emails)
    stored_emails = email_db.get_emails()
    assert len(stored_emails) == 3

def test_mark_as_processed(email_db, sample_email):
    """Test marking an email as processed."""
    email_db.add_email(**sample_email)
    email_db.mark_as_processed(sample_email['message_id'])
    processed = email_db.get_processed_emails()
    assert sample_email['message_id'] in processed

def test_mark_as_processed_batch(email_db):
    """Test marking multiple emails as processed in a batch."""
    emails = []
    message_ids = []
    for i in range(3):
        message_id = f'batch{i}'
        message_ids.append(message_id)
        emails.append({
            'message_id': message_id,
            'sender': 'sender@test.com',
            'recipient': 'recipient@test.com',
            'subject': f'Batch Subject {i}',
            'body': f'Batch Body {i}',
            'labels': 'INBOX',
            'received_date': datetime.now()
        })
    
    email_db.add_emails_batch(emails)
    email_db.mark_as_processed_batch(message_ids)
    processed = email_db.get_processed_emails()
    assert all(mid in processed for mid in message_ids)

def test_get_emails_with_date_filter(email_db, sample_email):
    """Test retrieving emails with date filtering."""
    # Add old email
    old_email = sample_email.copy()
    old_email['message_id'] = 'old123'
    old_email['received_date'] = datetime.now() - timedelta(days=10)
    email_db.add_email(**old_email)
    
    # Add recent email
    recent_email = sample_email.copy()
    recent_email['message_id'] = 'recent123'
    recent_email['received_date'] = datetime.now()
    email_db.add_email(**recent_email)
    
    # Get emails from last 5 days
    recent_emails = email_db.get_emails(days=5)
    assert len(recent_emails) == 1
    assert recent_emails[0][0] == 'recent123'