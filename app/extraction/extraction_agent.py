import json
from pathlib import Path

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

            return data

        except json.JSONDecodeError as error:
            raise ValueError(f"Model did not return valid JSON: {raw_response}") from error