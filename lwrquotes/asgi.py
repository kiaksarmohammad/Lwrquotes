import os, sys
from pathlib import Path
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

load_dotenv(_BASE_DIR / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lwrquotes.settings")

from django.core.asgi import get_asgi_application
application = get_asgi_application()
