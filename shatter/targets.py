"""
targets.py — Ecosystem target registry.

Built-in defaults are written to ~/.shatter on first run.
Users can freely edit that file to add, remove, or customise ecosystems.
The core engine reads exclusively from that config — no source edits required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH: Path = Path.home() / ".shatter"

# ──────────────────────────────────────────────────────────────────────────────
#  Data model
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Ecosystem:
    """Represents a language / framework ecosystem and the directories it generates."""

    name: str
    caches: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
#  Built-in defaults  (written to ~/.shatter on first run)
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_ECOSYSTEMS: list[Ecosystem] = [
    # ── JavaScript / TypeScript ────────────────
    Ecosystem(
        name="JavaScript",
        caches=[
            ".next",
            ".nuxt",
            ".svelte-kit",
            ".swc",
            ".turbo",
            ".parcel-cache",
            ".eslintcache",
            ".angular",
            ".cache",
            ".docusaurus",
            ".vuepress",
            "dist",
            "build",
            "out",
            ".serverless",
            ".netlify",
            ".webpack",
        ],
        deps=["node_modules", "bower_components"],
    ),
    # ── Python ─────────────────────────────────
    Ecosystem(
        name="Python",
        caches=[
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".pytype",
            ".hypothesis",
            ".pyre",
            ".eggs",
            "eggs",
            "htmlcov",
            "build",
            "dist",
        ],
        deps=[".venv", "venv", "env", "virtualenv",
              ".tox", ".nox", "__pypackages__"],
    ),
    # ── Rust ───────────────────────────────────
    Ecosystem(
        name="Rust",
        caches=[],
        deps=["target"],
    ),
    # ── Go ─────────────────────────────────────
    Ecosystem(
        name="Go",
        caches=[],
        deps=["vendor"],
    ),
    # ── PHP ────────────────────────────────────
    Ecosystem(
        name="PHP",
        caches=[".phpunit.cache"],
        deps=["vendor"],
    ),
    # ── Ruby ───────────────────────────────────
    Ecosystem(
        name="Ruby",
        caches=["tmp/cache", ".yardoc"],
        deps=["vendor/bundle", ".bundle"],
    ),
    # ── Java / Scala / Kotlin ──────────────────
    Ecosystem(
        name="Java / JVM",
        caches=[".gradle", "build", "target", ".bloop", ".metals"],
        deps=[],
    ),
    # ── .NET / C# ──────────────────────────────
    Ecosystem(
        name=".NET",
        caches=["bin", "obj", ".vs", "TestResults", ".ionide"],
        deps=["packages"],
    ),
    # ── Mobile (Expo / React Native) ───────────
    Ecosystem(
        name="Expo",
        caches=[".expo", ".cxx"],
        deps=[],
    ),
    # ── Dart / Flutter ─────────────────────────
    Ecosystem(
        name="Dart",
        caches=[".dart_tool", "build"],
        deps=[".pub-cache"],
    ),
    # ── C / C++ ────────────────────────────────
    Ecosystem(
        name="C/C++",
        caches=[
            "cmake-build-debug",
            "cmake-build-release",
            "out",
            "bin",
            ".cache",
            "CMakeFiles",
            ".ccls-cache",
        ],
        deps=[],
    ),
    # ── Swift / macOS / iOS ────────────────────
    Ecosystem(
        name="Swift",
        caches=["DerivedData", ".build", ".swiftpm"],
        deps=["Pods", "Carthage"],
    ),
    # ── Elixir / Erlang ────────────────────────
    Ecosystem(
        name="Elixir",
        caches=["_build", ".elixir_ls"],
        deps=["deps"],
    ),
    # ── Haskell ────────────────────────────────
    Ecosystem(
        name="Haskell",
        caches=["dist", "dist-newstyle", ".stack-work"],
        deps=[],
    ),
    # ── Clojure ────────────────────────────────
    Ecosystem(
        name="Clojure",
        caches=["target", ".cpcache", ".shadow-cljs"],
        deps=[],
    ),
    # ── OCaml ──────────────────────────────────
    Ecosystem(
        name="OCaml",
        caches=["_build"],
        deps=[],
    ),
    # ── Zig ────────────────────────────────────
    Ecosystem(
        name="Zig",
        caches=["zig-cache", "zig-out"],
        deps=[],
    ),
    # ── Nim ────────────────────────────────────
    Ecosystem(
        name="Nim",
        caches=["nimcache"],
        deps=[],
    ),
    # ── Game Engines (Unity, Godot, Unreal) ────
    Ecosystem(
        name="Unity",
        caches=["Library", "Logs", "obj", "Temp", "MemoryCaptures", "Builds"],
        deps=[],
    ),
    Ecosystem(
        name="Godot",
        caches=[".godot"],
        deps=[],
    ),
    Ecosystem(
        name="Unreal Engine",
        caches=["Binaries", "Build", "DerivedDataCache",
                "Intermediate", "Saved"],
        deps=[],
    ),
    # ── Data Science / R ───────────────────────
    Ecosystem(
        name="R",
        caches=[".Rproj.user", ".Rhistory"],
        deps=["renv"],
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
#  Config helpers
# ──────────────────────────────────────────────────────────────────────────────


def _ecosystems_to_json(ecosystems: list[Ecosystem]) -> dict:
    return {
        "ECOSYSTEMS": [
            {"name": e.name, "caches": list(e.caches), "deps": list(e.deps)}
            for e in ecosystems
        ]
    }


def _json_to_ecosystems(data: dict) -> list[Ecosystem]:
    return [
        Ecosystem(
            name=entry["name"],
            caches=list(entry.get("caches", [])),
            deps=list(entry.get("deps", [])),
        )
        for entry in data.get("ECOSYSTEMS", [])
    ]


def _ensure_config() -> None:
    """Write the default config to ~/.shatter if it does not already exist."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(_ecosystems_to_json(_DEFAULT_ECOSYSTEMS), indent=2),
            encoding="utf-8",
        )


def load_ecosystems() -> list[Ecosystem]:
    """
    Return the list of Ecosystem objects from ~/.shatter.

    If the file does not exist it is created with the built-in defaults first.
    Falls back to the built-in defaults if the file is malformed.
    """
    _ensure_config()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        ecosystems = _json_to_ecosystems(data)
        if not ecosystems:
            raise ValueError("empty ECOSYSTEMS list")
        return ecosystems
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        return list(_DEFAULT_ECOSYSTEMS)


# ──────────────────────────────────────────────────────────────────────────────
#  Module-level sets consumed by scanner.py
# ──────────────────────────────────────────────────────────────────────────────

# Populated at import time from the user config / defaults.
ECOSYSTEMS: list[Ecosystem] = load_ecosystems()


def _collect(attr: str) -> set[str]:
    """Gather all unique directory names for a given attribute across ecosystems."""
    names: set[str] = set()
    for eco in ECOSYSTEMS:
        names.update(getattr(eco, attr))
    return names


ALL_CACHE_DIRS: set[str] = _collect("caches")
ALL_DEP_DIRS: set[str] = _collect("deps")
ALL_TARGET_DIRS: set[str] = ALL_CACHE_DIRS | ALL_DEP_DIRS
