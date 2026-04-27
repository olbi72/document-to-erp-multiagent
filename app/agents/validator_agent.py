from app.config import settings
from app.models.document_case import DocumentCase


class ValidatorAgent:
    REQUIRED_FIELDS = [
        "document_type",
        "document_number",
        "document_date",
        "customer_name",
        "supplier_name",
        "total_amount",
        "vat_amount",
        "currency",
        "description",
    ]

    def validate(self, document_case: DocumentCase) -> DocumentCase:
        business_result = document_case.business_operation_result or {}

        if business_result.get("requires_hitl", True):
            document_case.validation_result = {
                "is_valid": False,
                "requires_hitl": True,
                "flags": ["already_required_by_buhgalter_agent"],
            }
            document_case.hitl_status = "pending"
            document_case.final_status = "review_required"
            return document_case

        flags: list[str] = []

        self._check_required_fields(document_case, flags)
        self._check_amounts(document_case, flags)
        self._check_customer_and_supplier(document_case, flags)
        self._check_counterparty(document_case, flags)
        self._check_business_classification(document_case, flags)

        requires_hitl = len(flags) > 0

        document_case.validation_result = {
            "is_valid": not requires_hitl,
            "requires_hitl": requires_hitl,
            "flags": flags,
        }

        if requires_hitl:
            document_case.hitl_status = "pending"
            document_case.final_status = "review_required"
        else:
            document_case.hitl_status = "not_required"
            document_case.final_status = "validated"

        return document_case

    def _check_required_fields(
        self,
        document_case: DocumentCase,
        flags: list[str],
    ) -> None:
        extracted = document_case.extracted_data

        missing_fields = []

        for field_name in self.REQUIRED_FIELDS:
            value = extracted.get(field_name)

            if value is None:
                missing_fields.append(field_name)
                continue

            if isinstance(value, str) and not value.strip():
                missing_fields.append(field_name)

        if missing_fields:
            flags.append(f"missing_required_fields: {', '.join(missing_fields)}")
    def _check_amounts(
        self,
        document_case: DocumentCase,
        flags: list[str],
    ) -> None:
        extracted = document_case.extracted_data

        total_amount = self._parse_amount(extracted.get("total_amount"))
        vat_amount = self._parse_amount(extracted.get("vat_amount"))

        if total_amount is None:
            flags.append("invalid_total_amount")

        if vat_amount is None:
            flags.append("invalid_vat_amount")

        if total_amount is None or vat_amount is None:
            return

        if total_amount < 0:
            flags.append("negative_total_amount")

        if vat_amount < 0:
            flags.append("negative_vat_amount")

        if total_amount < vat_amount:
            flags.append("total_amount_less_than_vat_amount")

    def _parse_amount(self, value) -> float | None:
        if value is None:
            return None

        value_str = str(value).strip()

        if not value_str:
            return None

        value_str = (
            value_str
            .replace(" ", "")
            .replace("\u00a0", "")
            .replace("грн.", "")
            .replace("грн", "")
            .replace("UAH", "")
            .replace("uah", "")
        )

        if "," in value_str and "." in value_str:
            value_str = value_str.replace(",", "")
        elif "," in value_str:
            value_str = value_str.replace(",", ".")

        try:
            return float(value_str)
        except ValueError:
            return None
    def _check_customer_and_supplier(
        self,
        document_case: DocumentCase,
        flags: list[str],
    ) -> None:
        extracted = document_case.extracted_data

        customer_name = self._normalize_text(extracted.get("customer_name"))
        supplier_name = self._normalize_text(extracted.get("supplier_name"))
        client_name = self._normalize_text(settings.client_name)

        if supplier_name and client_name and supplier_name == client_name:
            flags.append("supplier_may_be_customer")

        if customer_name and client_name and customer_name != client_name:
            flags.append("customer_name_differs_from_client_name")

    def _check_counterparty(
        self,
        document_case: DocumentCase,
        flags: list[str],
    ) -> None:
        counterparty_result = document_case.counterparty_result or {}
        status = counterparty_result.get("status")

        if status == "ambiguous":
            flags.append("counterparty_ambiguous")
        elif status == "not_found":
            flags.append("counterparty_not_found")
        elif status != "matched":
            flags.append("counterparty_not_matched")

    def _check_business_classification(
        self,
        document_case: DocumentCase,
        flags: list[str],
    ) -> None:
        business_result = document_case.business_operation_result or {}

        final_decision = business_result.get("final_decision")
        requires_hitl = business_result.get("requires_hitl", True)

        if not final_decision:
            flags.append("business_classification_missing")
            return

        if final_decision == "not_identified":
            flags.append("business_classification_not_identified")

        if requires_hitl:
            flags.append("business_requires_hitl")

    def _normalize_text(self, value: str | None) -> str:
        if value is None:
            return ""

        normalized = str(value).lower().strip()

        replacements = ['"', "'", "«", "»", ",", ".", "’", "-", "–", "—"]
        for char in replacements:
            normalized = normalized.replace(char, " ")

        normalized = " ".join(normalized.split())

        return normalized