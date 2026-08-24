"""
Transaction History and Undo Ledger for Smart File Organizer
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("SmartOrganizer.History")

@dataclass
class FileMoveRecord:
    original_path: str
    destination_path: str
    filename: str
    size_bytes: int
    category: str
    file_hash: Optional[str] = None
    renamed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "COMPLETED"  # COMPLETED, FAILED, UNDONE

@dataclass
class OperationRecord:
    batch_id: str
    timestamp: str
    source_dir: str
    strategy: str
    duplicate_strategy: str
    recursive: bool
    total_files: int
    successful_moves: int
    failed_moves: int
    files: List[FileMoveRecord] = field(default_factory=list)
    undone: bool = False
    undone_timestamp: Optional[str] = None

class TransactionHistory:
    """Manages persistent transaction records to enable reversible file operations."""

    def __init__(self, history_file: Optional[Path] = None):
        if history_file is None:
            # Default history file in user's home directory or local directory
            self.history_file = Path.home() / ".smart_file_organizer_history.json"
        else:
            self.history_file = Path(history_file)
        
        self.history: List[OperationRecord] = []
        self._load()

    def _load(self):
        """Load history from JSON file."""
        if not self.history_file.exists():
            self.history = []
            return
        
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.history = []
                for item in data:
                    files = [FileMoveRecord(**f_rec) for f_rec in item.get("files", [])]
                    item_copy = dict(item)
                    item_copy["files"] = files
                    self.history.append(OperationRecord(**item_copy))
        except Exception as e:
            logger.warning(f"Could not load transaction history from {self.history_file}: {e}")
            self.history = []

    def _save(self):
        """Save history to JSON file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for op in self.history:
                op_dict = asdict(op)
                data.append(op_dict)
            
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transaction history to {self.history_file}: {e}")

    def record_operation(self, operation: OperationRecord) -> None:
        """Record a completed batch operation."""
        self.history.append(operation)
        self._save()

    def get_last_active_operation(self, source_dir: Optional[str] = None) -> Optional[OperationRecord]:
        """Get the most recent non-undone batch operation, optionally filtered by directory."""
        for op in reversed(self.history):
            if not op.undone:
                if source_dir is None or Path(op.source_dir).resolve() == Path(source_dir).resolve():
                    return op
        return None

    def get_operation_by_id(self, batch_id: str) -> Optional[OperationRecord]:
        """Retrieve operation by batch ID."""
        for op in self.history:
            if op.batch_id == batch_id:
                return op
        return None

    def mark_undone(self, batch_id: str) -> bool:
        """Mark an operation as undone."""
        for op in self.history:
            if op.batch_id == batch_id:
                op.undone = True
                op.undone_timestamp = datetime.now().isoformat()
                for file_rec in op.files:
                    if file_rec.status == "COMPLETED":
                        file_rec.status = "UNDONE"
                self._save()
                return True
        return False

    def list_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return a summarized list of historical operations."""
        summary = []
        for op in reversed(self.history[-limit:]):
            summary.append({
                "batch_id": op.batch_id,
                "timestamp": op.timestamp,
                "source_dir": op.source_dir,
                "strategy": op.strategy,
                "duplicate_strategy": op.duplicate_strategy,
                "recursive": op.recursive,
                "total_files": op.total_files,
                "successful_moves": op.successful_moves,
                "failed_moves": op.failed_moves,
                "undone": op.undone,
                "undone_timestamp": op.undone_timestamp,
            })
        return summary

    def clear(self):
        """Clear all transaction history."""
        self.history = []
        self._save()
