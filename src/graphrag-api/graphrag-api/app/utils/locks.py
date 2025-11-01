
from contextlib import contextmanager
from pathlib import Path
import portalocker

@contextmanager
def session_lock(lock_file: Path):
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "a+") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        try:
            yield
        finally:
            portalocker.unlock(f)
