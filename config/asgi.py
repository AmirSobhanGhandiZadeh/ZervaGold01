import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# در Sprint بعدی (پیاده‌سازی Pricing/WebSocket طبق ADR-027)،
# یک URLRouter برای "websocket" اضافه می‌شود.
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
    }
)
