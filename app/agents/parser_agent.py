from pathlib import Path

from app.ingestion.file_detector import FileDetector
from app.parsing.docling_client import DoclingClient
from app.extraction.extraction_agent import ExtractionAgent
from app.models.document_case import DocumentCase


class ParserAgent:
    def __init__(self) -> None:
        self.file_detector = FileDetector()
        self.docling_client = DoclingClient()
        self.extraction_agent = ExtractionAgent()

    def parse_document(self, file_path: str | Path) -> DocumentCase:
        path = Path(file_path)

        file_type = self.file_detector.detect(path)
        document_text = self.docling_client.parse(path)
        extracted_data = self.extraction_agent.extract(document_text)

        return DocumentCase(
            source_file=str(path),
            file_name=path.name,
            file_type=file_type,
            document_text=document_text,
            extracted_data=extracted_data,
            final_status="parsed",
        )