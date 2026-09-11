"""
Tests for Jarvis v2 UpdatePipeline.
"""

import tempfile
import unittest
from pathlib import Path

from updater.candidate import (
    UpdateCandidate,
)

from updater.pipeline import (
    UpdatePipeline,
)


# ============================================================
# FAKE STAGING
# ============================================================

class FakeValidation:
    def __init__(
        self,
        success: bool,
    ):
        self.success = success
        self.compile_success = success
        self.tests_success = success
        self.return_code = (
            0 if success else 1
        )
        self.output = (
            "OK"
            if success
            else "FAILED"
        )
        self.duration_seconds = 0.01


class FakeStaging:
    """
    Полностью временный staging для unit tests.
    """

    def __init__(
        self,
        validation_success=True,
    ):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temp.name
        )

        self.validation_success = (
            validation_success
        )

        self.created = []

        self.removed = []

    def create(self):
        index = (
            len(self.created)
            + 1
        )

        path = (
            self.root
            / f"candidate_{index}"
        )

        (
            path
            / "core"
        ).mkdir(
            parents=True
        )

        (
            path
            / "core"
            / "example.py"
        ).write_text(
            "VALUE = 1\n",
            encoding="utf-8",
        )

        self.created.append(
            path
        )

        return path

    def validate(
        self,
        staging_dir,
    ):
        return FakeValidation(
            self.validation_success
        )

    def remove(
        self,
        staging_dir,
    ):
        self.removed.append(
            Path(staging_dir)
        )

    def cleanup(self):
        self.temp.cleanup()


# ============================================================
# TESTS
# ============================================================

class UpdatePipelineTests(
    unittest.TestCase
):

    def test_valid_candidate_is_accepted(
        self,
    ):
        staging = FakeStaging(
            validation_success=True
        )

        try:
            pipeline = UpdatePipeline(
                staging=staging
            )

            candidate = UpdateCandidate(
                relative_path=(
                    "core/example.py"
                ),
                new_content=(
                    "VALUE = 2\n"
                ),
                description=(
                    "Изменить тестовое значение."
                ),
                expected_effect=(
                    "Проверить pipeline."
                ),
                change_type="test",
            )

            review = pipeline.review(
                candidate
            )

            self.assertTrue(
                review.accepted
            )

            self.assertEqual(
                review.status,
                "ACCEPTED",
            )

            self.assertIn(
                "+VALUE = 2",
                review.diff,
            )

        finally:
            staging.cleanup()

    def test_failed_validation_rejects_candidate(
        self,
    ):
        staging = FakeStaging(
            validation_success=False
        )

        try:
            pipeline = UpdatePipeline(
                staging=staging
            )

            candidate = UpdateCandidate(
                relative_path=(
                    "core/example.py"
                ),
                new_content=(
                    "VALUE = 999\n"
                ),
                description="Test",
                expected_effect="Test",
                change_type="test",
            )

            review = pipeline.review(
                candidate
            )

            self.assertFalse(
                review.accepted
            )

            self.assertEqual(
                review.status,
                "REJECTED",
            )

        finally:
            staging.cleanup()

    def test_invalid_path_is_rejected_before_patch(
        self,
    ):
        staging = FakeStaging()

        try:
            pipeline = UpdatePipeline(
                staging=staging
            )

            candidate = UpdateCandidate(
                relative_path=".env",
                new_content=(
                    "SECRET=bad"
                ),
                description="Test",
                expected_effect="Test",
            )

            review = pipeline.review(
                candidate
            )

            self.assertFalse(
                review.accepted
            )

            self.assertEqual(
                len(staging.created),
                0,
            )

        finally:
            staging.cleanup()

    def test_no_change_is_rejected(
        self,
    ):
        staging = FakeStaging()

        try:
            pipeline = UpdatePipeline(
                staging=staging
            )

            candidate = UpdateCandidate(
                relative_path=(
                    "core/example.py"
                ),
                new_content=(
                    "VALUE = 1\n"
                ),
                description="No change",
                expected_effect="None",
                change_type="test",
            )

            review = pipeline.review(
                candidate
            )

            self.assertFalse(
                review.accepted
            )

            self.assertIn(
                "не изменяет",
                review.reason,
            )

        finally:
            staging.cleanup()

    def test_staging_is_removed_by_default(
        self,
    ):
        staging = FakeStaging()

        try:
            pipeline = UpdatePipeline(
                staging=staging
            )

            candidate = UpdateCandidate(
                relative_path=(
                    "core/example.py"
                ),
                new_content=(
                    "VALUE = 3\n"
                ),
                description="Test",
                expected_effect="Test",
                change_type="test",
            )

            pipeline.review(
                candidate,
                keep_staging=False,
            )

            self.assertEqual(
                len(staging.removed),
                1,
            )

        finally:
            staging.cleanup()

    def test_keep_staging_preserves_candidate(
        self,
    ):
        staging = FakeStaging()

        try:
            pipeline = UpdatePipeline(
                staging=staging
            )

            candidate = UpdateCandidate(
                relative_path=(
                    "core/example.py"
                ),
                new_content=(
                    "VALUE = 4\n"
                ),
                description="Test",
                expected_effect="Test",
                change_type="test",
            )

            pipeline.review(
                candidate,
                keep_staging=True,
            )

            self.assertEqual(
                len(staging.removed),
                0,
            )

        finally:
            staging.cleanup()


if __name__ == "__main__":
    unittest.main()