"""Secure file deletion — overwrites content before removing."""

import os
import logging

logger = logging.getLogger(__name__)


def secure_delete(path: str) -> bool:
    """Overwrite file with random bytes, then delete.

    Returns True if file was deleted, False on error.
    """
    if not path or not os.path.exists(path):
        return False

    try:
        size = os.path.getsize(path)
        with open(path, "wb") as f:
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
        os.remove(path)
        return True
    except Exception as e:
        logger.warning("Secure delete failed for %s: %s — falling back to standard delete", path, e)
        try:
            os.remove(path)
            return True
        except Exception:
            return False
