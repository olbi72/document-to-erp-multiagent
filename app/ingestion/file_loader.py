from pathlib import Path

from app.config import settings


class FileLoader:
    def get_files(self) -> list[Path]:
        input_path = Path(settings.input_dir)

        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_path}")

        files = [item for item in input_path.iterdir() if item.is_file()]
        return files