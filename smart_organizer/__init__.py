"""
Smart File Organizer Core Package
"""

from .config import (
    DEFAULT_CATEGORIES,
    OrganizationStrategy,
    DuplicateStrategy,
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_CATEGORY_ICONS,
    DEFAULT_CATEGORY_COLORS,
)
from .core import SmartOrganizer, FileItem, OrganizationResult, ScanResult
from .history import TransactionHistory, OperationRecord

__all__ = [
    "SmartOrganizer",
    "FileItem",
    "OrganizationResult",
    "ScanResult",
    "TransactionHistory",
    "OperationRecord",
    "DEFAULT_CATEGORIES",
    "OrganizationStrategy",
    "DuplicateStrategy",
    "DEFAULT_IGNORE_PATTERNS",
    "DEFAULT_CATEGORY_ICONS",
    "DEFAULT_CATEGORY_COLORS",
]

__version__ = "1.0.0"
