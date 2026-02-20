import json
import os
import tempfile
import unittest

from odse.cli import main


class CLITransformTests(unittest.TestCase):
    """Tests for the odse transform CLI command."""

    def setUp(self):
        self.csv_content = (
            "timestamp,power,inverter_state,run_state\n"
            "2026-02-09 12:00:00,10,512,1\n"
            "2026-02-09 12:05:00,8,512,1\n"
        )
        self.csv_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        )
        self.csv_file.write(self.csv_content)
        self.csv_file.close()

    def tearDown(self):
        os.unlink(self.csv_file.name)

    def test_transform_to_stdout(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            main([
                "transform",
                "--source",
                "huawei",
                "--input",
                self.csv_file.name,
            ])
        output = json.loads(mock_out.getvalue())
        self.assertEqual(len(output), 2)
        self.assertIn("timestamp", output[0])
        self.assertIn("kWh", output[0])

    def test_transform_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out:
            out_path = out.name
        try:
            main([
                "transform",
                "--source",
                "huawei",
                "--input",
                self.csv_file.name,
                "-o",
                out_path,
            ])
            with open(out_path) as f:
                output = json.load(f)
            self.assertEqual(len(output), 2)
        finally:
            os.unlink(out_path)

    def test_transform_to_csv_stdout(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            main([
                "transform",
                "--source",
                "huawei",
                "--input",
                self.csv_file.name,
                "--format",
                "csv",
            ])
        output = mock_out.getvalue()
        self.assertIn("timestamp", output)
        self.assertIn("kWh", output)

    def test_transform_missing_file(self):
        with self.assertRaises(SystemExit) as ctx:
            main([
                "transform",
                "--source",
                "huawei",
                "--input",
                "/nonexistent/file.csv",
            ])
        self.assertEqual(ctx.exception.code, 1)

    def test_transform_with_asset_id(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            main([
                "transform",
                "--source",
                "huawei",
                "--input",
                self.csv_file.name,
                "--asset-id", "SITE-001",
            ])
        output = json.loads(mock_out.getvalue())
        self.assertEqual(output[0]["asset_id"], "SITE-001")

    def test_transform_generic_csv_with_column_map(self):
        import io
        from unittest.mock import patch

        csv_content = "ts,energy\n2026-02-09 12:00:00,5.0\n"

        csv_f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        csv_f.write(csv_content)
        csv_f.close()

        try:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                main([
                    "transform",
                    "--source",
                    "generic_csv",
                    "--input",
                    csv_f.name,
                    "--column-map",
                    "timestamp=ts,kWh=energy",
                ])
            output = json.loads(mock_out.getvalue())
            self.assertEqual(len(output), 1)
            self.assertEqual(output[0]["kWh"], 5.0)
        finally:
            os.unlink(csv_f.name)


class CLIValidateTests(unittest.TestCase):
    """Tests for the odse validate CLI command."""

    def test_validate_valid_records(self):
        import io
        from unittest.mock import patch

        records = [
            {"timestamp": "2026-02-09T12:00:00Z", "kWh": 5.0, "error_type": "normal"},
            {"timestamp": "2026-02-09T12:05:00Z", "kWh": 4.8, "error_type": "normal"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            f.flush()
            json_path = f.name

        try:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                with self.assertRaises(SystemExit) as ctx:
                    main(["validate", "--input", json_path])
                self.assertEqual(ctx.exception.code, 0)
            report = json.loads(mock_out.getvalue())
            self.assertEqual(report["total"], 2)
            self.assertEqual(report["passed"], 2)
            self.assertEqual(report["failed"], 0)
        finally:
            os.unlink(json_path)

    def test_validate_invalid_records(self):
        import io
        from unittest.mock import patch

        records = [
            {"kWh": 5.0, "error_type": "normal"},  # missing timestamp
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            f.flush()
            json_path = f.name

        try:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                with self.assertRaises(SystemExit) as ctx:
                    main(["validate", "--input", json_path])
                self.assertEqual(ctx.exception.code, 1)
            report = json.loads(mock_out.getvalue())
            self.assertEqual(report["failed"], 1)
            self.assertTrue(len(report["errors"]) > 0)
        finally:
            os.unlink(json_path)

    def test_validate_with_profile(self):
        import io
        from unittest.mock import patch

        records = [
            {"timestamp": "2026-02-09T12:00:00Z", "kWh": 5.0, "error_type": "normal"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            f.flush()
            json_path = f.name

        try:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                with self.assertRaises(SystemExit) as ctx:
                    main([
                        "validate",
                        "--input",
                        json_path,
                        "--profile",
                        "bilateral",
                    ])
                self.assertEqual(ctx.exception.code, 1)
            report = json.loads(mock_out.getvalue())
            self.assertEqual(report["failed"], 1)
        finally:
            os.unlink(json_path)

    def test_validate_missing_file(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["validate", "--input", "/nonexistent/file.json"])
        self.assertEqual(ctx.exception.code, 1)


class CLIVersionTests(unittest.TestCase):
    """Tests for CLI version and help."""

    def test_version_subcommand(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            with self.assertRaises(SystemExit) as ctx:
                main(["version"])
            self.assertEqual(ctx.exception.code, 0)
        self.assertRegex(mock_out.getvalue().strip(), r"^\d+\.\d+\.\d+$")

    def test_version_flag(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_no_command_shows_help(self):
        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
