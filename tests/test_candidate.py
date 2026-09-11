"""
Tests for UpdateCandidate.
"""

import unittest

from updater.candidate import (
    UpdateCandidate,
    CandidateError,
)


class UpdateCandidateTests(
    unittest.TestCase
):

    def test_valid_core_candidate(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=(
                "core/example.py"
            ),
            new_content=(
                "VALUE = 2\n"
            ),
            description=(
                "Исправить значение."
            ),
            expected_effect=(
                "Тест будет проходить."
            ),
            change_type="fix",
        )

        candidate.validate()

        self.assertEqual(
            candidate.normalized_path(),
            "core/example.py",
        )

    def test_env_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=".env",
            new_content="SECRET=x",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_main_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path="main.py",
            new_content="print('x')",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_config_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path="config.py",
            new_content="X = 1",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_parent_escape_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=(
                "core/../../outside.py"
            ),
            new_content="X = 1",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_legacy_root_file_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path="brain.py",
            new_content="X = 1",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_non_python_candidate_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=(
                "core/example.exe"
            ),
            new_content="binary",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_empty_content_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=(
                "core/example.py"
            ),
            new_content="   ",
            description="Test",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_missing_description_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=(
                "core/example.py"
            ),
            new_content="X = 1",
            description="",
            expected_effect="Test",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()

    def test_unknown_change_type_is_blocked(
        self,
    ):
        candidate = UpdateCandidate(
            relative_path=(
                "core/example.py"
            ),
            new_content="X = 1",
            description="Test",
            expected_effect="Test",
            change_type="destroy",
        )

        with self.assertRaises(
            CandidateError
        ):
            candidate.validate()


if __name__ == "__main__":
    unittest.main()