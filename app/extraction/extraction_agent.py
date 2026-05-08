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
            timeout=120,
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

        without_vat_markers = [
            "без пдв",
            "без п.д.в",
            "без податку на додану вартість",
            "операція без пдв",
            "пдв: без пдв",
            "пдв без пдв",
        ]

        vat_amount = data.get("vat_amount")
        vat_amount_text = str(vat_amount).lower().strip() if vat_amount is not None else ""

        has_without_vat_marker = any(
            marker in document_text_lower
            for marker in without_vat_markers
        )

        vat_field_says_without_vat = any(
            marker in vat_amount_text
            for marker in without_vat_markers
        ) or vat_amount_text in ["безпдв", "без пдв", "no vat", "without vat"]

        if has_without_vat_marker or vat_field_says_without_vat:
            data["vat_amount"] = "0.00"
            data["vat_status"] = "without_vat"

        return data