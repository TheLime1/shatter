"""
cli.py — Typer CLI interface for shatter.
"""

from __future__ import annotations

import threading
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from . import __version__
from .scanner import FoundTarget, ScanResult, delete_targets, format_size, scan

app = typer.Typer(
    name="shatter",
    help="🔨 Recursively find and obliterate build caches & dependency bloat.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

BANNER = r"""
[bold bright_magenta]     _____ __          __  __           
    / ___// /_  ____ _/ /_/ /____  _____
    \__ \/ __ \/ __ `/ __/ __/ _ \/ ___/
   ___/ / / / / /_/ / /_/ /_/  __/ /    
  /____/_/ /_/\__,_/\__/\__/\___/_/[/bold bright_magenta]     [dim]v{version}[/dim]
"""


def _print_banner() -> None:
    console.print(BANNER.format(version=__version__))


# ── live-spinner helper ──────────────────────────


class LiveSpinner:
    """Thread-safe live line with a spinner + dynamic status message."""

    def __init__(self, label: str, style: str = "bright_magenta") -> None:
        self._label = label
        self._style = style
        self._status = ""
        self._lock = threading.Lock()
        self._spinner = Spinner("dots", style=style)
        self._stop = threading.Event()
        self._live: Live | None = None

    def set_status(self, msg: str) -> None:
        with self._lock:
            self._status = msg

    def _render(self) -> Text:
        t = Text()
        t.append("  ")
        t.append_text(self._spinner.render(console.get_time()))
        t.append(f"  {self._label} ", style=f"bold {self._style}")
        with self._lock:
            status = self._status
        max_len = max(console.width - 35, 20)
        if len(status) > max_len:
            status = "…" + status[-(max_len - 1):]
        t.append(status, style="dim")
        return t

    def __enter__(self) -> "LiveSpinner":
        self._live = Live(self._render(), console=console,
                          refresh_per_second=12, transient=True)
        self._live.__enter__()

        def _loop() -> None:
            while not self._stop.is_set():
                if self._live:
                    self._live.update(self._render())
                self._stop.wait(0.08)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
        if self._live:
            self._live.__exit__(*args)


# ── table builders ───────────────────────────────


def _kind_badge(kind: str) -> Text:
    return (
        Text("  cache ", style="bold white on dark_orange3")
        if kind == "cache"
        else Text("  deps  ", style="bold white on blue")
    )


def _flat_table(result: ScanResult, fast: bool = False) -> Table:
    """Default: one row per found target, sorted by size desc."""
    size_header = "Count" if fast else "Size"
    table = Table(
        title="[bold bright_white]  Scan Results[/bold bright_white]",
        box=box.ROUNDED,
        border_style="bright_magenta",
        header_style="bold bright_cyan",
        show_lines=True,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Directory", style="bright_white", min_width=42)
    table.add_column("Type", justify="center", width=10)
    table.add_column(size_header, justify="right",
                     style="bold bright_yellow", width=12)

    targets = (
        result.targets
        if fast
        else sorted(result.targets, key=lambda x: x.size_bytes, reverse=True)
    )
    for i, t in enumerate(targets, start=1):
        size_cell = "—" if fast else format_size(t.size_bytes)
        table.add_row(str(i), str(t.path), _kind_badge(t.kind), size_cell)

    return table


def _verbose_table(result: ScanResult, fast: bool = False) -> Table:
    """--verbose: group by project root with per-project subtotals."""
    table = Table(
        title="[bold bright_white]  Scan Results — by Project[/bold bright_white]",
        box=box.ROUNDED,
        border_style="bright_magenta",
        header_style="bold bright_cyan",
        show_lines=True,
        padding=(0, 1),
    )
    table.add_column("Project / Directory", style="bright_white", min_width=50)
    table.add_column("Type", justify="center", width=10)
    table.add_column("Size" if not fast else "Dirs",
                     justify="right", style="bold bright_yellow", width=12)

    groups = result.by_project()
    sorted_groups = sorted(
        groups.items(),
        key=lambda kv: sum(
            t.size_bytes for t in kv[1]) if not fast else len(kv[1]),
        reverse=True,
    )

    for proj_root, targets in sorted_groups:
        proj_label = proj_root.name if proj_root else "(no project)"
        proj_summary = f"{len(targets)} dir(s)" if fast else format_size(
            sum(t.size_bytes for t in targets))

        table.add_row(
            Text(f"📁 {proj_label}", style="bold bright_cyan"),
            Text(""),
            Text(proj_summary, style="bold bright_cyan"),
        )

        row_targets = targets if fast else sorted(
            targets, key=lambda x: x.size_bytes, reverse=True)
        for t in row_targets:
            try:
                rel = t.path.relative_to(proj_root) if proj_root else t.path
            except ValueError:
                rel = t.path
            table.add_row(
                Text(f"   └─ {rel}", style="dim white"),
                _kind_badge(t.kind),
                "—" if fast else format_size(t.size_bytes),
            )

    return table


def _totals_panel(result: ScanResult, dry_run: bool, fast: bool = False) -> Panel:
    lines: list[str] = []
    n_cache = sum(1 for t in result.targets if t.kind == "cache")
    n_dep = sum(1 for t in result.targets if t.kind == "dep")
    if fast:
        if n_cache:
            lines.append(
                f"[dark_orange3]🗑  Caches:[/dark_orange3]  [bold]{n_cache} dir(s)[/bold]")
        if n_dep:
            lines.append(
                f"[blue]📦 Deps:[/blue]     [bold]{n_dep} dir(s)[/bold]")
        lines.append("")
        lines.append(
            f"[bright_magenta]💎 Total:[/bright_magenta]    "
            f"[bold bright_white]{len(result.targets)} directories[/bold bright_white] "
            f"[dim](run without --fast to see sizes)[/dim]"
        )
    else:
        if result.cache_bytes:
            lines.append(
                f"[dark_orange3]🗑  Caches:[/dark_orange3]  [bold]{format_size(result.cache_bytes)}[/bold]"
            )
        if result.dep_bytes:
            lines.append(
                f"[blue]📦 Deps:[/blue]     [bold]{format_size(result.dep_bytes)}[/bold]"
            )
        lines.append("")
        lines.append(
            f"[bright_magenta]💎 Total:[/bright_magenta]    "
            f"[bold bright_white]{format_size(result.total_bytes)}[/bold bright_white]"
        )
    if dry_run:
        lines.append("")
        lines.append(
            "[dim italic]  ↑ Nothing was deleted (dry run)[/dim italic]")
    return Panel(
        "\n".join(lines),
        title="[bold bright_white]Summary[/bold bright_white]",
        border_style="bright_magenta",
        padding=(1, 3),
    )


# ── command ──────────────────────────────────────


@app.command()
def shatter(
    path: Path = typer.Argument(
        ".",
        help="Root directory to scan.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    cache: bool = typer.Option(
        False, "--cache", "-c", help="Only target build caches."),
    deps: bool = typer.Option(False, "--deps", "-d",
                              help="Only target dependency directories."),
    all_: bool = typer.Option(False, "--all", "-a",
                              help="Target both caches and deps."),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Scan only — don't delete anything."),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show per-project size breakdown grouped by project root."
    ),
    fast: bool = typer.Option(
        False, "--fast", "-f",
        help="Skip size calculation — instant results, no byte totals."
    ),
    yes: bool = typer.Option(False, "--yes", "-y",
                             help="Skip confirmation prompt."),
) -> None:
    """
    [bright_magenta]🔨 shatter[/bright_magenta] — Obliterate build caches & dependency bloat.

    Scans the given directory recursively. Stops descending past project roots
    (.git boundaries) to stay fast. Computes sizes in parallel.
    """
    _print_banner()

    # ── validate flags ───────────────────────────
    selected = sum([cache, deps, all_])
    if selected == 0:
        console.print(
            "[yellow]⚠  No target flag given.[/yellow]  "
            "Use [bold]--cache[/bold], [bold]--deps[/bold], or [bold]--all[/bold].\n"
        )
        raise typer.Exit(1)
    if selected > 1:
        console.print(
            "[red]✗  Please use only one of --cache, --deps, or --all.[/red]\n")
        raise typer.Exit(1)

    mode = "cache" if cache else ("deps" if deps else "all")

    # ── phase 1: walk ────────────────────────────
    with LiveSpinner("Scanning…", style="bright_magenta") as spinner:
        result: ScanResult | None = None

        def _do_scan() -> None:
            nonlocal result
            result = scan(
                root=path,
                mode=mode,
                console=console,
                fast=fast,
                on_visit=lambda p: spinner.set_status(f"Scanning  {p.name}"),
                on_size_progress=(
                    None if fast
                    else lambda t: spinner.set_status(
                        f"(sizing) {t.path.name}  {format_size(t.size_bytes)}"
                    )
                ),
            )

        scan_thread = threading.Thread(target=_do_scan)
        scan_thread.start()
        scan_thread.join()

    assert result is not None

    # ── empty ────────────────────────────────────
    if not result.targets:
        if path in result.skipped:
            console.print(
                Panel(
                    f"[bold yellow]🛡  Repo protected by .shatterignore[/bold yellow]\n"
                    f"[dim]{path} is shielded — nothing was scanned.[/dim]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    "[bright_green]✨ Nothing to clean — your project tree is spotless![/bright_green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )
        raise typer.Exit(0)

    # ── results ──────────────────────────────────
    console.print()
    table = _verbose_table(
        result, fast=fast) if verbose else _flat_table(result, fast=fast)
    console.print(table)
    console.print()
    console.print(_totals_panel(result, dry_run, fast=fast))
    console.print()

    if dry_run:
        raise typer.Exit(0)

    # ── confirm & delete ─────────────────────────
    if not yes:
        size_hint = "—" if fast else format_size(result.total_bytes)
        confirm = typer.confirm(
            f"🗑  Permanently delete {len(result.targets)} directories ({size_hint})?",
            default=False,
        )
        if not confirm:
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)

    console.print()
    with Progress(
        SpinnerColumn(style="bright_red"),
        TextColumn("[bold bright_red]Deleting[/bold bright_red]"),
        BarColumn(bar_width=40, style="dim red", complete_style="bright_red"),
        MofNCompleteColumn(),
        TextColumn("[dim]{task.fields[name]}[/dim]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("delete", total=len(result.targets), name="")

        def _on_progress(t: FoundTarget) -> None:
            progress.update(task, advance=1, name=t.path.name)

        removed = delete_targets(
            result.targets, console, on_progress=_on_progress)

    console.print(
        Panel(
            f"[bright_green]✅ Done![/bright_green]  Removed [bold]{removed}[/bold] "
            f"directories — freed "
            f"[bold bright_yellow]{format_size(result.total_bytes)}[/bold bright_yellow].",
            border_style="bright_green",
            padding=(1, 2),
        )
    )
