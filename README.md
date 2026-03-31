<div align="center">
     
<img width="1280" height="318" alt="Gemini_Generated_Image_rj2u2qrj2u2qrj2u (1) (Custom)" src="https://github.com/user-attachments/assets/3cb94e1d-08ba-436b-b347-362cb00b481c" />

**A cross-platform utility for safe, selective cleanup of build artifacts and dependency bloat.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

`shatter` is a fast, multi-ecosystem CLI tool designed to safely reclaim disk space. It traverses your project directories to identify and remove stale build caches (`.next`, `__pycache__`, `.gradle`) and heavy dependency folders (`node_modules`, `.venv`, `target`). 

Built for developers working across multiple languages, `shatter` replaces a dozen disparate cleanup scripts with one standardized, automation-friendly command.

## Why `shatter`?

| Feature                |            `shatter`             |       `npkill`        |   `find / rm`    |
| :--------------------- | :------------------------------: | :-------------------: | :--------------: |
| **Multi-Ecosystem**    |  ✅ (Rust, Python, JS, Go, etc.)  |      ❌ (JS only)      | ❌ (Manual setup) |
| **Safety Guardrails**  |  ✅ (`.shatterignore`, dry-runs)  |           ❌           |        ❌         |
| **Parallel Execution** |  ✅ (Threaded size calculation)   |           ❌           |        ❌         |
| **CI/CD Ready**        | ✅ (Standard exit codes, `--yes`) | ❌ (Interactive focus) |        ✅         |

## Core Features

- 🛡️ **Safety-First Deletion** — includes a strict `--dry-run` mode to audit changes before any destructive action occurs.
- ⚡ **IO-Optimized Discovery** — separates filesystem walking (BFS) from metadata retrieval (size calculation) using parallel threads to maximize throughput.
- 🎯 **Targeted Scans** — isolate your cleanup to specific artifact types (`--cache` only, `--deps` only, or `--all`).
- 🛑 **Directory Protection** — drop a `.shatterignore` file in any directory to completely exclude it and its children from the scan.
- 🌍 **Universal Compatibility** — native support for JavaScript, Python, Rust, Go, PHP, Ruby, Java, .NET, Dart, and Expo.
- 🤖 **POSIX-Compliant** — easily integratable into cron jobs or background scripts with non-interactive flags (`--yes`).

## Install

```bash
# Clone the repository
git clone [https://github.com/TheLime1/shatter.git](https://github.com/TheLime1/shatter.git)
cd shatter

# Create a virtual environment and install
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e .
```

> **Requires Python 3.10+**

## Usage

```bash
shatter [PATH] [OPTIONS]
```

`PATH` defaults to the current directory (`.`) if omitted.

### Examples

```bash
# Audit mode: Preview targets and sizes without deleting anything (Recommended first step)
shatter ~/projects --all --dry-run

# Reclaim space from heavy dependencies (node_modules, .venv, target, vendor)
shatter ~/projects --deps

# Clear generated build caches (.next, __pycache__, .gradle)
shatter ~/projects --cache

# High-speed cleanup: Skip size calculations and delete immediately
shatter ~/projects --all --fast

# Detailed reporting: Group targets by project root with subtotals
shatter ~/projects --all --dry-run --verbose

# Automated cleanup: Skip confirmation prompts for CI/CD or scripts
shatter ~/projects --all --yes
```

## CLI Options

| Flag           | Short | Description                                                                          |
| -------------- | ----- | ------------------------------------------------------------------------------------ |
| `--cache`      | `-c`  | Target build cache directories only                                                  |
| `--deps`       | `-d`  | Target dependency directories only                                                   |
| `--all`        | `-a`  | Target both caches and deps                                                          |
| `--dry-run`    | `-n`  | Scan and report only — performs no disk mutations                                    |
| `--fast`       | `-f`  | Skip parallel size calculation for immediate execution                               |
| `--verbose`    | `-v`  | Group output by project root with localized size subtotals                           |
| `--yes`        | `-y`  | Bypass interactive confirmation prompts                                              |
| `--older-than` | `-o`  | Only target dirs not modified within the given period (e.g. `30d`, `2w`, `3m`, `1y`) |

## Supported Ecosystems

| Ecosystem          | Caches                                                              | Dependencies                 |
| ------------------ | ------------------------------------------------------------------- | ---------------------------- |
| **JavaScript**     | `.next` `.nuxt` `.svelte-kit` `.swc` `.turbo` `.parcel-cache`       | `node_modules`               |
| **Python**         | `__pycache__` `.pytest_cache` `.mypy_cache` `.ruff_cache` `.pytype` | `.venv` `venv` `.tox` `.nox` |
| **Rust**           | —                                                                   | `target`                     |
| **Go**             | —                                                                   | `vendor`                     |
| **PHP**            | —                                                                   | `vendor`                     |
| **Ruby**           | —                                                                   | `vendor/bundle`              |
| **Java / Kotlin**  | `.gradle` `build`                                                   | —                            |
| **.NET / C#**      | `bin` `obj`                                                         | —                            |
| **Expo**           | `.expo`                                                             | —                            |
| **Dart / Flutter** | `.dart_tool` `build`                                                | —                            |

## Protecting Critical Paths

If you have vendor folders or specific node_modules you need to preserve, create an empty `.shatterignore` file in that directory's root:

```bash
touch ~/projects/legacy-api/.shatterignore
```

`shatter` halts traversal upon detecting this file, ensuring the directory and its children remain untouched.

```text
  ⏭  Skipped legacy-api (found .shatterignore)
```

## Architecture & Extensibility

`shatter` is built to be easily extensible. You can add support for new languages or frameworks without touching the source code at all.

```text
shatter/
├── __init__.py       # package versioning
├── __main__.py       # execution entry point
├── targets.py        # ecosystem loader (reads ~/.shatter)
├── scanner.py        # core BFS walk + threaded size engine
└── cli.py            # terminal UI and argument parsing
```

### User Config — `~/.shatter`

On first run, `shatter` creates `~/.shatter` in your home directory populated with all built-in ecosystem definitions. Open it with any text editor to customise targets:

```json
{
  "ECOSYSTEMS": [
    {
      "name": "JavaScript",
      "caches": [".next", ".nuxt", "dist", "build"],
      "deps": ["node_modules", "bower_components"]
    },
    {
      "name": "Python",
      "caches": ["__pycache__", ".pytest_cache", ".mypy_cache"],
      "deps": [".venv", "venv", ".tox"]
    }
  ]
}
```

- **Add** a new object to the `ECOSYSTEMS` array to support a new language.
- **Remove** any entry you don't want scanned.
- **Customise** `caches` or `deps` arrays to match your workflow.

Changes take effect on the next run — no reinstall needed. If the file is deleted or becomes malformed, `shatter` will recreate it with the built-in defaults.

## Contributing

We welcome pull requests for new ecosystems, bug fixes, or performance optimizations. 

1. Fork the repository.
2. If adding a built-in ecosystem default, update `_DEFAULT_ECOSYSTEMS` in `targets.py`.
3. Submit a PR with a brief description and a reference link confirming the standard directory names for that ecosystem.

## License

MIT © 2026 Aymen Hmani

## Output Previews

<img width="811" height="380" alt="Antigravity_YXlYhz6RGP" src="https://github.com/user-attachments/assets/11c93f6f-a002-4649-b23b-f2c72682318e" />
<img width="975" height="242" alt="Antigravity_Cvhe8yfEf2" src="https://github.com/user-attachments/assets/0882c89f-7eb9-42f6-8a6d-aac26a77f5c6" />
