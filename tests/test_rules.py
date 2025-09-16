import os
import json
import pytest
from datetime import datetime, timedelta
from rules import RuleProcessor, RuleCondition, Rule

@pytest.fixture
def sample_email(request):
    """Create a sample email for testing."""
    return {
        'message_id': 'test123',
        'sender': 'sender@test.com',
        'recipient': 'recipient@test.com',
        'subject': 'Test Subject',
        'body': 'Test Body',
        'labels': ['INBOX'],
        'received_date': datetime.now(),
        'is_read': False
    }

@pytest.fixture
def test_rules_file(tmpdir):
    """Create a temporary rules file for testing."""
    rules_data = {
        "rules": [
            {
                "name": "Test Rule",
                "conditions": [
                    {
                        "field": "subject",
                        "predicate": "contains",
                        "value": "test"
                    }
                ],
                "predicate": "all",
                "actions": [
                    {
                        "type": "mark_as_read"
                    }
                ]
            }
        ]
    }
    rules_file = tmpdir.join("test_rules.json")
    rules_file.write(json.dumps(rules_data))
    return str(rules_file)

class MockGmailService:
    def mark_as_read(self, message_id, mark_read=True):
        return True
    
    def move_message(self, message_id, label_name):
        return True

class MockEmailDB:
    def mark_as_read(self, message_id, is_read=True):
        return True
    
    def update_labels(self, message_id, labels):
        return True

def test_rule_condition_string_contains(sample_email):
    """Test string contains condition."""
    condition = RuleCondition('subject', 'contains', 'test')
    assert condition.evaluate(sample_email) is True
    
    sample_email['subject'] = 'No match here'
    assert condition.evaluate(sample_email) is False

def test_rule_condition_string_equals(sample_email):
    """Test string equals condition."""
    condition = RuleCondition('from', 'equals', 'sender@test.com')
    assert condition.evaluate(sample_email) is True
    
    sample_email['sender'] = 'other@test.com'
    assert condition.evaluate(sample_email) is False

def test_rule_condition_date_greater_than(sample_email):
    """Test date greater than condition."""
    condition = RuleCondition('received_date', 'greater_than', '7 days')
    sample_email['received_date'] = datetime.now() - timedelta(days=10)
    assert condition.evaluate(sample_email) is True
    
    sample_email['received_date'] = datetime.now() - timedelta(days=5)
    assert condition.evaluate(sample_email) is False

def test_rule_all_predicate(sample_email):
    """Test rule with 'all' predicate."""
    conditions = [
        RuleCondition('subject', 'contains', 'test'),
        RuleCondition('from', 'contains', '@test.com')
    ]
    rule = Rule('Test Rule', conditions, 'all', [{'type': 'mark_as_read'}])
    assert rule.evaluate(sample_email) is True
    
    sample_email['subject'] = 'No match'
    assert rule.evaluate(sample_email) is False

def test_rule_any_predicate(sample_email):
    """Test rule with 'any' predicate."""
    conditions = [
        RuleCondition('subject', 'contains', 'no match'),
        RuleCondition('from', 'contains', '@test.com')
    ]
    rule = Rule('Test Rule', conditions, 'any', [{'type': 'mark_as_read'}])
    assert rule.evaluate(sample_email) is True

def test_rule_actions(sample_email):
    """Test rule actions execution."""
    rule = Rule(
        'Test Rule',
        [RuleCondition('subject', 'contains', 'test')],
        'all',
        [
            {'type': 'mark_as_read'},
            {'type': 'move_message', 'label': 'TestLabel'}
        ]
    )
    gmail_service = MockGmailService()
    email_db = MockEmailDB()
    
    assert rule.apply_actions(sample_email, gmail_service, email_db) is True

def test_rule_processor_initialization(test_rules_file):
    """Test RuleProcessor initialization with valid rules file."""
    processor = RuleProcessor(test_rules_file)
    assert processor is not None
    assert len(processor.rules) > 0

def test_process_email_matches_rule(test_rules_file, sample_email):
    """Test processing an email that matches a rule."""
    processor = RuleProcessor(test_rules_file)
    gmail_service = MockGmailService()
    email_db = MockEmailDB()
    
    sample_email['subject'] = 'Test Subject'  # Should match the test rule
    success = processor.process_email(sample_email, gmail_service, email_db)
    assert success is True