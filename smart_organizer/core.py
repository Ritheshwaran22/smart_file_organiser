"""
Core Engine for Smart File Organizer
Provides scanning, classification, preview, organization, duplicate resolution, undo, and sandbox generation.
"""

import os
import shutil
import hashlib
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
import uuid

from .config import (
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ICONS,
    DEFAULT_CATEGORY_COLORS,
    DEFAULT_IGNORE_PATTERNS,
    OrganizationStrategy,
    DuplicateStrategy,
)
from .history import TransactionHistory, OperationRecord, FileMoveRecord

# Configure standard logger
logger = logging.getLogger("SmartOrganizer.Core")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def format_file_size(size_bytes: int) -> str:
    """Format bytes into a readable string representation."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def calculate_file_hash(file_path: Path, max_size_bytes: int = 10 * 1024 * 1024) -> Optional[str]:
    """Calculate MD5 hash of a file for duplicate content verification."""
    try:
        if file_path.stat().st_size > max_size_bytes:
            # For huge files, hash the first 10MB only for speed
            md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                md5.update(f.read(max_size_bytes))
            return md5.hexdigest()
        else:
            md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    md5.update(chunk)
            return md5.hexdigest()
    except Exception as e:
        logger.debug(f"Could not calculate hash for {file_path}: {e}")
        return None


@dataclass
class FileItem:
    """Represents a scanned file with its classification and proposed target."""
    path: str
    filename: str
    extension: str
    size_bytes: int
    size_human: str
    modified_time: str
    category: str
    category_icon: str
    category_color: str
    target_folder_name: str
    target_path: str
    is_duplicate: bool = False
    new_filename: Optional[str] = None
    file_hash: Optional[str] = None


@dataclass
class ScanResult:
    """Result of scanning a directory."""
    source_dir: str
    total_files: int
    total_size_bytes: int
    total_size_human: str
    categories_count: Dict[str, int]
    categories_size: Dict[str, int]
    categories_size_human: Dict[str, str]
    extensions_count: Dict[str, int]
    files: List[FileItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class OrganizationResult:
    """Result of executing an organization batch."""
    batch_id: str
    timestamp: str
    source_dir: str
    strategy: str
    duplicate_strategy: str
    total_processed: int
    successful_moves: int
    failed_moves: int
    skipped_moves: int
    created_folders: List[str]
    errors: List[Dict[str, str]]
    files: List[Dict[str, Any]]
    activity_logs: List[str]
    is_dry_run: bool = False


class SmartOrganizer:
    """
    Main file organization engine.
    Supports scanning, categorization, dry-run simulation, execution, and rollback.
    """

    def __init__(
        self,
        categories: Optional[Dict[str, List[str]]] = None,
        category_icons: Optional[Dict[str, str]] = None,
        category_colors: Optional[Dict[str, str]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        history: Optional[TransactionHistory] = None,
    ):
        self.categories = categories or dict(DEFAULT_CATEGORIES)
        self.category_icons = category_icons or dict(DEFAULT_CATEGORY_ICONS)
        self.category_colors = category_colors or dict(DEFAULT_CATEGORY_COLORS)
        self.ignore_patterns = ignore_patterns or set(DEFAULT_IGNORE_PATTERNS)
        self.history = history or TransactionHistory()
        self._memory_logs: List[str] = []

    def _log(self, message: str, level: str = "INFO"):
        """Internal logger that also stores logs in memory for API/UI response."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self._memory_logs.append(log_entry)
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)

    def clear_memory_logs(self):
        """Clear session memory logs."""
        self._memory_logs = []

    def get_memory_logs(self) -> List[str]:
        """Return captured logs."""
        return list(self._memory_logs)

    def get_category_for_extension(
        self, extension: str, custom_rules: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """Determine category for a file extension."""
        ext_clean = extension.lower().lstrip(".")
        if not ext_clean:
            return "Others"

        # Check custom rules first
        if custom_rules:
            for cat_name, ext_list in custom_rules.items():
                if ext_clean in [e.lower().lstrip(".") for e in ext_list]:
                    return cat_name

        # Check default category mapping
        for cat_name, ext_list in self.categories.items():
            if ext_clean in [e.lower().lstrip(".") for e in ext_list]:
                return cat_name

        return "Others"

    def compute_target_folder(
        self,
        file_path: Path,
        strategy: OrganizationStrategy,
        custom_rules: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """Compute the destination subfolder name based on the chosen strategy."""
        ext = file_path.suffix.lower().lstrip(".")
        
        if strategy == OrganizationStrategy.BY_CATEGORY:
            return self.get_category_for_extension(ext, custom_rules)

        elif strategy == OrganizationStrategy.BY_EXTENSION:
            return ext.upper() + " Files" if ext else "No Extension"

        elif strategy == OrganizationStrategy.BY_DATE_YEAR_MONTH:
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                month_name = mtime.strftime("%B")
                return f"{mtime.year}/{mtime.strftime('%m')}-{month_name}"
            except Exception:
                return "Unknown Date"

        elif strategy == OrganizationStrategy.BY_DATE_YEAR:
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                return str(mtime.year)
            except Exception:
                return "Unknown Year"

        elif strategy == OrganizationStrategy.BY_SIZE:
            try:
                size_bytes = file_path.stat().st_size
                if size_bytes < 1024 * 1024:
                    return "Tiny (< 1MB)"
                elif size_bytes < 50 * 1024 * 1024:
                    return "Medium (1MB - 50MB)"
                elif size_bytes < 1024 * 1024 * 1024:
                    return "Large (50MB - 1GB)"
                else:
                    return "Huge (> 1GB)"
            except Exception:
                return "Unknown Size"

        elif strategy == OrganizationStrategy.CUSTOM_RULES:
            return self.get_category_for_extension(ext, custom_rules)

        return "Organized"

    def is_ignored(self, path: Path, source_dir: Path) -> bool:
        """Check if file or directory should be ignored."""
        # Check system / hidden files
        if path.name.startswith(".") and path.name not in [".pdf", ".png", ".txt"]:
            return True
        
        # Check exact name against ignore patterns
        if path.name in self.ignore_patterns:
            return True

        # Check parent parts
        for part in path.parts:
            if part in self.ignore_patterns:
                return True

        return False

    def scan_directory(
        self,
        source_dir_path: str,
        recursive: bool = False,
        strategy: OrganizationStrategy = OrganizationStrategy.BY_CATEGORY,
        custom_rules: Optional[Dict[str, List[str]]] = None,
        ignore_patterns: Optional[Set[str]] = None,
    ) -> ScanResult:
        """
        Scan directory and detect all files, extensions, categories, and proposed targets.
        """
        self.clear_memory_logs()
        source_dir = Path(source_dir_path).resolve()
        
        if not source_dir.exists():
            err = f"Directory not found: {source_dir}"
            self._log(err, "ERROR")
            return ScanResult(
                source_dir=str(source_dir),
                total_files=0,
                total_size_bytes=0,
                total_size_human="0 B",
                categories_count={},
                categories_size={},
                categories_size_human={},
                extensions_count={},
                files=[],
                errors=[err],
            )

        if not source_dir.is_dir():
            err = f"Path is not a directory: {source_dir}"
            self._log(err, "ERROR")
            return ScanResult(
                source_dir=str(source_dir),
                total_files=0,
                total_size_bytes=0,
                total_size_human="0 B",
                categories_count={},
                categories_size={},
                categories_size_human={},
                extensions_count={},
                files=[],
                errors=[err],
            )

        effective_ignores = (self.ignore_patterns | ignore_patterns) if ignore_patterns else self.ignore_patterns

        self._log(f"Starting scan of '{source_dir}' (recursive={recursive}, strategy={strategy.value})")

        files: List[FileItem] = []
        categories_count: Dict[str, int] = {}
        categories_size: Dict[str, int] = {}
        extensions_count: Dict[str, int] = {}
        errors: List[str] = []
        total_size = 0

        # Scan iterator
        try:
            if recursive:
                file_iterator = [p for p in source_dir.rglob("*") if p.is_file()]
            else:
                file_iterator = [p for p in source_dir.iterdir() if p.is_file()]
        except PermissionError as e:
            err = f"Permission denied while reading directory: {e}"
            self._log(err, "ERROR")
            return ScanResult(
                source_dir=str(source_dir),
                total_files=0,
                total_size_bytes=0,
                total_size_human="0 B",
                categories_count={},
                categories_size={},
                categories_size_human={},
                extensions_count={},
                files=[],
                errors=[err],
            )
        except Exception as e:
            err = f"Error scanning directory: {e}"
            self._log(err, "ERROR")
            return ScanResult(
                source_dir=str(source_dir),
                total_files=0,
                total_size_bytes=0,
                total_size_human="0 B",
                categories_count={},
                categories_size={},
                categories_size_human={},
                extensions_count={},
                files=[],
                errors=[err],
            )

        for file_path in file_iterator:
            try:
                if self.is_ignored(file_path, source_dir):
                    continue

                stat = file_path.stat()
                size_bytes = stat.st_size
                total_size += size_bytes
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                raw_ext = file_path.suffix.lower().lstrip(".")
                ext_display = f".{raw_ext}" if raw_ext else "(none)"
                extensions_count[ext_display] = extensions_count.get(ext_display, 0) + 1

                target_folder = self.compute_target_folder(file_path, strategy, custom_rules)
                category = self.get_category_for_extension(raw_ext, custom_rules)
                
                # Check if file is already inside target folder (to avoid redundant move)
                target_full_dir = source_dir / target_folder
                target_dest_file = target_full_dir / file_path.name
                
                # Track category aggregates
                categories_count[target_folder] = categories_count.get(target_folder, 0) + 1
                categories_size[target_folder] = categories_size.get(target_folder, 0) + size_bytes

                icon = self.category_icons.get(category, self.category_icons.get("Others", "📁"))
                color = self.category_colors.get(category, self.category_colors.get("Others", "#94a3b8"))

                item = FileItem(
                    path=str(file_path),
                    filename=file_path.name,
                    extension=ext_display,
                    size_bytes=size_bytes,
                    size_human=format_file_size(size_bytes),
                    modified_time=mtime,
                    category=category,
                    category_icon=icon,
                    category_color=color,
                    target_folder_name=target_folder,
                    target_path=str(target_dest_file),
                    is_duplicate=False,
                )
                files.append(item)

            except PermissionError:
                err = f"Permission denied for file: {file_path.name}"
                errors.append(err)
                self._log(err, "WARNING")
            except Exception as e:
                err = f"Could not process file {file_path.name}: {e}"
                errors.append(err)
                self._log(err, "WARNING")

        categories_size_human = {
            cat: format_file_size(sz) for cat, sz in categories_size.items()
        }

        self._log(
            f"Scan completed: found {len(files)} files ({format_file_size(total_size)}) across {len(categories_count)} categories."
        )

        return ScanResult(
            source_dir=str(source_dir),
            total_files=len(files),
            total_size_bytes=total_size,
            total_size_human=format_file_size(total_size),
            categories_count=categories_count,
            categories_size=categories_size,
            categories_size_human=categories_size_human,
            extensions_count=extensions_count,
            files=files,
            errors=errors,
        )

    def resolve_duplicate_filename(
        self,
        dest_dir: Path,
        source_file: Path,
        duplicate_strategy: DuplicateStrategy,
        occupied_names: Set[str],
    ) -> Tuple[Path, bool]:
        """
        Determine new destination path according to duplicate strategy.
        Returns (final_path, was_renamed).
        """
        target_path = dest_dir / source_file.name
        stem = source_file.stem
        ext = source_file.suffix

        # Check if already exists on disk OR in current batch occupied names
        conflict_exists = target_path.exists() or (str(target_path.resolve()) in occupied_names)

        if not conflict_exists:
            return target_path, False

        # If it already points to the exact same file on disk (i.e. source == target), no rename needed
        if target_path.exists() and source_file.resolve() == target_path.resolve():
            return target_path, False

        if duplicate_strategy == DuplicateStrategy.OVERWRITE:
            return target_path, False

        elif duplicate_strategy == DuplicateStrategy.SKIP:
            return target_path, False

        elif duplicate_strategy == DuplicateStrategy.MOVE_TO_DUPLICATES:
            dup_dir = dest_dir.parent / "_Duplicates" if dest_dir.parent else dest_dir / "_Duplicates"
            dup_dir.mkdir(parents=True, exist_ok=True)
            # Find safe name inside _Duplicates
            seq = 1
            dup_target = dup_dir / source_file.name
            while dup_target.exists() or (str(dup_target.resolve()) in occupied_names):
                dup_target = dup_dir / f"{stem}_dup{seq}{ext}"
                seq += 1
            return dup_target, True

        elif duplicate_strategy == DuplicateStrategy.RENAME_TIMESTAMP:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            candidate = dest_dir / f"{stem}_{ts}{ext}"
            seq = 1
            while candidate.exists() or (str(candidate.resolve()) in occupied_names):
                candidate = dest_dir / f"{stem}_{ts}_{seq}{ext}"
                seq += 1
            return candidate, True

        else: # Default: RENAME_SEQUENCE e.g. "report (1).pdf"
            seq = 1
            candidate = dest_dir / f"{stem} ({seq}){ext}"
            while candidate.exists() or (str(candidate.resolve()) in occupied_names):
                seq += 1
                candidate = dest_dir / f"{stem} ({seq}){ext}"
            return candidate, True

    def organize(
        self,
        source_dir_path: str,
        strategy: OrganizationStrategy = OrganizationStrategy.BY_CATEGORY,
        duplicate_strategy: DuplicateStrategy = DuplicateStrategy.RENAME_SEQUENCE,
        recursive: bool = False,
        dry_run: bool = False,
        clean_empty_folders: bool = False,
        custom_rules: Optional[Dict[str, List[str]]] = None,
        ignore_patterns: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> OrganizationResult:
        """
        Organize directory with full error handling, duplicate resolution, logging, and undo history recording.
        """
        self.clear_memory_logs()
        batch_id = f"batch_{uuid.uuid4().hex[:10]}"
        timestamp_str = datetime.now().isoformat()
        source_dir = Path(source_dir_path).resolve()

        self._log(
            f"{'[DRY RUN] ' if dry_run else ''}Starting organization for '{source_dir}' "
            f"[Strategy: {strategy.value}, Duplicate Mode: {duplicate_strategy.value}, Recursive: {recursive}]"
        )

        scan_result = self.scan_directory(
            source_dir_path=str(source_dir),
            recursive=recursive,
            strategy=strategy,
            custom_rules=custom_rules,
            ignore_patterns=ignore_patterns,
        )

        if scan_result.errors and not scan_result.files:
            return OrganizationResult(
                batch_id=batch_id,
                timestamp=timestamp_str,
                source_dir=str(source_dir),
                strategy=strategy.value,
                duplicate_strategy=duplicate_strategy.value,
                total_processed=0,
                successful_moves=0,
                failed_moves=0,
                skipped_moves=0,
                created_folders=[],
                errors=[{"file": "Scan", "error": e} for e in scan_result.errors],
                files=[],
                activity_logs=self.get_memory_logs(),
                is_dry_run=dry_run,
            )

        successful_moves = 0
        failed_moves = 0
        skipped_moves = 0
        created_folders_set: Set[str] = set()
        errors_list: List[Dict[str, str]] = []
        file_records: List[FileMoveRecord] = []
        file_output_list: List[Dict[str, Any]] = []

        # Keep track of planned destination paths to prevent collisions within same batch
        occupied_destinations: Set[str] = set()

        total_files = len(scan_result.files)

        for idx, item in enumerate(scan_result.files, 1):
            src_path = Path(item.path)
            target_folder_name = item.target_folder_name
            dest_dir = source_dir / target_folder_name

            # Check if file is already in correct place
            if src_path.parent.resolve() == dest_dir.resolve():
                skipped_moves += 1
                self._log(f"Skipped (already organized): {src_path.name}")
                continue

            try:
                final_dest_path, was_renamed = self.resolve_duplicate_filename(
                    dest_dir=dest_dir,
                    source_file=src_path,
                    duplicate_strategy=duplicate_strategy,
                    occupied_names=occupied_destinations,
                )

                if duplicate_strategy == DuplicateStrategy.SKIP and final_dest_path.exists() and not was_renamed:
                    skipped_moves += 1
                    self._log(f"Skipped duplicate: {src_path.name}")
                    continue

                occupied_destinations.add(str(final_dest_path.resolve()))

                # Execute Move if not dry run
                if not dry_run:
                    # Create target directory safely
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    created_folders_set.add(str(dest_dir))

                    # Move file
                    shutil.move(str(src_path), str(final_dest_path))
                    status_msg = "Moved" if not was_renamed else f"Moved & Renamed -> {final_dest_path.name}"
                    self._log(f"{status_msg}: {src_path.name} -> {target_folder_name}/")
                else:
                    status_msg = "[DRY-RUN] Will move" if not was_renamed else f"[DRY-RUN] Will move & rename -> {final_dest_path.name}"
                    self._log(f"{status_msg}: {src_path.name} -> {target_folder_name}/")
                    created_folders_set.add(str(dest_dir))

                successful_moves += 1

                # Record transaction
                rec = FileMoveRecord(
                    original_path=str(src_path),
                    destination_path=str(final_dest_path),
                    filename=src_path.name,
                    size_bytes=item.size_bytes,
                    category=item.category,
                    file_hash=item.file_hash,
                    renamed=was_renamed,
                    status="COMPLETED" if not dry_run else "SIMULATED",
                )
                file_records.append(rec)

                file_output_list.append({
                    "original_path": str(src_path),
                    "destination_path": str(final_dest_path),
                    "filename": src_path.name,
                    "new_filename": final_dest_path.name if was_renamed else None,
                    "target_folder": target_folder_name,
                    "size_human": item.size_human,
                    "category": item.category,
                    "category_icon": item.category_icon,
                    "renamed": was_renamed,
                    "status": "SUCCESS",
                })

            except PermissionError as pe:
                failed_moves += 1
                err_str = f"Permission denied for '{src_path.name}': {pe}"
                errors_list.append({"file": src_path.name, "error": err_str})
                self._log(err_str, "ERROR")
            except OSError as oe:
                failed_moves += 1
                err_str = f"OS Error moving '{src_path.name}': {oe}"
                errors_list.append({"file": src_path.name, "error": err_str})
                self._log(err_str, "ERROR")
            except Exception as e:
                failed_moves += 1
                err_str = f"Unexpected error with '{src_path.name}': {e}"
                errors_list.append({"file": src_path.name, "error": err_str})
                self._log(err_str, "ERROR")

            if progress_callback:
                progress_callback(idx, total_files, src_path.name)

        # Optionally clean empty subfolders if requested
        if clean_empty_folders and not dry_run:
            self._cleanup_empty_dirs(source_dir)

        # Record in persistent history if this was an actual execution with moves
        if not dry_run and successful_moves > 0:
            op_record = OperationRecord(
                batch_id=batch_id,
                timestamp=timestamp_str,
                source_dir=str(source_dir),
                strategy=strategy.value,
                duplicate_strategy=duplicate_strategy.value,
                recursive=recursive,
                total_files=total_files,
                successful_moves=successful_moves,
                failed_moves=failed_moves,
                files=file_records,
                undone=False,
            )
            self.history.record_operation(op_record)

        self._log(
            f"Operation finished. Successful: {successful_moves}, Skipped: {skipped_moves}, Failed: {failed_moves}."
        )

        return OrganizationResult(
            batch_id=batch_id,
            timestamp=timestamp_str,
            source_dir=str(source_dir),
            strategy=strategy.value,
            duplicate_strategy=duplicate_strategy.value,
            total_processed=total_files,
            successful_moves=successful_moves,
            failed_moves=failed_moves,
            skipped_moves=skipped_moves,
            created_folders=list(created_folders_set),
            errors=errors_list,
            files=file_output_list,
            activity_logs=self.get_memory_logs(),
            is_dry_run=dry_run,
        )

    def undo(
        self,
        batch_id: Optional[str] = None,
        source_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reverse an organization operation. Moves files back to original paths and removes empty created folders.
        """
        self.clear_memory_logs()
        
        if batch_id:
            op = self.history.get_operation_by_id(batch_id)
        else:
            op = self.history.get_last_active_operation(source_dir)

        if not op:
            err = "No reversible operation found in history."
            self._log(err, "WARNING")
            return {
                "success": False,
                "message": err,
                "restored_count": 0,
                "failed_count": 0,
                "errors": [err],
                "activity_logs": self.get_memory_logs(),
            }

        if op.undone:
            err = f"Operation {op.batch_id} has already been undone."
            self._log(err, "WARNING")
            return {
                "success": False,
                "message": err,
                "restored_count": 0,
                "failed_count": 0,
                "errors": [err],
                "activity_logs": self.get_memory_logs(),
            }

        self._log(f"Starting rollback for batch '{op.batch_id}' ({len(op.files)} files recorded)...")

        restored_count = 0
        failed_count = 0
        errors: List[str] = []
        folders_to_check: Set[Path] = set()

        for file_rec in op.files:
            if file_rec.status != "COMPLETED":
                continue

            current_path = Path(file_rec.destination_path)
            orig_path = Path(file_rec.original_path)

            if not current_path.exists():
                err = f"File missing during rollback: {current_path}"
                errors.append(err)
                failed_count += 1
                self._log(err, "WARNING")
                continue

            try:
                # Ensure original parent directory exists
                orig_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check for collision at original location
                final_orig_path = orig_path
                if orig_path.exists() and orig_path.resolve() != current_path.resolve():
                    seq = 1
                    stem = orig_path.stem
                    ext = orig_path.suffix
                    while final_orig_path.exists():
                        final_orig_path = orig_path.parent / f"{stem}_restored{seq}{ext}"
                        seq += 1

                shutil.move(str(current_path), str(final_orig_path))
                restored_count += 1
                self._log(f"Restored: {current_path.name} -> {final_orig_path}")
                folders_to_check.add(current_path.parent)

            except Exception as e:
                err = f"Failed to restore {current_path.name}: {e}"
                errors.append(err)
                failed_count += 1
                self._log(err, "ERROR")

        # Clean up empty category folders left behind
        cleaned_folders = 0
        for folder in folders_to_check:
            try:
                if folder.exists() and folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()
                    cleaned_folders += 1
                    self._log(f"Removed empty folder: {folder.name}")
            except Exception as e:
                self._log(f"Could not remove folder {folder}: {e}", "WARNING")

        self.history.mark_undone(op.batch_id)
        msg = f"Rollback complete: {restored_count} files restored to original locations ({cleaned_folders} empty folders removed)."
        self._log(msg)

        return {
            "success": True,
            "batch_id": op.batch_id,
            "message": msg,
            "restored_count": restored_count,
            "failed_count": failed_count,
            "cleaned_folders": cleaned_folders,
            "errors": errors,
            "activity_logs": self.get_memory_logs(),
        }

    def _cleanup_empty_dirs(self, root_dir: Path):
        """Recursively remove empty subdirectories inside root_dir."""
        for dirpath, dirnames, filenames in os.walk(str(root_dir), topdown=False):
            if Path(dirpath).resolve() == root_dir.resolve():
                continue
            p = Path(dirpath)
            try:
                if not any(p.iterdir()):
                    p.rmdir()
                    self._log(f"Cleaned up empty directory: {p.name}")
            except Exception:
                pass

    def generate_demo_sandbox(self, target_parent_dir: Optional[str] = None) -> Path:
        """
        Create a test directory populated with 25+ diverse dummy files (including duplicates)
        for instant safe testing of all features.
        """
        parent = Path(target_parent_dir) if target_parent_dir else Path.cwd()
        sandbox_dir = parent / f"SmartOrganizer_Demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        sample_files = [
            # Documents
            ("Annual_Financial_Report.pdf", b"%PDF-1.4 Mock Financial Report Content"),
            ("Employee_Handbook.docx", b"Mock Word Document: Welcome to the company handbook."),
            ("Meeting_Notes_2026.txt", b"Notes from strategy sync: 1. Deploy file organizer 2. Review UI"),
            ("README.md", b"# Smart Organizer Sandbox\nSample readme file."),
            ("Terms_and_Conditions.rtf", b"{\\rtf1\\ansi Mock RTF Document}"),
            # Images
            ("Company_Logo_HighRes.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR Mock PNG Header Data"),
            ("Vacation_Photo_Hawaii.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF Mock JPEG Data"),
            ("Avatar_Profile.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 Mock WebP Data"),
            ("System_Icon.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><circle r='10'/></svg>"),
            # Audio & Video
            ("Podcast_Episode_42.mp3", b"ID3\x03\x00\x00 Mock MP3 Audio Stream Data"),
            ("Voice_Memo_Recorded.wav", b"RIFF\x24\x08\x00\x00WAVEfmt Mock WAV Audio"),
            ("Product_Demo_Walkthrough.mp4", b"\x00\x00\x00\x18ftypmp42 Mock MP4 Video Container"),
            ("Webinar_Recording.mkv", b"\x1a\x45\xdf\xa3 Mock MKV Video Data"),
            # Archives
            ("Project_Source_Backup.zip", b"PK\x03\x04 Mock ZIP Archive Header"),
            ("Old_Database_Dump.tar.gz", b"\x1f\x8b\x08 Mock GZ Archive Header"),
            ("Installation_Package.7z", b"7z\xbc\xaf\x27\x1c Mock 7z Archive"),
            # Spreadsheets & Presentations
            ("Q3_Sales_Forecast.xlsx", b"PK\x03\x04 Mock Excel Spreadsheet XML package"),
            ("Customer_Leads_Export.csv", b"id,name,email,plan\n1,Alice,alice@test.com,Pro\n2,Bob,bob@test.com,Enterprise"),
            ("Investor_Pitch_Deck.pptx", b"PK\x03\x04 Mock PowerPoint Presentation"),
            # Code & Dev
            ("automation_script.py", b"import os\nprint('Smart File Organizer running!')\n"),
            ("dashboard_ui.html", b"<!DOCTYPE html><html><head><title>App</title></head><body><h1>Hello</h1></body></html>"),
            ("styles.css", b":root { --primary: #3b82f6; } body { margin: 0; font-family: sans-serif; }"),
            ("api_client.js", b"async function fetchFiles() { const res = await fetch('/api/scan'); return res.json(); }"),
            ("database_schema.sql", b"CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50));"),
            # Executables & Books
            ("Setup_Installer.exe", b"MZ\x90\x00 Mock Executable Binary Header"),
            ("Python_Deep_Learning_Guide.epub", b"PK\x03\x04 Mock EPUB eBook Content"),
            # Duplicate files (same filename or content to test collision handling)
            ("Annual_Financial_Report.pdf", b"%PDF-1.4 Mock Financial Report Content (v2)"),
            ("Vacation_Photo_Hawaii.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF Mock JPEG Data copy"),
        ]

        created_count = 0
        for filename, content in sample_files:
            file_path = sandbox_dir / filename
            # If already exists, create with duplicate suffix or overwrite as specified
            try:
                with open(file_path, "wb") as f:
                    f.write(content)
                created_count += 1
            except Exception as e:
                logger.warning(f"Could not create sample file {filename}: {e}")

        logger.info(f"Generated demo sandbox folder with {created_count} files at: {sandbox_dir}")
        return sandbox_dir
