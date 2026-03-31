"""
scanner.py — Filesystem scanner and deletion engine.

Two-phase design for maximum speed:
  Phase 1 — Walk:   BFS through the directory tree, instantly collect target paths.
                    Stops recursing into a project deeper than MAX_PROJECT_DEPTH
                    levels past its .git root.
  Phase 2 — Size:   Compute directory sizes in parallel via ThreadPoolExecutor.
                    I/O-bound work → threads give real speedup.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Callable, Literal

from rich.console import Console

from .targets import ALL_CACHE_DIRS, ALL_DEP_DIRS

IGNORE_FILE = ".shatterignore"
# levels deep inside a project root (.git sibling) to scan
MAX_PROJECT_DEPTH = 4
MAX_WORKERS = 16        # parallel threads for size calculation

TargetKind = Literal["cache", "dep"]


# ── data structures ─────────────────────────────


@dataclass
class FoundTarget:
    """A directory that matched one of the known target names."""

    path: Path
    kind: TargetKind
    project_root: Path | None = None  # nearest ancestor that contained .git
    size_bytes: int = 0


@dataclass
class ScanResult:
    """Aggregated result of a full scan."""

    targets: list[FoundTarget] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(t.size_bytes for t in self.targets)

    @property
    def cache_bytes(self) -> int:
        return sum(t.size_bytes for t in self.targets if t.kind == "cache")

    @property
    def dep_bytes(self) -> int:
        return sum(t.size_bytes for t in self.targets if t.kind == "dep")

    def by_project(self) -> dict[Path | None, list[FoundTarget]]:
        """Group targets by their project root (None = no .git ancestor found)."""
        groups: dict[Path | None, list[FoundTarget]] = {}
        for t in self.targets:
            groups.setdefault(t.project_root, []).append(t)
        return groups


# ── helpers ─────────────────────────────────────


def dir_size(path: Path) -> int:
    """
    Compute total byte size of a directory using os.scandir DirEntry caching.
    DirEntry.stat() on Windows avoids a second syscall — much faster than rglob+stat.
    """
    total = 0
    stack = [str(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue
    return total


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:,.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:,.1f} PB"


# ── duration helpers ─────────────────────────────

_DURATION_RE = re.compile(r"^(\d+)\s*([dDmMyYwW])$")
_UNIT_DAYS = {"d": 1, "w": 7, "m": 30, "y": 365}


def parse_duration(value: str) -> timedelta:
    """Parse a human duration string into a timedelta.

    Accepted units: d (days), w (weeks), m (months ~30d), y (years ~365d).
    Examples: '30d', '3m', '1y', '2w'.
    """
    m = _DURATION_RE.match(value.strip())
    if not m:
        raise ValueError(
            f"Invalid duration {value!r}. Use e.g. '30d', '2w', '3m', '1y'."
        )
    n, unit = int(m.group(1)), m.group(2).lower()
    return timedelta(days=n * _UNIT_DAYS[unit])


def filter_older_than(targets: list[FoundTarget], max_age: timedelta) -> list[FoundTarget]:
    """Return only targets whose directory mtime is older than max_age from now."""
    cutoff = time.time() - max_age.total_seconds()
    kept = []
    for t in targets:
        try:
            if t.path.stat().st_mtime < cutoff:
                kept.append(t)
        except OSError:
            pass
    return kept


# ── phase 1: walk ───────────────────────────────


def _resolve_targets(mode: str) -> set[str]:
    if mode == "cache":
        return ALL_CACHE_DIRS
    if mode == "deps":
        return ALL_DEP_DIRS
    return ALL_CACHE_DIRS | ALL_DEP_DIRS


def _walk(
    root: Path,
    wanted: set[str],
    console: Console,
    on_visit: Callable[[Path], None] | None,
) -> ScanResult:
    """
    Phase 1: pure BFS walk — no size computation, returns instantly.

    Stack entries: (dir_path, current_project_root | None, remaining_depth | None)
    """
    result = ScanResult()
    resolved_root = root.resolve()

    # .shatterignore guard for the root itself — bail out immediately
    if (resolved_root / IGNORE_FILE).exists():
        result.skipped.append(resolved_root)
        console.print(
            f"  [bold yellow]🛡  {resolved_root.name}[/bold yellow] "
            f"[dim]is protected by .shatterignore — skipping entirely[/dim]"
        )
        return result

    # (path, project_root, remaining_depth)
    stack: list[tuple[Path, Path | None, int | None]] = [
        (resolved_root, None, None)]

    while stack:
        current, proj_root, remaining = stack.pop()

        if on_visit:
            on_visit(current)

        # .shatterignore guard for subdirectories
        if (current / IGNORE_FILE).exists() and current != resolved_root:
            result.skipped.append(current)
            console.print(
                f"  [dim]⏭  Skipped [bold]{current.name}[/bold] "
                f"(found .shatterignore)[/dim]"
            )
            continue

        # Detect project root (dir that contains .git)
        if proj_root is None and (current / ".git").exists() and current != resolved_root:
            proj_root = current
            remaining = MAX_PROJECT_DEPTH

        # Depth exhausted — stop recursing
        if remaining is not None and remaining <= 0:
            continue

        try:
            children = sorted(current.iterdir())
        except (PermissionError, OSError):
            continue

        for child in children:
            if not child.is_dir():
                continue
            if child.name == ".git":
                continue

            if child.name in wanted:
                kind: TargetKind = "cache" if child.name in ALL_CACHE_DIRS else "dep"
                result.targets.append(
                    FoundTarget(path=child, kind=kind, project_root=proj_root)
                )
                continue  # don't recurse into matched dirs

            next_depth: int | None = None
            next_proj = proj_root
            if remaining is not None:
                next_depth = remaining - 1
            elif (child / ".git").exists():
                next_proj = child
                next_depth = MAX_PROJECT_DEPTH

            stack.append((child, next_proj, next_depth))

    return result


# ── phase 2: parallel size ──────────────────────


def _fill_sizes(
    result: ScanResult,
    on_progress: Callable[[FoundTarget], None] | None = None,
) -> None:
    """
    Phase 2: compute sizes for all targets in parallel using threads.
    Mutates result.targets in-place.
    """
    if not result.targets:
        return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_target = {
            pool.submit(dir_size, t.path): t for t in result.targets
        }
        for future in as_completed(future_to_target):
            t = future_to_target[future]
            try:
                t.size_bytes = future.result()
            except Exception:
                t.size_bytes = 0
            if on_progress:
                on_progress(t)


# ── public API ──────────────────────────────────


def scan(
    root: Path,
    mode: str,
    console: Console,
    on_visit: Callable[[Path], None] | None = None,
    on_size_progress: Callable[[FoundTarget], None] | None = None,
    fast: bool = False,
) -> ScanResult:
    """
    Full two-phase scan:
      1. Walk (instant BFS)
      2. Parallel size calculation (skipped when fast=True)
    """
    wanted = _resolve_targets(mode)
    result = _walk(root, wanted, console, on_visit)
    if not fast:
        _fill_sizes(result, on_size_progress)
    return result


# ── deletion ────────────────────────────────────


def delete_targets(
    targets: list[FoundTarget],
    console: Console,
    on_progress: Callable[[FoundTarget], None] | None = None,
) -> int:
    """Delete every target directory. Returns count of successfully removed dirs."""
    removed = 0
    for t in targets:
        try:
            shutil.rmtree(t.path)
            removed += 1
        except Exception as exc:
            console.print(f"  [red]✗  Failed to remove {t.path}: {exc}[/red]")
        finally:
            if on_progress:
                on_progress(t)
    return removed
