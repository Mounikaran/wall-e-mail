# Wall-E-Mail

A Python-based email automation tool that helps you manage your Gmail inbox using customizable rules.

## Features

- **Gmail Integration**: Seamless integration with Gmail using Gmail API
- **Rule-Based Processing**: Define custom rules to automatically process emails
- **Local Database**: SQLite-based storage for email metadata and processing state
- **Batch Processing**: Efficient batch processing of emails
- **Label Management**: Create and manage Gmail labels
- **Customizable Actions**: Supports actions like marking as read/unread and moving messages

## Project Structure

```
wall-e-mail/
├── database/               # Database related modules
│   ├── emails.db          # SQLite database file
│   └── emails.py          # Email database operations
├── rules/                 # Email processing rules
│   ├── config.json        # Rule configurations
│   └── processor.py       # Rule processing logic
├── services/              # External services integration
│   └── gmail_service.py   # Gmail API integration
├── tests/                 # Test suite
│   ├── test_database.py   # Database tests
│   ├── test_gmail.py      # Gmail service tests
│   └── test_rules.py      # Rule processor tests
├── logger.py              # Logging configuration
├── main.py               # Application entry point
├── requirements.txt      # Project dependencies
└── setup.py             # Package setup configuration
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Mounikaran/wall-e-mail.git
cd wall-e-mail
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Gmail API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `gmail_credentials.json` in the project root

## Configuration

1. Rules Configuration:
   - Edit `rules/config.json` to define your email processing rules
   - Example rule:
   ```json
   {
     "rules": [
       {
         "name": "Archive Newsletters",
         "conditions": [
           {
             "field": "subject",
             "predicate": "contains",
             "value": "newsletter"
           }
         ],
         "predicate": "all",
         "actions": [
           {
             "type": "move_message",
             "label": "Newsletters"
           }
         ]
       }
     ]
   }
   ```

## Usage

Run the application with optional command-line arguments:
```bash
python main.py [--email_count COUNT] [--days DAYS] [--only_unread BOOL]
```

### Command-line Arguments

- `--email_count COUNT`: Maximum number of emails to process (default: processes all matching emails)
  ```bash
  python main.py --email_count 100  # Process up to 100 emails
  ```

- `--days DAYS`: Number of days to look back for emails (default: 7)
  ```bash
  python main.py --days 30  # Process emails from the last 30 days
  ```

- `--only_unread BOOL`: Process only unread emails (default: False)
  ```bash
  python main.py --only_unread True  # Process only unread emails
  ```

### Usage Notes

**Important**: When using multiple arguments, be aware of these behaviors:

1. `--email_count` vs `--days`:
   - When both are provided, `--email_count` takes priority
   - The program will stop after processing the specified number of emails, even if there are more recent emails within the specified days
   - If you want to process ALL emails within a specific time range, use only `--days` without `--email_count`

### Usage Examples

Process the most recent 50 emails (regardless of date):
```bash
python main.py --email_count 50
```

Process all emails from the last 3 days:
```bash
python main.py --days 3
```

Process only unread emails from the last 7 days:
```bash
python main.py --days 7 --only_unread True
```

Not Recommended (email_count will override days filter):
```bash
python main.py --email_count 50 --days 14  # Will stop after 50 emails
```

The application will:
1. Authenticate with Gmail
2. Fetch emails based on the provided criteria
3. Process them according to your rules
4. Store email metadata in the local database
5. Apply configured actions (mark as read/unread, move to labels)
6. Show progress with a progress bar for each batch

## Testing

Run the test suite:
```bash
pytest
```

The test suite includes:
- Database operations tests
- Gmail service integration tests
- Rule processing tests

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Gmail API
- SQLite
- Python Community