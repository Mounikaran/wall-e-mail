import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from services.gmail_service import GmailService
from database.emails import EmailDatabase
from logger import logger


RULE_FILE_PATH = os.path.join(os.path.dirname(__file__), "config.json")

EMAIL_FIELD_MAPPING = {
    "from": "sender",
    "sender": "sender",
    "to": "recipient",
    "recipient": "recipient",
    "subject": "subject",
    "body": "body",
    "received_date": "received_date",
}


class RuleCondition:
    # Map rule fields to email dictionary fields

    def __init__(self, field: str, predicate: str, value: str):
        self.field = field
        self.predicate = predicate
        self.value = value

    def evaluate(self, email: Dict[str, Any]) -> bool:
        # Map the field name to the correct email dictionary key
        email_field = EMAIL_FIELD_MAPPING.get(self.field)
        if not email_field or email_field not in email:
            logger.error(
                f"Field '{self.field}' (mapped to '{email_field}') not found in email"
            )
            return False

        field_value = email[email_field]

        # Handle date type fields
        if self.field == "received_date":
            return self._evaluate_date(field_value)

        # Handle string type fields
        return self._evaluate_string(str(field_value))

    def _evaluate_string(self, field_value: str) -> bool:
        if self.predicate == "contains":
            return self.value.lower() in field_value.lower()
        elif self.predicate == "does_not_contain":
            return self.value.lower() not in field_value.lower()
        elif self.predicate == "equals":
            return self.value.lower() == field_value.lower()
        elif self.predicate == "does_not_equal":
            return self.value.lower() != field_value.lower()
        return False

    def _evaluate_date(self, field_value: datetime) -> bool:
        try:
            # Convert field_value to naive datetime for comparison
            if field_value.tzinfo:
                field_value = field_value.replace(tzinfo=None)

            now = datetime.now()
            if "days" in self.value:
                days = int(self.value.split()[0])
                compare_date = now - timedelta(days=days)
            else:
                return False

            if self.predicate == "less_than":
                return field_value > compare_date
            elif self.predicate == "greater_than":
                return field_value < compare_date

            return False
        except (ValueError, AttributeError) as e:
            logger.error(f"Error evaluating date: {e}")
        
        return False


class Rule:
    def __init__(
        self,
        name: str,
        conditions: List[RuleCondition],
        predicate: str,
        actions: List[Dict[str, str]],
    ):
        self.name = name
        self.conditions = conditions
        self.predicate = predicate  # 'all' or 'any'
        self.actions = actions

    def evaluate(self, email: Dict[str, Any]) -> bool:
        if not self.conditions:
            return False

        results = []
        for condition in self.conditions:
            result = condition.evaluate(email)
            results.append(result)

        final_result = False
        if self.predicate == "all":
            final_result = all(results)
        elif self.predicate == "any":
            final_result = any(results)

        return final_result

    def apply_actions(
        self,
        email: Dict[str, Any],
        gmail_service: GmailService,
        email_db: EmailDatabase,
    ) -> bool:
        try:
            for action in self.actions:
                action_type = action["type"]
                if action_type == "mark_as_read":
                    gmail_service.mark_as_read(email["message_id"], True)
                    email_db.mark_as_read(email["message_id"], True)
                elif action_type == "mark_as_unread":
                    gmail_service.mark_as_read(email["message_id"], False)
                    email_db.mark_as_read(email["message_id"], False)
                elif action_type == "move_message":
                    if "label" in action:
                        gmail_service.move_message(email["message_id"], action["label"])
                        email_db.update_labels(email["message_id"], action["label"])
            return True
        except Exception as e:
            logger.error(f"Error applying actions for rule {self.name}: {e}")
        
        return False


class RuleProcessor:
    def __init__(self, rules_path=None):
        self.rules = []
        self.rules_path = rules_path or RULE_FILE_PATH
        self.load_rules()

    def load_rules(self):
        try:
            with open(self.rules_path, "r") as f:
                rules_data = json.load(f)

            for rule_data in rules_data["rules"]:
                conditions = [
                    RuleCondition(c["field"], c["predicate"], c["value"])
                    for c in rule_data["conditions"]
                ]
                rule = Rule(
                    rule_data["name"],
                    conditions,
                    rule_data["predicate"],
                    rule_data["actions"],
                )
                self.rules.append(rule)
        except Exception as e:
            logger.error(f"Error loading rules from {RULE_FILE_PATH}: {e}")

    def process_email(
        self,
        email: Dict[str, Any],
        gmail_service: GmailService,
        email_db: EmailDatabase,
    ) -> bool:
        """Process a single email through all rules."""
        try:
            for rule in self.rules:
                if rule.evaluate(email):
                    if rule.apply_actions(email, gmail_service, email_db):
                        logger.debug(
                            f"Successfully applied actions for rule '{rule.name}'"
                        )
                    else:
                        logger.error(f"Failed to apply actions for rule '{rule.name}'")

            return True
        except Exception as e:
            logger.error(f"Error processing email {email['message_id']}: {e}")
        
        return False
