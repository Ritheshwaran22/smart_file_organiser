"""
Django Views and API Handlers for Smart File Organizer
"""

import json
import os
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from smart_organizer import (
    SmartOrganizer,
    OrganizationStrategy,
    DuplicateStrategy,
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ICONS,
    DEFAULT_CATEGORY_COLORS,
)

# Global organizer instance
organizer = SmartOrganizer()


def index(request: HttpRequest) -> HttpResponse:
    """Render the main Smart File Organizer Dashboard."""
    # Pre-populate common paths for quick selector
    user_home = Path.home()
    common_paths = {
        "Downloads": str(user_home / "Downloads"),
        "Desktop": str(user_home / "Desktop"),
        "Documents": str(user_home / "Documents"),
        "Pictures": str(user_home / "Pictures"),
    }
    # Filter only existing paths
    available_shortcuts = {
        name: p for name, p in common_paths.items() if Path(p).exists()
    }

    context = {
        "categories": DEFAULT_CATEGORIES,
        "category_icons": DEFAULT_CATEGORY_ICONS,
        "category_colors": DEFAULT_CATEGORY_COLORS,
        "shortcuts": available_shortcuts,
        "strategies": [
            {"id": "by_category", "name": "By Category", "desc": "Documents, Images, Audio, Video, Code, Archives..."},
            {"id": "by_extension", "name": "By Extension", "desc": "Subfolders for each file extension (.pdf, .png, etc.)"},
            {"id": "by_date_year_month", "name": "By Date (Year / Month)", "desc": "e.g. 2026/08-August based on modification date"},
            {"id": "by_date_year", "name": "By Year", "desc": "e.g. 2026/ based on file year"},
            {"id": "by_size", "name": "By File Size", "desc": "Tiny (<1MB), Medium (1-50MB), Large (50MB-1GB), Huge"},
        ],
        "duplicate_strategies": [
            {"id": "rename_sequence", "name": "Auto-Rename (Sequence)", "desc": "Append (1), (2), (3)... to prevent overwrites"},
            {"id": "rename_timestamp", "name": "Auto-Rename (Timestamp)", "desc": "Append _YYYYMMDD_HHMMSS suffix"},
            {"id": "move_to_duplicates", "name": "Move to _Duplicates Folder", "desc": "Isolate duplicates into a dedicated directory"},
            {"id": "skip", "name": "Skip Duplicates", "desc": "Leave existing conflicting files unchanged"},
        ],
    }
    return render(request, "organizer_app/index.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def api_scan(request: HttpRequest) -> JsonResponse:
    """Scan directory and return categorized summary."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        target_path = data.get("path", "").strip()
        strategy_str = data.get("strategy", "by_category")
        recursive = bool(data.get("recursive", False))
        custom_rules = data.get("custom_rules", None)

        if not target_path:
            return JsonResponse({"success": False, "error": "Please provide a directory path."}, status=400)

        path_obj = Path(target_path).resolve()
        if not path_obj.exists() or not path_obj.is_dir():
            return JsonResponse({"success": False, "error": f"Directory does not exist: {target_path}"}, status=404)

        try:
            strategy = OrganizationStrategy(strategy_str)
        except ValueError:
            strategy = OrganizationStrategy.BY_CATEGORY

        scan_result = organizer.scan_directory(
            source_dir_path=str(path_obj),
            recursive=recursive,
            strategy=strategy,
            custom_rules=custom_rules,
        )

        files_serialized = [
            {
                "path": f.path,
                "filename": f.filename,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "size_human": f.size_human,
                "modified_time": f.modified_time,
                "category": f.category,
                "category_icon": f.category_icon,
                "category_color": f.category_color,
                "target_folder_name": f.target_folder_name,
                "target_path": f.target_path,
            }
            for f in scan_result.files
        ]

        return JsonResponse({
            "success": True,
            "source_dir": scan_result.source_dir,
            "total_files": scan_result.total_files,
            "total_size_bytes": scan_result.total_size_bytes,
            "total_size_human": scan_result.total_size_human,
            "categories_count": scan_result.categories_count,
            "categories_size": scan_result.categories_size,
            "categories_size_human": scan_result.categories_size_human,
            "extensions_count": scan_result.extensions_count,
            "files": files_serialized,
            "errors": scan_result.errors,
            "logs": organizer.get_memory_logs(),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_organize(request: HttpRequest) -> JsonResponse:
    """Execute or simulate organization on the target directory."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        target_path = data.get("path", "").strip()
        strategy_str = data.get("strategy", "by_category")
        duplicate_strategy_str = data.get("duplicate_strategy", "rename_sequence")
        recursive = bool(data.get("recursive", False))
        dry_run = bool(data.get("dry_run", False))
        clean_empty = bool(data.get("clean_empty_folders", False))
        custom_rules = data.get("custom_rules", None)

        if not target_path:
            return JsonResponse({"success": False, "error": "Please provide a directory path."}, status=400)

        path_obj = Path(target_path).resolve()
        if not path_obj.exists() or not path_obj.is_dir():
            return JsonResponse({"success": False, "error": f"Directory does not exist: {target_path}"}, status=404)

        try:
            strategy = OrganizationStrategy(strategy_str)
        except ValueError:
            strategy = OrganizationStrategy.BY_CATEGORY

        try:
            dup_strategy = DuplicateStrategy(duplicate_strategy_str)
        except ValueError:
            dup_strategy = DuplicateStrategy.RENAME_SEQUENCE

        result = organizer.organize(
            source_dir_path=str(path_obj),
            strategy=strategy,
            duplicate_strategy=dup_strategy,
            recursive=recursive,
            dry_run=dry_run,
            clean_empty_folders=clean_empty,
            custom_rules=custom_rules,
        )

        return JsonResponse({
            "success": True,
            "batch_id": result.batch_id,
            "timestamp": result.timestamp,
            "source_dir": result.source_dir,
            "strategy": result.strategy,
            "duplicate_strategy": result.duplicate_strategy,
            "total_processed": result.total_processed,
            "successful_moves": result.successful_moves,
            "failed_moves": result.failed_moves,
            "skipped_moves": result.skipped_moves,
            "created_folders": result.created_folders,
            "errors": result.errors,
            "files": result.files,
            "logs": result.activity_logs,
            "is_dry_run": result.is_dry_run,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_undo(request: HttpRequest) -> JsonResponse:
    """Undo the last or a specific organization batch."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        batch_id = data.get("batch_id", None)
        target_path = data.get("path", None)

        result = organizer.undo(batch_id=batch_id, source_dir=target_path)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def api_history(request: HttpRequest) -> JsonResponse:
    """Return transaction history."""
    try:
        history_records = organizer.history.list_history(limit=30)
        return JsonResponse({"success": True, "history": history_records})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_create_demo(request: HttpRequest) -> JsonResponse:
    """Create a sample mock folder with assorted dummy files for testing."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        parent_dir = data.get("parent_dir", None)
        if not parent_dir:
            parent_dir = str(Path.home() / "Desktop")
            if not Path(parent_dir).exists():
                parent_dir = str(Path.cwd())

        sandbox_dir = organizer.generate_demo_sandbox(parent_dir)
        return JsonResponse({
            "success": True,
            "sandbox_path": str(sandbox_dir),
            "message": f"Demo sandbox created with 25+ test files at {sandbox_dir}",
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
