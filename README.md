# ![Shatter](docs/banner.webp)

Shatter shows how much space folders like `node_modules`, `.venv`, and `.next` take up across your projects. It lists the matching directories and their sizes, then asks before permanently deleting them.

## Install

With Git and Python 3.10 or later installed, run this in a Python environment you use for command-line tools.

```sh
python -m pip install git+https://github.com/TheLime1/shatter.git
```

## First scan

Preview the directories in your projects folder, grouped by repository. Replace `~/projects` with the folder you want to scan.

```sh
shatter ~/projects --all --dry-run --verbose
```

To clean up old dependency folders, narrow the scan and preview it again. Once the list looks right, repeat the command without `--dry-run` and confirm at the prompt.

```sh
shatter ~/projects --deps --older-than 30d --dry-run
```

The age filter uses the directory’s own modification time. Shatter matches directory names across all projects, so check generic names like `bin`, `build`, and `vendor` before confirming.

## Options

The scan path defaults to the current directory. Choose one target flag per scan.

| Target | Examples |
| --- | --- |
| `-c`, `--cache` | `.next`, `__pycache__`, `.gradle`, `CMakeFiles`, `.godot` |
| `-d`, `--deps` | `node_modules`, `.venv`, `vendor`, `Pods` |
| `-a`, `--all` | Both groups |

| Option | Effect |
| --- | --- |
| `-n`, `--dry-run` | List matches and exit before deletion. |
| `-v`, `--verbose` | Group matches by project and show subtotals. |
| `-f`, `--fast` | Skip size calculations and report directory counts. |
| `-o`, `--older-than` | Filter by age, for example `30d`, `2w`, `3m`, or `1y`. |
| `-y`, `--yes` | Delete matches without asking for confirmation. |

## Exclude a project

Place an empty file named `.shatterignore` at the root of a project you want to keep. For example, `~/projects/client-app/.shatterignore` makes Shatter skip that project when scanning `~/projects`.

Put the marker **above** any matching directory you want to keep. Shatter selects a directory such as `node_modules` before looking inside it, so a marker inside `node_modules` comes too late.

## Customize directory names

Shatter writes its defaults to `~/.shatter` on first use. Edit the `caches` and `deps` lists in that JSON file to change what the next scan picks up. Use individual directory names. To replace your edits with the built-in defaults, run `shatter init`.

The [built-in list](shatter/targets.py) includes web frameworks, compilers, and game engines. To contribute a default, include the directory name, what creates it, and how to regenerate its contents.

<details>
<summary>Example terminal output</summary>

![Scan results grouped by project, with sizes for individual dependency folders](https://github.com/user-attachments/assets/11c93f6f-a002-4649-b23b-f2c72682318e)
![Dry-run summary showing 3.6 GB of caches and 58.0 GB of dependencies](https://github.com/user-attachments/assets/0882c89f-7eb9-42f6-8a6d-aac26a77f5c6)

</details>

[MIT License](LICENSE) © 2026 Aymen Hmani
