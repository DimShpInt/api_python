"""API Python Package."""

from api_python.config import settings

__version__ = "0.1.0"

# __all__ явно указывает, что экспортируется при `from api_python import *`
__all__ = [
    "__version__",
    "settings",
]
