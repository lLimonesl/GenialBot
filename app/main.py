"""Railway entrypoint.

Importing bot starts the Discord client and the embedded FastAPI dashboard.
Keeping this module thin makes the Railway start command stable while the
legacy root files are refactored incrementally.
"""

import bot  # noqa: F401
