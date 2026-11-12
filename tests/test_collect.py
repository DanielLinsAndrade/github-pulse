import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collect import build_snapshot, history_csv, render_status, render_svg


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 12, 9, 17, tzinfo=ZoneInfo("America/Fortaleza"))
        self.repos = [
            {"name": "legal", "full_name": "Teste/legal", "html_url": "https://github.com/Teste/legal",
             "fork": False, "private": False, "stargazers_count": 4, "forks_count": 2,
             "open_issues_count": 1, "language": "Python", "pushed_at": "2026-11-11T00:00:00Z"},
            {"name": "github-pulse", "full_name": "Teste/github-pulse", "fork": False},
            {"name": "forkado", "full_name": "Teste/forkado", "fork": True},
            {"name": "privado", "full_name": "Teste/privado", "private": True},
        ]

    def test_snapshot_filters_and_totals(self):
        snap = build_snapshot("Teste", self.repos, "Teste/github-pulse", self.now)
        self.assertEqual(snap["repository_count"], 1)
        self.assertEqual(snap["stars"], 4)
        self.assertEqual(snap["forks"], 2)
        self.assertEqual(snap["repositories"][0]["name"], "legal")

    def test_history_and_panel(self):
        snap = build_snapshot("Teste", self.repos, "Teste/github-pulse", self.now)
        self.assertIn("2026-11-12,1,4,2,1", history_csv([snap]))
        self.assertIn("[legal](https://github.com/Teste/legal)", render_status([snap]))
        self.assertIn("<svg", render_svg([snap]))
        self.assertIn("<circle", render_svg([snap]))
        self.assertIn("<polyline", render_svg([snap, snap]))


if __name__ == "__main__":
    unittest.main()
