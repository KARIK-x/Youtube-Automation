"""Safe output handling: unique names, atomic copy."""
import os, shutil, tempfile
from pathlib import Path

def unique_path(directory, base_name):
    """Return a non-existing path in directory for base_name, suffixing if needed."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / base_name
    if not candidate.exists():
        return candidate
    stem = Path(base_name).stem
    suf = Path(base_name).suffix
    i = 1
    while (directory / f"{stem}_{i}{suf}").exists():
        i += 1
    return directory / f"{stem}_{i}{suf}"

def atomic_copy(src, dst):
    """Copy src to dst atomically via temp file + rename. Validates src exists."""
    src = Path(src); dst = Path(dst)
    if not src.exists():
        raise FileNotFoundError(f"source missing: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dst.parent), prefix=".tmp_")
    os.close(fd)
    try:
        shutil.copy2(src, tmp)
        # validate
        if os.path.getsize(tmp) == 0:
            raise RuntimeError("empty output")
        os.replace(tmp, dst)
    except Exception:
        try: os.remove(tmp)
        except OSError: pass
        raise
    return dst
