import json
import tempfile
import shutil
from pathlib import Path
from django.test import TestCase, Client
from django.urls import reverse

class OrganizerAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_dir = Path(tempfile.mkdtemp(prefix="django_test_organizer_"))
        
        # Create some sample files
        (self.test_dir / "sample.pdf").write_text("sample pdf")
        (self.test_dir / "photo.png").write_text("sample png")
        (self.test_dir / "audio.mp3").write_text("sample mp3")
        (self.test_dir / "script.py").write_text("print('test')")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dashboard_view(self):
        response = self.client.get(reverse("organizer_app:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Smart File Organizer")

    def test_api_scan_endpoint(self):
        response = self.client.post(
            reverse("organizer_app:api_scan"),
            data=json.dumps({
                "path": str(self.test_dir),
                "strategy": "by_category",
                "recursive": False
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_files"], 4)
        self.assertIn("Documents", data["categories_count"])
        self.assertIn("Images", data["categories_count"])

    def test_api_organize_and_undo_endpoints(self):
        # Organize
        org_response = self.client.post(
            reverse("organizer_app:api_organize"),
            data=json.dumps({
                "path": str(self.test_dir),
                "strategy": "by_category",
                "duplicate_strategy": "rename_sequence",
                "dry_run": False
            }),
            content_type="application/json"
        )
        self.assertEqual(org_response.status_code, 200)
        org_data = org_response.json()
        self.assertTrue(org_data["success"])
        self.assertEqual(org_data["successful_moves"], 4)
        batch_id = org_data["batch_id"]

        # Verify files were moved
        self.assertTrue((self.test_dir / "Documents" / "sample.pdf").exists())
        self.assertTrue((self.test_dir / "Images" / "photo.png").exists())

        # Test Undo endpoint
        undo_response = self.client.post(
            reverse("organizer_app:api_undo"),
            data=json.dumps({
                "batch_id": batch_id,
                "path": str(self.test_dir)
            }),
            content_type="application/json"
        )
        self.assertEqual(undo_response.status_code, 200)
        undo_data = undo_response.json()
        self.assertTrue(undo_data["success"])
        self.assertEqual(undo_data["restored_count"], 4)

        # Verify files restored
        self.assertTrue((self.test_dir / "sample.pdf").exists())
        self.assertTrue((self.test_dir / "photo.png").exists())

    def test_api_create_demo_and_history(self):
        demo_response = self.client.post(
            reverse("organizer_app:api_create_demo"),
            data=json.dumps({"parent_dir": str(self.test_dir)}),
            content_type="application/json"
        )
        self.assertEqual(demo_response.status_code, 200)
        demo_data = demo_response.json()
        self.assertTrue(demo_data["success"])
        self.assertTrue(Path(demo_data["sandbox_path"]).exists())

        hist_response = self.client.get(reverse("organizer_app:api_history"))
        self.assertEqual(hist_response.status_code, 200)
        hist_data = hist_response.json()
        self.assertTrue(hist_data["success"])
        self.assertIsInstance(hist_data["history"], list)
