import base64
from pathlib import Path

import requests

from app.config import settings


IMAGE_PATH = Path("data/inbox/1000dribnyts.png")
MODEL = "qwen2.5vl:7b"


def main() -> None:
    image_base64 = base64.b64encode(IMAGE_PATH.read_bytes()).decode("utf-8")

    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": MODEL,
            "prompt": "Look at the image. Return only JSON: {\"document_type\": \"...\", \"document_number\": \"...\"}",
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0
            },
        },
        timeout=600,
    )

    response.raise_for_status()
    result = response.json()

    print(result.get("response", "").strip())


if __name__ == "__main__":
    main()