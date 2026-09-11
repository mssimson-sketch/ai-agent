"""
Jarvis v2 - Update Pipeline

Проверяет UpdateCandidate полностью в изолированном staging.

Pipeline:
Candidate
  -> validate
  -> staging copy
  -> PatchManager
  -> diff inspection
  -> compile
  -> unit tests
  -> ACCEPTED / REJECTED

ВАЖНО:
этот модуль НЕ применяет изменения
к рабочей копии проекта.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from updater.candidate import (
    UpdateCandidate,
    CandidateError,
)

from updater.patch_manager import (
    PatchManager,
    PatchError,
    PatchResult,
)

from updater.staging import (
    StagingManager,
    ValidationResult,
)


class UpdatePipelineError(Exception):
    pass


@dataclass
class UpdateReview:
    accepted: bool
    status: str

    candidate_path: str

    reason: str

    staging_dir: str | None = None

    patch: PatchResult | None = None

    validation: ValidationResult | None = None

    diff: str = ""


class UpdatePipeline:
    """
    Безопасная проверка одного кандидата.
    """

    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_REJECTED = "REJECTED"

    def __init__(
        self,
        staging: StagingManager | None = None,
    ):
        self.staging = (
            staging
            or StagingManager()
        )

    # ========================================================
    # REVIEW
    # ========================================================

    def review(
        self,
        candidate: UpdateCandidate,
        keep_staging: bool = False,
    ) -> UpdateReview:
        """
        Проверить кандидат без изменения рабочего проекта.
        """

        staging_dir = None

        try:
            # ------------------------------------------------
            # 1. CANDIDATE VALIDATION
            # ------------------------------------------------

            candidate.validate()

            relative_path = (
                candidate.normalized_path()
            )

            # ------------------------------------------------
            # 2. CREATE STAGING
            # ------------------------------------------------

            staging_dir = (
                self.staging.create()
            )

            # ------------------------------------------------
            # 3. PATCH STAGING ONLY
            # ------------------------------------------------

            patcher = PatchManager(
                staging_dir
            )

            patch = patcher.replace_file(
                relative_path=relative_path,
                new_content=(
                    candidate.new_content
                ),
            )

            # Пустое изменение не считаем
            # новым обновлением.
            if (
                patch.changed_lines == 0
                and not patch.diff
            ):
                return UpdateReview(
                    accepted=False,
                    status=self.STATUS_REJECTED,
                    candidate_path=relative_path,
                    reason=(
                        "Кандидат не изменяет файл."
                    ),
                    staging_dir=str(
                        staging_dir
                    ),
                    patch=patch,
                    validation=None,
                    diff="",
                )

            # ------------------------------------------------
            # 4. VALIDATE STAGING
            # ------------------------------------------------

            validation = (
                self.staging.validate(
                    staging_dir
                )
            )

            if not validation.success:

                reason = (
                    "Кандидат не прошёл "
                    "автоматическую проверку."
                )

                return UpdateReview(
                    accepted=False,
                    status=self.STATUS_REJECTED,
                    candidate_path=relative_path,
                    reason=reason,
                    staging_dir=str(
                        staging_dir
                    ),
                    patch=patch,
                    validation=validation,
                    diff=patch.diff,
                )

            # ------------------------------------------------
            # 5. ACCEPT
            # ------------------------------------------------

            return UpdateReview(
                accepted=True,
                status=self.STATUS_ACCEPTED,
                candidate_path=relative_path,
                reason=(
                    "Кандидат успешно прошёл "
                    "компиляцию и все тесты."
                ),
                staging_dir=str(
                    staging_dir
                ),
                patch=patch,
                validation=validation,
                diff=patch.diff,
            )

        except (
            CandidateError,
            PatchError,
        ) as exc:

            return UpdateReview(
                accepted=False,
                status=self.STATUS_REJECTED,
                candidate_path=str(
                    getattr(
                        candidate,
                        "relative_path",
                        "unknown",
                    )
                ),
                reason=str(exc),
                staging_dir=(
                    str(staging_dir)
                    if staging_dir
                    else None
                ),
            )

        except Exception as exc:

            return UpdateReview(
                accepted=False,
                status=self.STATUS_REJECTED,
                candidate_path=str(
                    getattr(
                        candidate,
                        "relative_path",
                        "unknown",
                    )
                ),
                reason=(
                    "Неожиданная ошибка "
                    "проверки кандидата: "
                    + str(exc)
                ),
                staging_dir=(
                    str(staging_dir)
                    if staging_dir
                    else None
                ),
            )

        finally:
            # Для обычной автоматической проверки
            # staging можно удалить.
            #
            # keep_staging=True полезен разработчику
            # для ручной инспекции diff/файлов.

            if (
                staging_dir is not None
                and not keep_staging
            ):
                try:
                    self.staging.remove(
                        staging_dir
                    )
                except Exception:
                    pass