from pathlib import Path


class FileDetector:
    SUPPORTED_EXTENSIONS = {
        ".pdf": "pdf",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
    }

    def detect(self, file_path: Path) -> str:
        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")

        return self.SUPPORTED_EXTENSIONS[extension]