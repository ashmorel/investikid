from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# In development the limiter is disabled so test suites and rapid local iteration
# don't trip per-IP thresholds that exist for production abuse protection.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.environment != "development",
)
