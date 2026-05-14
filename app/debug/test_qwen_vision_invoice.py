import base64
import json
from pathlib import Path

import requests

from app.config import settings


IMAGE_PATH = Path("data/inbox/1000dribnyts.png")
MODEL = "qwen2.5vl:7b"


def encode_image_base64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def main() -> None:
    image_base64 = encode_image_base64(IMAGE_PATH)

    prompt = """
You are an invoice extraction system.

Extract data from the Ukrainian invoice image.

Return only valid JSON with this structure:

{
  "document_kind": "invoice",
  "document_type": null,
  "document_number": null,
  "document_date": null,
  "supplier_name": null,
  "supplier_ipn": null,
  "supplier_edrpou": null,
  "customer_name": null,
  "customer_ipn": null,
  "customer_edrpou": null,
  "items": [
    {
      "line_number": null,
      "item_name": null,
      "unit": null,
      "quantity": null,
      "unit_price_without_vat": null,
      "line_total_without_vat": null
    }
  ],
  "totals": {
    "total_without_vat_before_discount": null,
    "discount_amount": null,
    "total_without_vat_after_discount": null,
    "vat_rate": null,
    "vat_amount": null,
    "total_with_vat": null
  },
  "extraction_quality": {
    "items_complete": true,
    "confidence": 0.0,
    "problems": []
  }
}

Rules:
- Extract all visible item rows.
- Do not invent item rows.
- Do not copy document totals into item rows.
- Amounts must be strings.
- If a field is not visible, use null.
- If the table is unclear, still extract what you can and list problems.
- Return only JSON.
- Do not use markdown.
"""

    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0
            },
        },
        timeout=300,
    )

    response.raise_for_status()

    result = response.json()
    raw_text = result.get("response", "").strip()

    print("=== RAW MODEL OUTPUT ===")
    print(raw_text)

    cleaned = (
        raw_text
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        print("\nERROR: Model did not return valid JSON")
        return

    print("\n=== PARSED JSON ===")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))

    output_path = Path("data/debug/qwen_vision_invoice_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved parsed JSON to: {output_path}")


if __name__ == "__main__":
    main()