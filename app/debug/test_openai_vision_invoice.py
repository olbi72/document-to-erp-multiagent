import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


IMAGE_PATH = Path("data/inbox/1000dribnyts.png")
MODEL = "gpt-4.1-mini"


def encode_image_to_data_url(image_path: Path) -> str:
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def main() -> None:
    load_dotenv()

    client = OpenAI()

    image_data_url = encode_image_to_data_url(IMAGE_PATH)

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
- Return only JSON. No markdown.
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_data_url},
                ],
            }
        ],
        temperature=0,
    )
    print("\n=== USAGE ===")
    print(response.usage)
    raw_text = response.output_text.strip()

    print("=== RAW MODEL OUTPUT ===")
    print(raw_text)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print("\nERROR: Model did not return valid JSON")
        return

    print("\n=== PARSED JSON ===")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    output_path = Path("data/debug/openai_vision_invoice_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved parsed JSON to: {output_path}")


if __name__ == "__main__":
    main()