import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure current directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from smart_organizer import (
    SmartOrganizer,
    OrganizationStrategy,
    DuplicateStrategy,
    DEFAULT_CATEGORY_ICONS,
)

# Optional rich output support
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    HAS_RICH = True
    console = Console(force_terminal=True, legacy_windows=False)
except Exception:
    HAS_RICH = False
    console = None


def print_banner():
    banner_text = """
╔═══════════════════════════════════════════════════════════════════╗
║                   SMART FILE ORGANIZER v1.0                      ║
║     Intelligent Directory Categorizer, Deduplicator & Undo Engine ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    if HAS_RICH:
        console.print(f"[bold cyan]{banner_text}[/bold cyan]")
    else:
        print(banner_text)


def display_scan_results(scan_res):
    if HAS_RICH:
        console.print(Panel.fit(
            f"[bold green]Scan Summary for:[/bold green] [yellow]{scan_res.source_dir}[/yellow]\n"
            f"[bold]Total Files:[/bold] {scan_res.total_files} | [bold]Total Size:[/bold] {scan_res.total_size_human}",
            title="📂 Directory Scan", border_style="cyan"
        ))

        # Categories Table
        table = Table(title="📊 Category Breakdown", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Files", justify="right", style="green")
        table.add_column("Size", justify="right", style="yellow")
        table.add_column("Share", justify="right", style="blue")

        total_files = max(1, scan_res.total_files)
        for cat, count in sorted(scan_res.categories_count.items(), key=lambda x: x[1], reverse=True):
            size_h = scan_res.categories_size_human.get(cat, "0 B")
            pct = (count / total_files) * 100
            icon = DEFAULT_CATEGORY_ICONS.get(cat, "📁")
            table.add_row(f"{icon} {cat}", str(count), size_h, f"{pct:.1f}%")

        console.print(table)

        # File List preview (first 15 items)
        if scan_res.files:
            file_table = Table(title=f"📑 File Preview (Showing top {min(15, len(scan_res.files))} of {len(scan_res.files)})", show_header=True)
            file_table.add_column("File Name", style="white")
            file_table.add_column("Ext", style="yellow")
            file_table.add_column("Size", justify="right", style="green")
            file_table.add_column("Target Folder", style="cyan")

            for item in scan_res.files[:15]:
                file_table.add_row(item.filename, item.extension, item.size_human, item.target_folder_name)

            console.print(file_table)
    else:
        print(f"\nScan Summary for: {scan_res.source_dir}")
        print(f"Total Files: {scan_res.total_files} | Total Size: {scan_res.total_size_human}\n")
        print("Categories Breakdown:")
        for cat, count in scan_res.categories_count.items():
            print(f" - {cat}: {count} files ({scan_res.categories_size_human.get(cat, '0 B')})")


def display_organize_results(result):
    mode_str = "[DRY-RUN SIMULATION]" if result.is_dry_run else "[COMPLETED]"
    if HAS_RICH:
        console.print(Panel.fit(
            f"[bold green]{mode_str} Operation Summary[/bold green]\n"
            f"[bold]Batch ID:[/bold] {result.batch_id}\n"
            f"[bold]Processed:[/bold] {result.total_processed} files\n"
            f"[bold green]Successfully Organized:[/bold green] {result.successful_moves}\n"
            f"[bold yellow]Skipped:[/bold yellow] {result.skipped_moves}\n"
            f"[bold red]Failed:[/bold red] {result.failed_moves}",
            title="✨ Results", border_style="green" if result.failed_moves == 0 else "yellow"
        ))
    else:
        print(f"\n{mode_str} Operation Summary:")
        print(f"Batch ID: {result.batch_id}")
        print(f"Successfully Organized: {result.successful_moves}")
        print(f"Skipped: {result.skipped_moves}")
        print(f"Failed: {result.failed_moves}")


def run_interactive_menu():
    print_banner()
    organizer = SmartOrganizer()

    while True:
        if HAS_RICH:
            console.print("\n[bold cyan]Main Menu Options:[/bold cyan]")
            console.print("  [1] 📂 Scan & Preview Directory")
            console.print("  [2] 🚀 Organize Directory Now")
            console.print("  [3] 🧪 Dry-Run Simulation (Safe Preview)")
            console.print("  [4] ↩️  Undo Last Organization Operation")
            console.print("  [5] 🛠️  Generate Demo Test Sandbox (Safe Test Files)")
            console.print("  [6] 📜 View Transaction History")
            console.print("  [0] ❌ Exit")
            choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")
        else:
            print("\nMain Menu Options:")
            print("  [1] Scan & Preview Directory")
            print("  [2] Organize Directory Now")
            print("  [3] Dry-Run Simulation (Safe Preview)")
            print("  [4] Undo Last Organization Operation")
            print("  [5] Generate Demo Test Sandbox (Safe Test Files)")
            print("  [6] View Transaction History")
            print("  [0] Exit")
            choice = input("\nSelect an option [1-6, 0]: ").strip()

        if choice == "0":
            if HAS_RICH:
                console.print("[bold yellow]Exiting Smart File Organizer. Goodbye![/bold yellow]")
            else:
                print("Exiting Smart File Organizer. Goodbye!")
            break

        elif choice == "5":
            if HAS_RICH:
                parent = Prompt.ask("Enter directory to create Sandbox in (or press Enter for current folder)", default=str(Path.cwd()))
            else:
                parent = input("Enter directory (Enter for current folder): ").strip() or str(Path.cwd())
            
            sandbox = organizer.generate_demo_sandbox(parent)
            if HAS_RICH:
                console.print(f"[bold green]✓ Demo Sandbox created with 25+ test files at:[/bold green] [yellow]{sandbox}[/yellow]")
            else:
                print(f"Demo Sandbox created at: {sandbox}")

        elif choice in ["1", "2", "3"]:
            if HAS_RICH:
                target_dir = Prompt.ask("Enter target directory path")
            else:
                target_dir = input("Enter target directory path: ").strip()

            target_path = Path(target_dir).resolve()
            if not target_path.exists() or not target_path.is_dir():
                if HAS_RICH:
                    console.print(f"[bold red]Error: Directory does not exist: {target_dir}[/bold red]")
                else:
                    print(f"Error: Directory does not exist: {target_dir}")
                continue

            # Strategy Selection
            if HAS_RICH:
                console.print("\n[bold]Select Organization Strategy:[/bold]")
                console.print("  [1] By File Category (Documents, Images, Code, Audio, etc.)")
                console.print("  [2] By File Extension (.pdf, .png, .zip, etc.)")
                console.print("  [3] By Date (Year/Month - e.g. 2026/08-August)")
                console.print("  [4] By File Size (Tiny, Medium, Large, Huge)")
                strat_choice = Prompt.ask("Strategy", choices=["1", "2", "3", "4"], default="1")
            else:
                print("\nStrategies: [1] Category [2] Extension [3] Date [4] Size")
                strat_choice = input("Select strategy [1-4]: ").strip() or "1"

            strat_map = {
                "1": OrganizationStrategy.BY_CATEGORY,
                "2": OrganizationStrategy.BY_EXTENSION,
                "3": OrganizationStrategy.BY_DATE_YEAR_MONTH,
                "4": OrganizationStrategy.BY_SIZE,
            }
            strategy = strat_map.get(strat_choice, OrganizationStrategy.BY_CATEGORY)

            if choice == "1":
                scan_res = organizer.scan_directory(str(target_path), strategy=strategy)
                display_scan_results(scan_res)
            elif choice == "3":
                res = organizer.organize(str(target_path), strategy=strategy, dry_run=True)
                display_organize_results(res)
            elif choice == "2":
                # Duplicate Strategy
                if HAS_RICH:
                    console.print("\n[bold]Select Duplicate Resolution Strategy:[/bold]")
                    console.print("  [1] Sequence Number (e.g. file (1).pdf)")
                    console.print("  [2] Timestamp (e.g. file_20260824_193000.pdf)")
                    console.print("  [3] Move to _Duplicates/ Folder")
                    console.print("  [4] Skip Conflicting Files")
                    dup_choice = Prompt.ask("Duplicate Strategy", choices=["1", "2", "3", "4"], default="1")
                else:
                    dup_choice = input("Duplicate Strategy [1] Sequence [2] Timestamp [3] Duplicates Folder [4] Skip: ").strip() or "1"

                dup_map = {
                    "1": DuplicateStrategy.RENAME_SEQUENCE,
                    "2": DuplicateStrategy.RENAME_TIMESTAMP,
                    "3": DuplicateStrategy.MOVE_TO_DUPLICATES,
                    "4": DuplicateStrategy.SKIP,
                }
                dup_strat = dup_map.get(dup_choice, DuplicateStrategy.RENAME_SEQUENCE)

                confirm = True
                if HAS_RICH:
                    confirm = Confirm.ask(f"Ready to organize files in [yellow]{target_path}[/yellow]?", default=True)
                if confirm:
                    res = organizer.organize(str(target_path), strategy=strategy, duplicate_strategy=dup_strat, dry_run=False)
                    display_organize_results(res)

        elif choice == "4":
            if HAS_RICH:
                target_dir = Prompt.ask("Enter directory to undo (leave empty for most recent global operation)", default="")
            else:
                target_dir = input("Enter directory to undo (leave empty for last): ").strip()

            target_arg = target_dir if target_dir else None
            undo_res = organizer.undo(source_dir=target_arg)
            if undo_res["success"]:
                if HAS_RICH:
                    console.print(f"[bold green]✓ {undo_res['message']}[/bold green]")
                else:
                    print(f"✓ {undo_res['message']}")
            else:
                if HAS_RICH:
                    console.print(f"[bold red]✗ {undo_res['message']}[/bold red]")
                else:
                    print(f"✗ {undo_res['message']}")

        elif choice == "6":
            history_list = organizer.history.list_history()
            if not history_list:
                if HAS_RICH:
                    console.print("[yellow]No history records found.[/yellow]")
                else:
                    print("No history records found.")
            else:
                if HAS_RICH:
                    h_table = Table(title="📜 Operation History", show_header=True)
                    h_table.add_column("Batch ID", style="cyan")
                    h_table.add_column("Timestamp", style="white")
                    h_table.add_column("Directory", style="yellow")
                    h_table.add_column("Files", justify="right", style="green")
                    h_table.add_column("Status", style="magenta")

                    for item in history_list:
                        status = "[bold red]UNDONE[/bold red]" if item["undone"] else "[bold green]ACTIVE[/bold green]"
                        h_table.add_row(item["batch_id"], item["timestamp"][:19], item["source_dir"], str(item["successful_moves"]), status)
                    console.print(h_table)
                else:
                    print("\nOperation History:")
                    for item in history_list:
                        status = "UNDONE" if item["undone"] else "ACTIVE"
                        print(f" - {item['batch_id']} | {item['timestamp'][:19]} | {item['source_dir']} | {item['successful_moves']} files | {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Smart File Organizer - Organize, categorize, deduplicate, and manage files automatically."
    )
    parser.add_argument("--path", "-p", help="Target directory path to scan or organize")
    parser.add_argument("--scan", "-s", action="store_true", help="Scan directory and show category summary")
    parser.add_argument("--organize", "-o", action="store_true", help="Execute organization on target directory")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Simulate organization without moving any files")
    parser.add_argument("--undo", "-u", action="store_true", help="Undo the last organization operation")
    parser.add_argument("--batch-id", help="Specific Batch ID to undo")
    parser.add_argument("--demo", action="store_true", help="Generate a demo sandbox folder with assorted test files")
    parser.add_argument(
        "--mode", "-m",
        choices=["category", "extension", "date", "size"],
        default="category",
        help="Organization strategy mode",
    )
    parser.add_argument(
        "--duplicates",
        choices=["sequence", "timestamp", "duplicates_folder", "skip", "overwrite"],
        default="sequence",
        help="Duplicate resolution strategy",
    )
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan subdirectories recursively")
    parser.add_argument("--clean-empty", action="store_true", help="Clean empty subfolders after organizing")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive menu mode")

    args = parser.parse_args()

    # If no arguments provided or interactive flag set, launch interactive UI
    if len(sys.argv) == 1 or args.interactive:
        run_interactive_menu()
        return

    organizer = SmartOrganizer()

    if args.demo:
        parent_dir = args.path if args.path else str(Path.cwd())
        sandbox = organizer.generate_demo_sandbox(parent_dir)
        print(f"✓ Demo sandbox created at: {sandbox}")
        return

    if args.undo:
        res = organizer.undo(batch_id=args.batch_id, source_dir=args.path)
        if res["success"]:
            print(f"✓ {res['message']}")
        else:
            print(f"✗ {res['message']}")
        return

    if not args.path:
        print("Error: Please provide --path <directory> or run without arguments for interactive mode.")
        sys.exit(1)

    target_path = Path(args.path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Target path does not exist or is not a directory: {args.path}")
        sys.exit(1)

    strategy_map = {
        "category": OrganizationStrategy.BY_CATEGORY,
        "extension": OrganizationStrategy.BY_EXTENSION,
        "date": OrganizationStrategy.BY_DATE_YEAR_MONTH,
        "size": OrganizationStrategy.BY_SIZE,
    }
    strategy = strategy_map.get(args.mode, OrganizationStrategy.BY_CATEGORY)

    dup_map = {
        "sequence": DuplicateStrategy.RENAME_SEQUENCE,
        "timestamp": DuplicateStrategy.RENAME_TIMESTAMP,
        "duplicates_folder": DuplicateStrategy.MOVE_TO_DUPLICATES,
        "skip": DuplicateStrategy.SKIP,
        "overwrite": DuplicateStrategy.OVERWRITE,
    }
    dup_strategy = dup_map.get(args.duplicates, DuplicateStrategy.RENAME_SEQUENCE)

    if args.scan:
        scan_res = organizer.scan_directory(
            source_dir_path=str(target_path),
            recursive=args.recursive,
            strategy=strategy,
        )
        display_scan_results(scan_res)

    elif args.organize or args.dry_run:
        res = organizer.organize(
            source_dir_path=str(target_path),
            strategy=strategy,
            duplicate_strategy=dup_strategy,
            recursive=args.recursive,
            dry_run=args.dry_run,
            clean_empty_folders=args.clean_empty,
        )
        display_organize_results(res)
    else:
        # Default action when path is given without specific action flag: scan
        scan_res = organizer.scan_directory(
            source_dir_path=str(target_path),
            recursive=args.recursive,
            strategy=strategy,
        )
        display_scan_results(scan_res)


if __name__ == "__main__":
    main()
