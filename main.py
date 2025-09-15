import argparse
from tqdm import tqdm

from logger import logger
from services.gmail_service import GmailService
from database.emails import EmailDatabase
from rules.processor import RuleProcessor


def process_emails(email_count: int, days: int, only_unread: bool):
    try:
        # Initialize services
        email_service = GmailService()
        email_db = EmailDatabase()
        rule_processor = RuleProcessor()

        # Process emails in batches
        total_processed = 0
        batch_no = 1
        for batch in email_service.get_emails_batch(
            max_results=email_count, days=days, only_unread=only_unread
        ):
            logger.info(f"Processing batch of {len(batch)} emails...")

            try:
                # Prepare email data for batch insertion
                for email in batch:
                    email["labels"] = ",".join(email["labels"])

                # Store entire batch in database at once
                email_db.add_emails_batch(batch)

                # Process batch through rules
                batch_processed_ids = []
                with tqdm(total=len(batch), desc=f"Batch {batch_no}") as progress_bar:
                    for email in batch:
                        try:
                            if rule_processor.process_email(email, email_service, email_db):
                                batch_processed_ids.append(email["message_id"])
                        except Exception as e:
                            logger.error(
                                f"Error processing email {email['message_id']}: {e}"
                            )
                            continue
                        progress_bar.update(1)
                batch_no += 1

                # Mark processed emails in batch
                if batch_processed_ids:
                    total_processed += len(batch_processed_ids)
                    logger.info(
                        f"Marked {len(batch_processed_ids)} emails as processed in this batch. Total processed: {total_processed}"
                    )
                    email_db.mark_as_processed_batch(batch_processed_ids)

            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                continue

    except Exception as e:
        logger.error("An error occurred while processing emails: %s", e)
        raise
    finally:
        email_db.close()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Mail cleanup tool")

    arg_parser.add_argument(
        "--email_count",
        type=int,
        default=None,
        help="Maximum number of emails to process in the mailbox",
    )
    arg_parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days to look back for emails",
    )
    arg_parser.add_argument(
        "--only_unread",
        type=bool,
        default=False,
        help="Process only unread emails",
    )

    args = arg_parser.parse_args()

    email_count = args.email_count
    days = args.days
    only_unread = args.only_unread

    # Validate arguments
    if email_count is not None and email_count < 1:
        raise ValueError("email_count must be at least 1")
    if days is not None and days < 1:
        raise ValueError("days must be at least 1")
    if not isinstance(only_unread, bool):
        raise ValueError("only_unread must be a boolean value")
    
    if days is None and email_count is None:
        logger.info("No filters specified, setting default values: days=7")
        days = 7

    # Process emails
    process_emails(email_count, days, only_unread)
