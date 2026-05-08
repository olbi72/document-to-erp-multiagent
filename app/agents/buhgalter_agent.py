from pathlib import Path
import json
import requests

from app.config import settings
from app.models.document_case import DocumentCase
from app.reference.contragent_repository import ContragentRepository
from app.reference.non_business_repository import NonBusinessRepository


class BuhgalterAgent:
    def __init__(self) -> None:
        self.repository = ContragentRepository()
        self.non_business_repository = NonBusinessRepository()
        self.model_name = settings.buhgalter_model

    def resolve_counterparty(
        self,
        supplier_name: str | None,
        supplier_ipn: str | None = None,
        supplier_edrpou: str | None = None,
    ) -> dict:
        if supplier_edrpou:
            match = self.repository.find_by_edrpou(supplier_edrpou)
            if match:
                return {
                    "status": "matched",
                    "method": "by_edrpou",
                    "input_supplier_name": supplier_name,
                    "input_ipn": supplier_ipn,
                    "input_edrpou": supplier_edrpou,
                    "matched_counterparty": match,
                    "confidence": 1.0,
                    "candidates": [],
                    "reason": "Exact match by EDRPOU",
                }

        if supplier_ipn:
            match = self.repository.find_by_inn(supplier_ipn)
            if match:
                return {
                    "status": "matched",
                    "method": "by_inn",
                    "input_supplier_name": supplier_name,
                    "input_ipn": supplier_ipn,
                    "input_edrpou": supplier_edrpou,
                    "matched_counterparty": match,
                    "confidence": 1.0,
                    "candidates": [],
                    "reason": "Exact match by INN",
                }

        if supplier_name:
            candidates = self.repository.find_name_candidates(supplier_name, limit=5)

            if not candidates:
                return {
                    "status": "not_found",
                    "method": "by_name_similarity",
                    "input_supplier_name": supplier_name,
                    "input_ipn": supplier_ipn,
                    "input_edrpou": supplier_edrpou,
                    "matched_counterparty": None,
                    "confidence": 0.0,
                    "candidates": [],
                    "reason": "No candidates found by name",
                }

            best_candidate = candidates[0]
            best_score = best_candidate["score"]
            second_score = candidates[1]["score"] if len(candidates) > 1 else 0

            if best_score >= 90 and (best_score - second_score) >= 10:
                return {
                    "status": "matched",
                    "method": "by_name_similarity",
                    "input_supplier_name": supplier_name,
                    "input_ipn": supplier_ipn,
                    "input_edrpou": supplier_edrpou,
                    "matched_counterparty": best_candidate,
                    "confidence": round(best_score / 100, 2),
                    "candidates": candidates,
                    "reason": "Best fuzzy match by supplier name",
                }

            return {
                "status": "ambiguous",
                "method": "by_name_similarity",
                "input_supplier_name": supplier_name,
                "input_ipn": supplier_ipn,
                "input_edrpou": supplier_edrpou,
                "matched_counterparty": None,
                "confidence": round(best_score / 100, 2),
                "candidates": candidates,
                "reason": "Name candidates found, but result requires review",
            }

        return {
            "status": "not_found",
            "method": "unresolved",
            "input_supplier_name": supplier_name,
            "input_ipn": supplier_ipn,
            "input_edrpou": supplier_edrpou,
            "matched_counterparty": None,
            "confidence": 0.0,
            "candidates": [],
            "reason": "No supplier identifiers provided",
        }

    def enrich_document_case(self, document_case: DocumentCase) -> DocumentCase:
        extracted = document_case.extracted_data

        counterparty_result = self.resolve_counterparty(
            supplier_name=extracted.get("supplier_name"),
            supplier_ipn=extracted.get("supplier_ipn"),
            supplier_edrpou=extracted.get("supplier_edrpou"),
        )

        document_case.counterparty_result = counterparty_result

        if self.is_without_vat_document(document_case):
            document_case.history_operations = []
            base_result = self.build_without_vat_result(document_case)
        else:
            history_operations = self.get_history_for_counterparty(document_case)
            document_case.history_operations = history_operations
            base_result = self.build_history_based_result(document_case)

        document_case.business_operation_result = base_result

        llm_classification = self.classify_business_operation_with_llm(document_case)

        document_case.business_operation_result = {
            **base_result,
            "llm_classification": llm_classification,
            "final_decision": llm_classification.get("final_decision"),
            "requires_hitl": (
                base_result.get("requires_hitl", True)
                or llm_classification.get("requires_hitl", True)
            ),
        }

        document_case.final_status = "counterparty_checked"

        return document_case

    def is_without_vat_document(self, document_case: DocumentCase) -> bool:
        extracted = document_case.extracted_data or {}

        vat_status = extracted.get("vat_status")
        vat_amount = extracted.get("vat_amount")

        if vat_status == "without_vat":
            return True

        if vat_amount is None:
            return False

        normalized_vat = str(vat_amount).strip().replace(",", ".")

        try:
            return float(normalized_vat) == 0.0
        except ValueError:
            return False

    def build_without_vat_result(self, document_case: DocumentCase) -> dict:
        return {
            "canonical_counterparty_name": self.get_canonical_counterparty_name(
                document_case
            ),
            "has_non_business_history": False,
            "history_count": 0,
            "history_signal": "skipped_without_vat",
            "preliminary_decision": "llm_only_without_vat",
            "classification_path": "simplified_without_vat",
            "requires_hitl": False,
        }

    def get_history_for_counterparty(self, document_case: DocumentCase) -> list[dict]:
        counterparty_result = document_case.counterparty_result

        if counterparty_result.get("status") != "matched":
            return []

        matched_counterparty = counterparty_result.get("matched_counterparty") or {}

        counterparty_name = (
            matched_counterparty.get("full_name")
            or matched_counterparty.get("short_name")
            or ""
        )

        if not counterparty_name:
            return []

        return self.non_business_repository.find_operations_for_counterparty(
            counterparty_name
        )

    def has_history_for_counterparty(self, document_case: DocumentCase) -> bool:
        return len(document_case.history_operations) > 0

    def get_canonical_counterparty_name(self, document_case: DocumentCase) -> str | None:
        counterparty_result = document_case.counterparty_result

        if counterparty_result.get("status") != "matched":
            return None

        matched_counterparty = counterparty_result.get("matched_counterparty") or {}

        return (
            matched_counterparty.get("full_name")
            or matched_counterparty.get("short_name")
            or None
        )

    def summarize_history(self, document_case: DocumentCase) -> dict:
        history = document_case.history_operations

        if not history:
            return {
                "has_history": False,
                "history_count": 0,
                "business_statuses": [],
            }

        statuses = []
        for item in history:
            status = item.get("business_status")
            if status and status not in statuses:
                statuses.append(status)

        return {
            "has_history": True,
            "history_count": len(history),
            "business_statuses": statuses,
        }

    def get_history_status_set(self, document_case: DocumentCase) -> set[str]:
        statuses = set()

        for item in document_case.history_operations:
            status = item.get("business_status")
            if status:
                statuses.add(status)

        return statuses

    def build_history_based_result(self, document_case: DocumentCase) -> dict:
        canonical_name = self.get_canonical_counterparty_name(document_case)

        if not canonical_name:
            return {
                "canonical_counterparty_name": None,
                "has_non_business_history": False,
                "history_count": 0,
                "history_signal": "no_matched_counterparty",
                "preliminary_decision": "not_identified",
                "classification_path": "history_based",
                "requires_hitl": True,
            }

        history_operations = self.non_business_repository.find_operations_for_counterparty(
            canonical_name
        )

        if not history_operations:
            return {
                "canonical_counterparty_name": canonical_name,
                "has_non_business_history": False,
                "history_count": 0,
                "history_signal": "no_non_business_history",
                "preliminary_decision": "no_history_signal",
                "classification_path": "history_based",
                "requires_hitl": True,
            }

        return {
            "canonical_counterparty_name": canonical_name,
            "has_non_business_history": True,
            "history_count": len(history_operations),
            "history_signal": "counterparty_found_in_non_business_history",
            "preliminary_decision": "non_business_history_signal",
            "classification_path": "history_based",
            "requires_hitl": False,
        }

    def build_non_business_history_signal(self, document_case: DocumentCase) -> dict:
        canonical_name = self.get_canonical_counterparty_name(document_case)

        if not canonical_name:
            return {
                "has_non_business_history": False,
                "history_count": 0,
                "signal": "no_matched_counterparty",
                "requires_hitl": True,
            }

        operations = self.non_business_repository.find_operations_for_counterparty(
            canonical_name
        )

        if not operations:
            return {
                "has_non_business_history": False,
                "history_count": 0,
                "signal": "no_non_business_history",
                "requires_hitl": True,
            }

        return {
            "has_non_business_history": True,
            "history_count": len(operations),
            "signal": "counterparty_found_in_non_business_history",
            "requires_hitl": False,
        }

    def load_policy_prompt(self) -> str:
        prompt_path = Path("app/prompts/buhgalter_agent_policy.txt")

        if not prompt_path.exists():
            raise FileNotFoundError(f"Policy prompt not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")

    def classify_business_operation_with_llm(self, document_case: DocumentCase) -> dict:
        policy_prompt = self.load_policy_prompt()
        extracted = document_case.extracted_data
        base_signal = document_case.business_operation_result

        simplified_without_vat = (
            base_signal.get("classification_path") == "simplified_without_vat"
        )

        if simplified_without_vat:
            extra_instruction = """
This document is explicitly WITHOUT VAT.
vat_amount is 0.00 and vat_status is without_vat.
For this document, classify the operation only based on:
- service description
- accounting policy rules

Do not require HITL only because there is no historical non-business signal.
Use HITL only if the description is ambiguous or the decision cannot be made confidently.
"""
        else:
            extra_instruction = """
Use the historical non-business signal as an additional factor.
If the historical signal and the service description conflict, require HITL.
"""

        prompt = f"""
{policy_prompt}

Current document data:
supplier_name: {extracted.get("supplier_name")}
canonical_counterparty_name: {self.get_canonical_counterparty_name(document_case)}
description: {extracted.get("description")}
total_amount: {extracted.get("total_amount")}
vat_amount: {extracted.get("vat_amount")}
vat_status: {extracted.get("vat_status")}

Classification path:
classification_path: {base_signal.get("classification_path")}
preliminary_decision: {base_signal.get("preliminary_decision")}

Historical non-business signal:
has_non_business_history: {base_signal.get("has_non_business_history")}
history_count: {base_signal.get("history_count")}
history_signal: {base_signal.get("history_signal")}

Additional instruction:
{extra_instruction}
"""

        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()

        raw_response = response.json().get("response", "").strip()

        cleaned_response = (
            raw_response
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            return {
                "policy_decision": "not_identified",
                "final_decision": "not_identified",
                "confidence": 0.0,
                "requires_hitl": True,
                "reason": f"Model did not return valid JSON: {raw_response}",
            }