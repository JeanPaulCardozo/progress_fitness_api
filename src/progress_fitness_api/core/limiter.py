from slowapi import Limiter
from slowapi.util import get_remote_address

Limit = Limiter(key_func=get_remote_address)
