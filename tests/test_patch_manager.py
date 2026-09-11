"""
Tests for Jarvis v2 PatchManager.

Все изменения происходят только во временной папке.
"""

import tempfile
import unittest
from pathlib import Path

from updater.patch_manager import (
    PatchManager,
    PatchError,
)


class PatchManagerTests(
    unittest.TestCase
):

    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temp.name
        )

        self.sample = (
            self.root
            / "core"
            / "sample.py"
        )

        self.sample.parent.mkdir(
            parents=True
        )

        self.sample.write_text(
            "VALUE = 1\n",
            encoding="utf-8",
        )

        self.manager = PatchManager(
            self.root
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_patch_changes_file(
        self,
    ):
        result = (
            self.manager.replace_file(
                "core/sample.py",
                "VALUE = 2\n",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertNotEqual(
            result.old_sha256,
            result.new_sha256,
        )

        self.assertIn(
            "VALUE = 2",
            self.sample.read_text(
                encoding="utf-8"
            ),
        )

        self.assertIn(
            "+VALUE = 2",
            result.diff,
        )

    def test_identical_patch_has_no_changes(
        self,
    ):
        result = (
            self.manager.replace_file(
                "core/sample.py",
                "VALUE = 1\n",
            )
        )

        self.assertEqual(
            result.changed_lines,
            0,
        )

        self.assertEqual(
            result.diff,
            "",
        )

    def test_parent_escape_is_blocked(
        self,
    ):
        with self.assertRaises(
            PatchError
        ):
            self.manager.replace_file(
                "../outside.py",
                "BAD = True\n",
            )

    def test_absolute_path_is_blocked(
        self,
    ):
        with self.assertRaises(
            PatchError
        ):
            self.manager.replace_file(
                "D:/AI_Agent/config.py",
                "BAD = True\n",
            )

    def test_env_is_blocked(
        self,
    ):
        env = (
            self.root
            / ".env"
        )

        env.write_text(
            "SECRET=test\n",
            encoding="utf-8",
        )

        with self.assertRaises(
            PatchError
        ):
            self.manager.read_file(
                ".env"
            )

    def test_gitignore_is_blocked(
        self,
    ):
        target = (
            self.root
            / ".gitignore"
        )

        target.write_text(
            ".env\n",
            encoding="utf-8",
        )

        with self.assertRaises(
            PatchError
        ):
            self.manager.replace_file(
                ".gitignore",
                "",
            )

    def test_executable_type_is_blocked(
        self,
    ):
        target = (
            self.root
            / "bad.exe"
        )

        target.write_bytes(
            b"test"
        )

        with self.assertRaises(
            PatchError
        ):
            self.manager.read_file(
                "bad.exe"
            )


if __name__ == "__main__":
    unittest.main()