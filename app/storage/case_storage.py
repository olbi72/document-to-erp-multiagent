import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.document_case import DocumentCase
from app.storage.review_package_builder import ReviewPackageBuilder


class CaseStorage:
    def __init__(self) -> None:
        self.review_package_builder = ReviewPackageBuilder()

    def save(self, document_case: DocumentCase) -> Path:
        output_dir = self._get_output_dir(document_case)
        output_dir.mkdir(parents=True, exist_ok=True)

        technical_output_path = output_dir / self._build_technical_file_name(document_case)

        technical_payload = self._build_technical_payload(document_case)

        self._write_json(technical_output_path, technical_payload)

        if document_case.final_status == "review_required":
            review_output_path = output_dir / self._build_review_file_name(document_case)
            review_payload = self.review_package_builder.build(document_case)
            self._write_json(review_output_path, review_payload)

        return technical_output_path

    def _build_technical_payload(self, document_case: DocumentCase) -> dict[str, Any]:
        payload = asdict(document_case)

        payload["processing_metadata"] = {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "pipeline_stage": document_case.final_status,
        }

        payload["human_review"] = self._build_human_review_block(document_case)

        return payload

    def _build_human_review_block(self, document_case: DocumentCase) -> dict[str, Any]:
        if document_case.final_status == "review_required":
            return {
                "status": "pending",
                "reviewed_by": None,
                "reviewed_at": None,
                "review_decision": None,
                "corrections": {},
                "review_comment": None,
            }

        return {
            "status": "not_required",
            "reviewed_by": None,
            "reviewed_at": None,
            "review_decision": None,
            "corrections": {},
            "review_comment": None,
        }

    def _get_output_dir(self, document_case: DocumentCase) -> Path:
        if document_case.final_status == "validated":
            return Path(settings.approved_dir)

        if document_case.final_status == "review_required":
            return Path(settings.review_pending_dir)

        return Path(settings.rejected_dir)

    def _build_technical_file_name(self, document_case: DocumentCase) -> str:
        source_name = Path(document_case.file_name).stem
        return f"{source_name}.technical.json"

    def _build_review_file_name(self, document_case: DocumentCase) -> str:
        source_name = Path(document_case.file_name).stem
        return f"{source_name}.review.json"

    def _write_json(self, output_path: Path, payload: dict[str, Any]) -> None:
        with output_path.open("w", encoding="utf-8") as file_obj:
            json.dump(
                payload,
                file_obj,
                ensure_ascii=False,
                indent=2,
            )