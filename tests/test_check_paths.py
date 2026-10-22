import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_paths.py"
SAMPLE = Path(__file__).resolve().parent / "data" / "sample_matches.csv"


class CheckPathsTests(unittest.TestCase):
    def run_script(self, root):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_existing_files_and_expected_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(SAMPLE, root / "DATA.csv")
            (root / "data" / "csv").mkdir(parents=True)
            shutil.copyfile(SAMPLE, root / "data" / "csv" / "DATA.csv")
            (root / "archive_v16").mkdir()
            shutil.copyfile(
                SAMPLE, root / "archive_v16" / "v16_per_match_predictions.csv"
            )

            before = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            result = self.run_script(root)
            after = sorted(str(path.relative_to(root)) for path in root.rglob("*"))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(before, after)
            self.assertEqual(result.stdout.count("VAR:"), 3)
            self.assertEqual(
                result.stdout.count("sep=None: 3 sutun | sep=',': 3 sutun"), 3
            )
            self.assertIn("match_id", result.stdout)
            self.assertIn("ID_away", result.stdout)
            self.assertEqual(result.stdout.count("Dosya boyutu:"), 3)
            self.assertTrue(result.stdout.rstrip().endswith("BITTI - salt okunur"))

    def test_missing_and_unreadable_files_do_not_stop_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "DATA.csv").write_text("", encoding="utf-8")

            result = self.run_script(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("OKUMA HATASI:", result.stdout)
            self.assertIn("YOK:", result.stdout)
            self.assertTrue(result.stdout.rstrip().endswith("BITTI - salt okunur"))


if __name__ == "__main__":
    unittest.main()
