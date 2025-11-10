from os import environ

# Telegram Bot Configuration
API_ID = int(environ.get("API_ID", "22182189"))
API_HASH = environ.get("API_HASH", "5e7c4088f8e23d0ab61e29ae11960bf5")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

# Wasabi Configuration
WASABI_ACCESS_KEY = environ.get("WASABI_ACCESS_KEY", "")
WASABI_SECRET_KEY = environ.get("WASABI_SECRET_KEY", "")
WASABI_REGION = environ.get("WASABI_REGION", "us-east-1")
WASABI_BUCKET = environ.get("WASABI_BUCKET", "")
WASABI_ENDPOINT = f"s3.{WASABI_REGION}.wasabisys.com"
