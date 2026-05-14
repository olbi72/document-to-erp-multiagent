import json
from pathlib import Path
from typing import Any

import requests

from app.config import settings


class ExtractionAgent:
    def __init__(self) -> None:
        self.prompt_path = Path("app/prompts/extraction_agent_prompt.txt")

    def load_prompt_template(self) -> str:
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Extraction prompt not found: {self.prompt_path}")

        return self.prompt_path.read_text(encoding="utf-8")

    def build_prompt(self, document_text: str) -> str:
        prompt_template = self.load_prompt_template()

        return prompt_template.format(
            client_name=settings.client_name,
            client_edrpou=settings.client_edrpou,
            client_ipn=settings.client_ipn,
            document_text=document_text,
        )

    def extract(self, document_text: str) -> dict:
        prompt = self.build_prompt(document_text)

        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.parser_model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=300,
        )

        response.raise_for_status()
        result = response.json()

        raw_response = result.get("response", "").strip()

        if not raw_response:
            raise ValueError("Ollama returned empty response")

        cleaned_response = (
            raw_response
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        try:
            data = json.loads(cleaned_response)

            if data.get("supplier_edrpou") == settings.client_edrpou:
                data["supplier_edrpou"] = None

            if data.get("supplier_ipn") == settings.client_ipn:
                data["supplier_ipn"] = None

            data = self._normalize_without_vat(data, document_text)

            return data

        except json.JSONDecodeError as error:
            raise ValueError(f"Model did not return valid JSON: {raw_response}") from error


    def _normalize_without_vat(
        self,
        data: dict[str, Any],
        document_text: str,
    ) -> dict[str, Any]:
        document_text_lower = document_text.lower()

        def parse_amount(value) -> float | None:
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
                .replace(",", ".")
            )

            try:
                return float(value_str)
            except ValueError:
                return None

        vat_amount = parse_amount(data.get("vat_amount"))

        document_totals_raw = data.get("document_totals_raw") or {}
        raw_document_vat_amount = parse_amount(document_totals_raw.get("vat_amount"))
        vat_included_amount = parse_amount(document_totals_raw.get("vat_included_amount"))

        has_positive_vat = any(
            value is not None and value > 0
            for value in [
                vat_amount,
                raw_document_vat_amount,
                vat_included_amount,
            ]
        )

        if has_positive_vat:
            return data

        strong_without_vat_markers = [
            "операція без пдв",
            "без податку на додану вартість",
            "пдв не нараховується",
            "не є платником пдв",
            "без п.д.в.",
            "без п.д.в",
        ]

        raw_amount_labels = data.get("raw_amount_labels") or []
        raw_amount_labels_text = " ".join(
            str(label).lower()
            for label in raw_amount_labels
        )

        has_strong_without_vat_marker = any(
            marker in document_text_lower
            for marker in strong_without_vat_markers
        )

        label_says_without_vat = "без пдв" in raw_amount_labels_text

        has_vat_total_label = any(
            marker in document_text_lower
            for marker in [
                "пдв 20%",
                "пдв:",
                "сума з пдв",
                "всього з пдв",
                "загальна сума з пдв",
                "в т.ч. пдв",
                "у тому числі пдв",
            ]
        )

        if has_vat_total_label:
            return data

        if has_strong_without_vat_marker or label_says_without_vat:
            data["vat_amount"] = "0.00"
            data["vat_status"] = "without_vat"

        return data