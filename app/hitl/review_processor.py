import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings


class ReviewProcessor:
    def process_review_file(self, review_file_path: str | Path) -> Path:
        review_path = Path(review_file_path)

        if not review_path.exists():
            raise FileNotFoundError(f"Review file not found: {review_path}")

        review_payload = self._read_json(review_path)

        current_decision = review_payload["document_data"].get(
            "business_operation_decision"
        )
        accountant_review = review_payload.get("accountant_review", {})
        accountant_answer = accountant_review.get("accountant_answer")

        final_decision = self._resolve_final_decision(
            current_decision=current_decision,
            accountant_answer=accountant_answer,
        )

        review_payload["review_status"] = "completed"
        review_payload["accountant_review"]["final_business_operation_decision"] = (
            final_decision
        )
        review_payload["accountant_review"]["reviewed_at"] = datetime.now().isoformat(
            timespec="seconds"
        )

        approved_dir = Path(settings.approved_dir)
        approved_dir.mkdir(parents=True, exist_ok=True)

        approved_review_path = approved_dir / review_path.name.replace(
            ".review.json",
            ".approved.review.json",
        )

        self._write_json(approved_review_path, review_payload)

        self._move_matching_technical_file_to_approved(review_path, final_decision)

        return approved_review_path

    def _resolve_final_decision(
        self,
        current_decision: str | None,
        accountant_answer: str | None,
    ) -> str:
        if accountant_answer is None:
            raise ValueError("accountant_answer is empty")

        normalized_answer = accountant_answer.strip().lower()

        if current_decision in ["business", "non_business"]:
            if normalized_answer == "y":
                return current_decision

            if normalized_answer == "n":
                return self._invert_business_decision(current_decision)

            raise ValueError(
                "For current decision business/non_business, "
                "accountant_answer must be Y or N"
            )

        if current_decision == "not_identified":
            if normalized_answer in ["business", "non_business"]:
                return normalized_answer

            raise ValueError(
                "For current decision not_identified, "
                "accountant_answer must be business or non_business"
            )

        raise ValueError(f"Unsupported current decision: {current_decision}")

    def _invert_business_decision(self, current_decision: str) -> str:
        if current_decision == "business":
            return "non_business"

        if current_decision == "non_business":
            return "business"

        raise ValueError(f"Cannot invert decision: {current_decision}")

    def _move_matching_technical_file_to_approved(
        self,
        review_path: Path,
        final_decision: str,
    ) -> None:
        technical_path = Path(
            str(review_path).replace(".review.json", ".technical.json")
        )

        if not technical_path.exists():
            return

        technical_payload = self._read_json(technical_path)

        technical_payload["business_operation_result"][
            "final_decision"
        ] = final_decision

        if "llm_classification" in technical_payload["business_operation_result"]:
            technical_payload["business_operation_result"]["llm_classification"][
                "final_decision"
            ] = final_decision

        technical_payload["human_review"] = {
            "status": "completed",
            "reviewed_by": "accountant",
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "review_decision": final_decision,
            "corrections": {
                "business_operation_decision": final_decision,
            },
            "review_comment": None,
        }

        technical_payload["final_status"] = "validated"
        technical_payload["hitl_status"] = "completed"

        approved_dir = Path(settings.approved_dir)
        approved_dir.mkdir(parents=True, exist_ok=True)

        approved_technical_path = approved_dir / technical_path.name.replace(
            ".technical.json",
            ".approved.technical.json",
        )

        self._write_json(approved_technical_path, technical_payload)

        technical_path.unlink()

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as file_obj:
            json.dump(
                payload,
                file_obj,
                ensure_ascii=False,
                indent=2,
            )