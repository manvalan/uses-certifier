"""Local copy of the uses-rules repository, fetched on demand."""
import os
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/manvalan/uses-rules"
CACHE_ENV = "USES_RULES_CACHE"


class FetchError(Exception):
    """The rules repository could not be downloaded."""


def cache_dir():
    """Folder of the cached rules (USES_RULES_CACHE or the user cache)."""
    if os.environ.get(CACHE_ENV):
        return Path(os.environ[CACHE_ENV])
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "uses-certifier" / "uses-rules"


def cached():
    """The cached rules folder, or None when it was never fetched."""
    path = cache_dir()
    return path if (path / "rules").is_dir() else None


def fetch(ref="main", url=None):
    """Download or update the rules at the given branch or tag."""
    path = cache_dir()
    if (path / ".git").is_dir():
        _git("-C", str(path), "fetch", "--depth", "1", "origin", ref)
        _git("-C", str(path), "checkout", "--quiet", "FETCH_HEAD")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--quiet", "--depth", "1", "--branch", ref,
             url or REPO_URL, str(path))
    return path


def _git(*args):
    """Run git, turning a failure into a readable error."""
    try:
        subprocess.run(["git", *args], check=True, capture_output=True,
                       text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise FetchError(f"git {' '.join(args)} failed: {detail.strip()}")
