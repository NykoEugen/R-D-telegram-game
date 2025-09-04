# Handlers Package
from .commands import start_router, game_router, language_router

# Backward compatibility
start = start_router
game = game_router  
language = language_router
