from typing import Any

from app.models.document_case import DocumentCase


class ReviewPackageBuilder:
    def build(self, document_case: DocumentCase) -> dict[str, Any]:
        extracted = document_case.extracted_data or {}
        counterparty_result = document_case.counterparty_result or {}
        business_result = document_case.business_operation_result or {}
        validation_result = document_case.validation_result or {}

        supplier_from_document = extracted.get("supplier_name")
        supplier_final = self._get_final_supplier_name(counterparty_result)
        supplier_match_status = counterparty_result.get("status")
        current_decision = business_result.get("final_decision")

        return {
            "file_name": document_case.file_name,
            "source_file": document_case.source_file,
            "review_status": "pending",
            "document_data": {
                "document_type": extracted.get("document_type"),
                "document_number": extracted.get("document_number"),
                "document_date": extracted.get("document_date"),
                "customer_name": extracted.get("customer_name"),
                "supplier_name_from_document": supplier_from_document,
                "supplier_name_final": supplier_final,
                "supplier_is_new": supplier_match_status == "not_found",
                "supplier_match_status": supplier_match_status,
                "total_amount": extracted.get("total_amount"),
                "vat_amount": extracted.get("vat_amount"),
                "currency": extracted.get("currency"),
                "description": extracted.get("description"),
                "business_operation_decision": current_decision,
            },
            "review_flags": validation_result.get("flags", []),
            "accountant_review": self._build_accountant_review_block(
                current_decision
            ),
        }

    def _get_final_supplier_name(
        self,
        counterparty_result: dict[str, Any],
    ) -> str | None:
        if counterparty_result.get("status") != "matched":
            return None

        matched_counterparty = counterparty_result.get("matched_counterparty") or {}

        return (
            matched_counterparty.get("full_name")
            or matched_counterparty.get("short_name")
            or None
        )

    def _build_accountant_review_block(
        self,
        current_decision: str | None,
    ) -> dict[str, Any]:
        if current_decision in ["business", "non_business"]:
            return {
                "question": (
                    f"Система визначила операцію як {current_decision}. "
                    "Це правильно?"
                ),
                "instruction": (
                    "Поміняйте null у полі accountant_answer на Y, "
                    "якщо правильно, або на N, якщо неправильно."
                ),
                "allowed_answers": ["Y", "N"],
                "accountant_answer": None,
                "final_business_operation_decision": None,
                "review_comment": None,
            }

        return {
            "question": (
                "Система не змогла визначити господарськість операції. "
                "Оберіть фінальне рішення."
            ),
            "instruction": (
                "Поміняйте null у полі accountant_answer "
                "на business або non_business."
            ),
            "allowed_answers": ["business", "non_business"],
            "accountant_answer": None,
            "final_business_operation_decision": None,
            "review_comment": None,
        }