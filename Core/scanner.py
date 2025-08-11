# core/scanner.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import os
from typing import Generator, Optional, Dict


@dataclass(frozen=True)
class FileMeta:
    """Lightweight record describing a file on disk."""
    path: str
    name: str
    parent: str
    extension: str
    size_bytes: int
    created: datetime
    modified: datetime
    is_text: bool
    preview: Optional[str] = None  # short text preview for small text files

    def to_dict(self) -> Dict:
        return asdict(self)


class FileScanner:
    """
    Recursively scans directories and yields FileMeta records.

    Usage:
        # Your test folder:
        #   /Users/abraheemrashid/Desktop/Metadata
        scanner = FileScanner("/Users/abraheemrashid/Desktop/Metadata", include_hidden=False)
        for meta in scanner.scan():
            print(meta.name, meta.size_bytes)
    """
    SMALL_PREVIEW_LIMIT = 1_000_000  # read preview only if file <= 1 MB
    PREVIEW_CHARS = 500

    def __init__(self,
                 root: Path | str,
                 include_hidden: bool = False,
                 follow_symlinks: bool = False) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Root path does not exist: {self.root}")
        self.include_hidden = include_hidden
        self.follow_symlinks = follow_symlinks

    def scan(self) -> Generator[FileMeta, None, None]:
        """
        Generator: yields FileMeta for each regular file under root.
        """
        for path in self._iter_paths(self.root):
            try:
                yield self.path_to_metadata(path)
            except (PermissionError, OSError):
                # Skip unreadable/special files
                continue

    def _iter_paths(self, directory: Path) -> Generator[Path, None, None]:
        """Iterate files recursively using os.scandir for speed."""
        try:
            with os.scandir(directory) as it:
                for entry in it:
                    try:
                        # Skip hidden if requested
                        if not self.include_hidden and self._is_hidden(entry.name, directory):
                            continue

                        if entry.is_dir(follow_symlinks=self.follow_symlinks):
                            # Avoid infinite loops on cyclic symlinks
                            if not self.follow_symlinks and os.path.islink(entry.path):
                                continue
                            yield from self._iter_paths(Path(entry.path))
                        elif entry.is_file(follow_symlinks=self.follow_symlinks):
                            yield Path(entry.path)
                        # ignore other types (sockets, FIFOs)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            return  # silently skip unreadable dirs

    @staticmethod
    def _is_hidden(name: str, parent: Path) -> bool:
        """
        Consider hidden if the name begins with '.' or any ancestor is hidden.
        Cross-platform: On Windows, leading dot still treated as 'hidden' conventionally.
        """
        if name.startswith('.'):
            return True
        # Walk up from parent to root to detect hidden ancestors (dot folders)
        p = parent
        while True:
            if p.name.startswith('.'):
                return True
            if p.parent == p:
                break
            p = p.parent
        return False

    @classmethod
    def path_to_metadata(cls, path: Path) -> FileMeta:
        """Build a FileMeta from a Path (classmethod per spec)."""
        st = path.stat()
        ext = (path.suffix[1:].lower() if path.suffix else "")
        created = cls._ts_to_dt(st.st_ctime)
        modified = cls._ts_to_dt(st.st_mtime)
        is_text = cls._looks_like_text(path)
        preview = None

        if is_text and st.st_size <= cls.SMALL_PREVIEW_LIMIT:
            preview = cls._safe_read_preview(path, cls.PREVIEW_CHARS)

        return FileMeta(
            path=str(path),
            name=path.name,
            parent=str(path.parent),
            extension=ext,
            size_bytes=st.st_size,
            created=created,
            modified=modified,
            is_text=is_text,
            preview=preview
        )

    @staticmethod
    def _ts_to_dt(ts: float) -> datetime:
        # Local time; we’ll normalize/format for dashboards later
        return datetime.fromtimestamp(ts)

    @staticmethod
    def _looks_like_text(path: Path, probe_bytes: int = 1024) -> bool:
        """
        Heuristic: if first N bytes contain NULL, treat as binary.
        Falls back to 'True' if readable with utf-8 ignoring errors.
        """
        try:
            with open(path, "rb") as f:
                chunk = f.read(probe_bytes)
            if b"\x00" in chunk:
                return False
            # Secondary heuristic: try decoding (won't raise with errors='ignore')
            _ = chunk.decode("utf-8", errors="ignore")
            return True
        except (OSError, PermissionError):
            return False

    @staticmethod
    def _safe_read_preview(path: Path, chars: int) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(chars)
            # one-line it for small dashboards
            return " ".join(text.split())
        except (OSError, PermissionError):
            return None


# ---------- Quick test runner (defaults to your Metadata folder) ----------
if __name__ == "__main__":
    import argparse, json

    # Prefer the exact path you gave; also try common variants in case-insensitive filesystems.
    candidates = [
        Path("/Users/abraheemrashid/Desktop/Metadata"),
        Path("/Users/abraheemrashid/desktop/Metadata"),
        Path("~/Desktop/Metadata").expanduser(),
        Path("~/desktop/Metadata").expanduser(),
    ]
    default_path = None
    for c in candidates:
        try:
            if c.exists():
                default_path = c.resolve()
                break
        except Exception:
            continue
    if default_path is None:
        # Fall back to the first candidate; FileScanner will raise if it truly doesn't exist.
        default_path = candidates[0]

    ap = argparse.ArgumentParser(description="Quick test for FileScanner")
    ap.add_argument(
        "--root",
        default=str(default_path),
        help="Folder to scan (defaults to your Metadata folder)"
    )
    ap.add_argument("--show", type=int, default=10, help="How many files to print")
    args = ap.parse_args()

    try:
        scanner = FileScanner(args.root, include_hidden=False, follow_symlinks=False)
        files = list(scanner.scan())
    except FileNotFoundError as e:
        # Helpful hint if the Desktop/desktop casing was the issue.
        print(e)
        print("Tip: On macOS try 'Desktop' with a capital D if the path is case-sensitive.")
        raise

    print(f"Scanned {len(files)} files under {scanner.root}")

    # Lightweight preview without importing utils.py
    def _hsize(b: int) -> str:
        return f"{b/1024:.1f} KB" if b < 1_048_576 else f"{b/1_048_576:.2f} MB"

    preview = [
        {
            "name": m.name,
            "ext": (m.extension or "-"),
            "size": _hsize(m.size_bytes),
            "folder": m.parent,
            "modified": m.modified.isoformat(timespec="seconds"),
        }
        for m in files[:args.show]
    ]
    print(json.dumps(preview, indent=2))
