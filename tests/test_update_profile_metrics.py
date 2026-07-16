import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_profile_metrics.py"
SPEC = importlib.util.spec_from_file_location("update_profile_metrics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpdateProfileMetricsTest(unittest.TestCase):
    def test_readme_is_relative_to_repository_root(self):
        self.assertEqual(MODULE.README, SCRIPT.parents[1] / "README.md")

    def test_main_updates_configured_readme(self):
        metrics = {
            "commits": 1,
            "pull_requests": 2,
            "issues": 3,
            "total_contributions": 6,
        }
        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            readme.write_text(
                "before\n<!-- METRICS:START -->old<!-- METRICS:END -->\nafter\n",
                encoding="utf-8",
            )
            with (
                patch.object(MODULE, "README", readme),
                patch.object(MODULE, "get_token", return_value="token"),
                patch.object(MODULE, "fetch_metrics", return_value=metrics),
            ):
                self.assertEqual(MODULE.main(), 0)

            updated = readme.read_text(encoding="utf-8")
            self.assertIn("| Commits | 1 |", updated)
            self.assertIn("| Total Contributions | 6 |", updated)
            self.assertTrue(updated.startswith("before\n"))
            self.assertTrue(updated.endswith("\nafter\n"))


if __name__ == "__main__":
    unittest.main()
