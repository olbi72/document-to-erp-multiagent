from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentCase:
    source_file: str
    file_name: str
    file_type: str | None = None

    document_text: str | None = None
    extracted_data: dict[str, Any] = field(default_factory=dict)

    counterparty_result: dict[str, Any] = field(default_factory=dict)
    history_operations: list[dict[str, Any]] = field(default_factory=list)
    business_operation_result: dict[str, Any] = field(default_factory=dict)
    validation_result: dict[str, Any] = field(default_factory=dict)

    hitl_status: str = "not_sent"
    final_status: str = "new"