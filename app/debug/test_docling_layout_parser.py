from pathlib import Path
import json
import requests
from PIL import Image

from app.config import settings


FILE_PATH = Path("data/inbox/1000dribnyts.png")


def get_docling_json(file_path: Path) -> dict:
    url = f"{settings.docling_base_url}/v1/convert/file"

    with file_path.open("rb") as file_obj:
        response = requests.post(
            url,
            files={"files": (file_path.name, file_obj)},
            data={
                "to_formats": "json",
                "do_ocr": "true",
                "force_ocr": "false",
                "ocr_engine": "tesseract",
                "ocr_lang": ["ukr", "eng"],
                "do_table_structure": "true",
                "table_mode": "accurate",
                "table_cell_matching": "false",
                "pipeline": "standard",
            },
            timeout=120,
        )

    response.raise_for_status()
    return response.json()["document"]["json_content"]


def extract_text_blocks(docling_json: dict) -> list[dict]:
    blocks = []

    for item in docling_json.get("texts", []):
        text = (item.get("text") or "").strip()
        if not text:
            continue

        prov = item.get("prov") or []
        if not prov:
            continue

        bbox = prov[0].get("bbox") or {}

        blocks.append(
            {
                "text": text,
                "x1": float(bbox.get("l", 0)),
                "y_top": float(bbox.get("t", 0)),
                "x2": float(bbox.get("r", 0)),
                "y_bottom": float(bbox.get("b", 0)),
            }
        )

    return blocks


def group_blocks_into_rows(blocks: list[dict], y_tolerance: float = 18.0) -> list[list[dict]]:
    sorted_blocks = sorted(blocks, key=lambda b: -b["y_top"])

    rows: list[list[dict]] = []

    for block in sorted_blocks:
        placed = False

        for row in rows:
            row_y = sum(item["y_top"] for item in row) / len(row)

            if abs(block["y_top"] - row_y) <= y_tolerance:
                row.append(block)
                placed = True
                break

        if not placed:
            rows.append([block])

    for row in rows:
        row.sort(key=lambda b: b["x1"])

    return rows


def print_rows(rows: list[list[dict]]) -> None:
    for index, row in enumerate(rows, start=1):
        row_text = " | ".join(item["text"] for item in row)
        print(f"{index:03d}: {row_text}")
def split_rows_into_sections(rows: list[list[dict]]) -> dict:
    sections = {
        "header": [],
        "counterparties": [],
        "item_rows": [],
        "totals": [],
        "footer": [],
    }

    current_section = "header"

    for row in rows:
        row_text = " | ".join(item["text"] for item in row)
        row_text_lower = row_text.lower()

        if "постачальник" in row_text_lower or "покупець" in row_text_lower:
            current_section = "counterparties"

        if any(
            marker in row_text_lower
            for marker in [
                "загальна сума",
                "знижка",
                "сума без пдв",
                "пдв",
                "сума з пдв",
                "всього до сплати",
            ]
        ):
            current_section = "totals"

        if any(
            marker in row_text_lower
            for marker in [
                "відпустив",
                "отримав",
                "підпис",
            ]
        ):
            current_section = "footer"

        if current_section == "counterparties":
            if not any(
                marker in row_text_lower
                for marker in [
                    "постачальник",
                    "покупець",
                    "іпн",
                    "єдрпоу",
                    "адреса",
                    "телефон",
                ]
            ):
                if row and row[0]["y_top"] < 840:
                    current_section = "item_rows"

        sections[current_section].append(row_text)

    return sections


def print_sections(sections: dict) -> None:
    for section_name, section_rows in sections.items():
        print(f"\n=== {section_name.upper()} ===\n")
        for row in section_rows:
            print(row)

def get_section_bbox(section_rows: list[str], rows: list[list[dict]]) -> dict | None:
    matched_blocks = []

    for row in rows:
        row_text = " | ".join(item["text"] for item in row)

        if row_text in section_rows:
            matched_blocks.extend(row)

    if not matched_blocks:
        return None

    return {
        "x1": min(block["x1"] for block in matched_blocks),
        "y_top": max(block["y_top"] for block in matched_blocks),
        "x2": max(block["x2"] for block in matched_blocks),
        "y_bottom": min(block["y_bottom"] for block in matched_blocks),
    }


def crop_section(
    image_path: Path,
    bbox: dict,
    output_path: Path,
    padding: int = 30,
) -> None:
    image = Image.open(image_path)

    image_width, image_height = image.size

    scale_x = image_width / 1053
    scale_y = image_height / 1493

    left = max(0, int((bbox["x1"] * scale_x) - padding))
    right = min(image_width, int((bbox["x2"] * scale_x) + padding))

    top = max(0, int(((1493 - bbox["y_top"]) * scale_y) - padding))
    bottom = min(image_height, int(((1493 - bbox["y_bottom"]) * scale_y) + padding))

    cropped = image.crop((left, top, right, bottom))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output_path)

    print(f"Saved crop: {output_path}")


def main() -> None:
    docling_json = get_docling_json(FILE_PATH)

    print("Tables count:", len(docling_json.get("tables", [])))
    print("Texts count:", len(docling_json.get("texts", [])))

    blocks = extract_text_blocks(docling_json)
    rows = group_blocks_into_rows(blocks)

    print("\n=== Reconstructed rows from bbox ===\n")
    print_rows(rows)
    sections = split_rows_into_sections(rows)
    print_sections(sections)
    output_dir = Path("data/debug/crops")

    item_bbox = get_section_bbox(sections.get("item_rows", []), rows)
    totals_bbox = get_section_bbox(sections.get("totals", []), rows)

    if item_bbox:
        crop_section(
            image_path=FILE_PATH,
            bbox=item_bbox,
            output_path=output_dir / "1000dribnyts_items.png",
            padding=50,
        )

    if totals_bbox:
        crop_section(
            image_path=FILE_PATH,
            bbox=totals_bbox,
            output_path=output_dir / "1000dribnyts_totals.png",
            padding=50,
        )


if __name__ == "__main__":
    main()