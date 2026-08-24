"""
Configuration, Constants, and Category Mappings for Smart File Organizer
"""

from enum import Enum
from typing import Dict, List, Set

class OrganizationStrategy(str, Enum):
    BY_CATEGORY = "by_category"
    BY_EXTENSION = "by_extension"
    BY_DATE_YEAR_MONTH = "by_date_year_month"
    BY_DATE_YEAR = "by_date_year"
    BY_SIZE = "by_size"
    CUSTOM_RULES = "custom_rules"

class DuplicateStrategy(str, Enum):
    RENAME_SEQUENCE = "rename_sequence"      # file (1).pdf
    RENAME_TIMESTAMP = "rename_timestamp"    # file_20260824_192030.pdf
    MOVE_TO_DUPLICATES = "move_to_duplicates" # _Duplicates/file.pdf
    SKIP = "skip"
    OVERWRITE = "overwrite"

# Broad catalog of 150+ file extensions classified into 12 intuitive categories
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Documents": [
        "pdf", "docx", "doc", "txt", "rtf", "odt", "tex", "wpd", "wps", 
        "pages", "log", "msg", "eml"
    ],
    "Images": [
        "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg", 
        "ico", "heic", "heif", "raw", "cr2", "nef", "arw", "psd"
    ],
    "Videos": [
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "3gp", 
        "vob", "ogv", "mts", "m2ts", "ts", "mpg", "mpeg"
    ],
    "Audio": [
        "mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "aiff", "alac", 
        "mid", "midi", "opus", "amr"
    ],
    "Archives": [
        "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "dmg", "pkg", 
        "tgz", "cab", "z", "lz", "lzma"
    ],
    "Spreadsheets": [
        "xlsx", "xls", "csv", "tsv", "ods", "numbers", "xlsm", "xlsb"
    ],
    "Presentations": [
        "pptx", "ppt", "key", "odp", "pps", "ppsx"
    ],
    "Code & Dev": [
        "py", "js", "ts", "jsx", "tsx", "html", "htm", "css", "scss", "sass", 
        "less", "json", "xml", "yaml", "yml", "java", "cpp", "c", "h", "hpp", 
        "cs", "php", "rb", "go", "rs", "sql", "sh", "bat", "ps1", "lua", 
        "swift", "kt", "dart", "r", "m", "asm", "vue", "md"
    ],
    "Executables & Installers": [
        "exe", "msi", "apk", "app", "deb", "rpm", "bin", "jar", "run", "gadget"
    ],
    "Books & Reading": [
        "epub", "mobi", "azw", "azw3", "cbr", "cbz", "djvu", "fb2", "lit"
    ],
    "Design & 3D": [
        "ai", "xd", "fig", "sketch", "blend", "obj", "stl", "fbx", "3ds", 
        "dae", "dwg", "dxf", "c4d"
    ],
    "Fonts": [
        "ttf", "otf", "woff", "woff2", "eot", "fon"
    ],
}

DEFAULT_CATEGORY_ICONS: Dict[str, str] = {
    "Documents": "📄",
    "Images": "🖼️",
    "Videos": "🎥",
    "Audio": "🎵",
    "Archives": "📦",
    "Spreadsheets": "📊",
    "Presentations": "📑",
    "Code & Dev": "💻",
    "Executables & Installers": "⚙️",
    "Books & Reading": "📚",
    "Design & 3D": "🎨",
    "Fonts": "🔤",
    "Others": "📁",
    "_Duplicates": "👥",
}

DEFAULT_CATEGORY_COLORS: Dict[str, str] = {
    "Documents": "#3b82f6",     # Blue
    "Images": "#ec4899",        # Pink
    "Videos": "#8b5cf6",        # Purple
    "Audio": "#10b981",         # Emerald
    "Archives": "#f59e0b",      # Amber
    "Spreadsheets": "#059669",  # Green
    "Presentations": "#ea580c", # Orange
    "Code & Dev": "#06b6d4",    # Cyan
    "Executables & Installers": "#64748b", # Slate
    "Books & Reading": "#6366f1", # Indigo
    "Design & 3D": "#d946ef",   # Fuchsia
    "Fonts": "#14b8a6",         # Teal
    "Others": "#94a3b8",        # Gray
    "_Duplicates": "#ef4444",   # Red
}

DEFAULT_IGNORE_PATTERNS: Set[str] = {
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".organizer_history.json",
    ".organizer_log.log",
}
