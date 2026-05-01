import json
from pathlib import Path
from typing import Any


class EvaluationRunner:
    def __init__(
        self,
        golden_dataset_path: str | Path = "app/evaluation/golden_dataset.json",
        results_dir: str | Path = "data/approved",
    ) -> None:
        self.golden_dataset_path = Path(golden_dataset_path)
        self.results_dir = Path(results_dir)

    def run(self) -> dict[str, Any]:
        golden_cases = self._load_golden_dataset()

        details = []

        for case in golden_cases:
            actual_payload = self._load_actual_payload(case["file_name"])
            case_result = self._evaluate_case(case, actual_payload)
            details.append(case_result)

        total_cases = len(details)
        passed_cases = sum(1 for item in details if item["passed"])
        failed_cases = total_cases - passed_cases

        return {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "accuracy": round(passed_cases / total_cases, 4) if total_cases else 0.0,
            "details": details,
        }

    def _load_golden_dataset(self) -> list[dict[str, Any]]:
        if not self.golden_dataset_path.exists():
            raise FileNotFoundError(
                f"Golden dataset not found: {self.golden_dataset_path}"
            )

        with self.golden_dataset_path.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj)

    def _load_actual_payload(self, file_name: str) -> dict[str, Any] | None:
        source_stem = Path(file_name).stem

        possible_files = [
            self.results_dir / f"{source_stem}.technical.json",
            self.results_dir / f"{source_stem}.approved.technical.json",
        ]

        for path in possible_files:
            if path.exists():
                with path.open("r", encoding="utf-8") as file_obj:
                    return json.load(file_obj)

        return None

    def _evaluate_case(
        self,
        expected: dict[str, Any],
        actual_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if actual_payload is None:
            return {
                "case_id": expected.get("case_id"),
                "file_name": expected.get("file_name"),
                "passed": False,
                "error": "Actual technical JSON not found in results directory",
                "checks": {},
            }

        actual_supplier_name_final = self._get_actual_supplier_name_final(
            actual_payload
        )
        actual_counterparty_status = (
            actual_payload.get("counterparty_result", {}).get("status")
        )
        actual_business_decision = (
            actual_payload.get("business_operation_result", {}).get("final_decision")
        )
        actual_hitl_required = (
            actual_payload.get("validation_result", {}).get("requires_hitl")
        )

        checks = {
            "supplier_name_correct": (
                actual_supplier_name_final
                == expected.get("expected_supplier_name_final")
            ),
            "counterparty_status_correct": (
                actual_counterparty_status
                == expected.get("expected_counterparty_status")
            ),
            "business_decision_correct": (
                actual_business_decision
                == expected.get("expected_business_decision")
            ),
            "hitl_routing_correct": (
                actual_hitl_required
                == expected.get("expected_hitl_required")
            ),
        }

        return {
            "case_id": expected.get("case_id"),
            "file_name": expected.get("file_name"),
            "passed": all(checks.values()),
            "checks": checks,
            "expected": {
                "supplier_name_final": expected.get(
                    "expected_supplier_name_final"
                ),
                "counterparty_status": expected.get(
                    "expected_counterparty_status"
                ),
                "business_decision": expected.get(
                    "expected_business_decision"
                ),
                "hitl_required": expected.get("expected_hitl_required"),
            },
            "actual": {
                "supplier_name_final": actual_supplier_name_final,
                "counterparty_status": actual_counterparty_status,
                "business_decision": actual_business_decision,
                "hitl_required": actual_hitl_required,
            },
        }

    def _get_actual_supplier_name_final(
        self,
        actual_payload: dict[str, Any],
    ) -> str | None:
        counterparty_result = actual_payload.get("counterparty_result", {})

        if counterparty_result.get("status") != "matched":
            return None

        matched_counterparty = counterparty_result.get("matched_counterparty") or {}

        return (
            matched_counterparty.get("full_name")
            or matched_counterparty.get("short_name")
            or None
        )