from pathlib import Path
import re

import requests

from app.config import settings


class DoclingClient:
    def parse(self, file_path: Path) -> str:
        url = f"{settings.docling_base_url}/v1/convert/file"

        with file_path.open("rb") as file_obj:
            files = {"files": (file_path.name, file_obj)}
            data = {
                "to_formats": "md",
                "do_ocr": "true",
                "ocr_engine": "tesseract",
                "ocr_lang": ["ukr", "eng"],
            }

            response = requests.post(url, files=files, data=data, timeout=120)

        response.raise_for_status()
        result = response.json()

        document = result.get("document", {})
        markdown_text = document.get("md_content", "")

        if not markdown_text:
            raise ValueError(f"Docling returned empty text for file: {file_path.name}")

        cleaned_text = re.sub(
            r"!\[.*?\]\(data:image\/.*?;base64,.*?\)",
            "",
            markdown_text,
            flags=re.DOTALL,
        )

        cleaned_text = cleaned_text.strip()

        if not cleaned_text:
            raise ValueError(f"Docling returned empty cleaned text for file: {file_path.name}")

        return cleaned_text[:4000]