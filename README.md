<div align="center">
     
<img width="1280" height="318" alt="Gemini_Generated_Image_rj2u2qrj2u2qrj2u (1) (Custom)" src="https://github.com/user-attachments/assets/3cb94e1d-08ba-436b-b347-362cb00b481c" />

**Recursively find and obliterate build caches & dependency bloat.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

`shatter` is a fast, cross-platform CLI tool that recursively walks your project directories and destroys build caches (`.next`, `__pycache__`, `.gradle`, …) and downloaded dependency folders (`node_modules`, `.venv`, `target`, …). It's built for developers who work across many projects and want to reclaim disk space in one command.

## Features

- 🔍 **Two-phase scan** — directory walk is near-instant; size calculation runs in parallel threads
- 🎯 **Targeted modes** — clean only caches, only deps, or both
- 🧾 **Dry-run** — preview everything that *would* be deleted before committing
- ⚡ **Fast mode** — skip size calculation entirely for instant results
- 📁 **Verbose mode** — group results by project with per-project subtotals  
- 🛡️ **`.shatterignore`** — drop a file in any directory to protect it and all its children
- 🌍 **Multi-ecosystem** — JavaScript, Python, Rust, Go, PHP, Ruby, Java, .NET, Dart, and more
- 🔌 **Contributor-friendly** — add new ecosystems by editing a single config file

## Install

```bash
# Clone the repo
git clone https://github.com/yourname/shatter.git
cd shatter

# Create a virtual environment and install
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e .
```

> **Requires Python 3.10+**

## Usage

```
shatter [PATH] [OPTIONS]
```

`PATH` defaults to the current directory (`.`) if omitted.

### Examples

```bash
# Preview everything that would be deleted (safe — nothing is removed)
shatter ~/projects --all --dry-run

# Delete only node_modules / .venv / target / vendor across all projects
shatter ~/projects --deps

# Delete only build caches (.next, __pycache__, .gradle …)
shatter ~/projects --cache

# Delete everything — fast, no size numbers
shatter ~/projects --all --fast

# Per-project breakdown grouped by repo, with sizes
shatter ~/projects --all --dry-run --verbose

# Skip confirmation prompt (useful in scripts / CI)
shatter ~/projects --all --yes
```

## Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--cache` | `-c` | Target build cache directories only |
| `--deps` | `-d` | Target dependency directories only |
| `--all` | `-a` | Target both caches and deps |
| `--dry-run` | `-n` | Scan and report — delete nothing |
| `--fast` | `-f` | Skip size calculation for instant results |
| `--verbose` | `-v` | Group results by project root with per-project subtotals |
| `--yes` | `-y` | Skip the deletion confirmation prompt |

## Supported Ecosystems

| Ecosystem | Caches | Dependencies |
|-----------|--------|-------------|
| **JavaScript** | `.next` `.nuxt` `.svelte-kit` `.swc` `.turbo` `.parcel-cache` | `node_modules` |
| **Python** | `__pycache__` `.pytest_cache` `.mypy_cache` `.ruff_cache` `.pytype` | `.venv` `venv` `.tox` `.nox` |
| **Rust** | — | `target` |
| **Go** | — | `vendor` |
| **PHP** | — | `vendor` |
| **Ruby** | — | `vendor/bundle` |
| **Java / Kotlin** | `.gradle` `build` | — |
| **.NET / C#** | `bin` `obj` | — |
| **Expo** | `.expo` | — |
| **Dart / Flutter** | `.dart_tool` `build` | — |

## Protecting a Directory with `.shatterignore`

Create an empty `.shatterignore` file in any directory to tell `shatter` to skip it and all its subdirectories entirely:

```bash
touch ~/projects/important-project/.shatterignore
```

`shatter` will print a subtle notice and move on:

```
  ⏭  Skipped important-project (found .shatterignore)
```

## How It Works

`shatter` uses a two-phase approach to stay fast even across hundreds of projects:

**Phase 1 — Walk (instant)**
A BFS traversal of the directory tree collects all matching target paths. The scanner is `.git`-aware: once it enters a project root (a directory containing `.git`), it limits recursion to a shallow depth so it doesn't wander into deeply nested generated code.

**Phase 2 — Size (parallel)**
Once all paths are collected, their sizes are computed concurrently using a `ThreadPoolExecutor`. Since disk I/O is the bottleneck, threads provide a real speedup here. Use `--fast` to skip this phase entirely if you only want to know *what* is there, not *how much*.

## Architecture

The codebase is designed so contributors can add new ecosystems **without touching any core logic**.

```
shatter/
├── __init__.py       # version
├── __main__.py       # python -m shatter entry point
├── targets.py        # ← ADD NEW ECOSYSTEMS HERE
├── scanner.py        # walk + size engine (never needs editing for new ecosystems)
└── cli.py            # Typer + Rich UI layer
```

### Adding a New Ecosystem

Open `shatter/targets.py` and append an entry to `ECOSYSTEMS`:

```python
Ecosystem(
    name="Zig",
    caches=[".zig-cache"],
    deps=[],
),
```

That's it. No other files need to change.

## Contributing

1. Fork the repo and create a branch
2. Add your ecosystem to `targets.py`
3. Open a pull request — please include a brief description of the ecosystem and a source link confirming the directory names

## License

MIT © 2024

## Screenshots

<img width="811" height="380" alt="Antigravity_YXlYhz6RGP" src="https://github.com/user-attachments/assets/11c93f6f-a002-4649-b23b-f2c72682318e" />
<img width="975" height="242" alt="Antigravity_Cvhe8yfEf2" src="https://github.com/user-attachments/assets/0882c89f-7eb9-42f6-8a6d-aac26a77f5c6" />


