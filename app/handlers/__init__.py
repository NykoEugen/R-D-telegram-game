# Handlers Package
from .commands import language_router, start_router

# Backward compatibility
start = start_router
language = language_router
