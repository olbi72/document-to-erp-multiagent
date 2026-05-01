from pathlib import Path

from app.agents.buhgalter_agent import BuhgalterAgent
from app.agents.parser_agent import ParserAgent
from app.agents.validator_agent import ValidatorAgent
from app.config import settings
from app.observability.langfuse_client import (
    build_trace_context,
    flush_langfuse,
    observe,
)
from app.storage.case_storage import CaseStorage

@observe(name="parser_agent_parse_document")
def run_parser_agent(parser_agent: ParserAgent, file_path: Path):
    return parser_agent.parse_document(file_path)


@observe(name="buhgalter_agent_enrich_document_case")
def run_buhgalter_agent(buhgalter_agent: BuhgalterAgent, document_case):
    return buhgalter_agent.enrich_document_case(document_case)


@observe(name="validator_agent_validate")
def run_validator_agent(validator_agent: ValidatorAgent, document_case):
    return validator_agent.validate(document_case)


@observe(name="case_storage_save")
def run_case_storage(case_storage: CaseStorage, document_case):
    return case_storage.save(document_case)

@observe(name="process_document")
def process_document(file_path: Path) -> dict:
    parser_agent = ParserAgent()
    buhgalter_agent = BuhgalterAgent()
    validator_agent = ValidatorAgent()
    case_storage = CaseStorage()

    document_case = run_parser_agent(parser_agent, file_path)
    document_case = run_buhgalter_agent(buhgalter_agent, document_case)
    document_case = run_validator_agent(validator_agent, document_case)
    output_path = run_case_storage(case_storage, document_case)

    return {
        "file_name": document_case.file_name,
        "file_type": document_case.file_type,
        "final_status": document_case.final_status,
        "hitl_status": document_case.hitl_status,
        "saved_json": str(output_path),
        "extracted_data": document_case.extracted_data,
        "counterparty_result": document_case.counterparty_result,
        "history_operations_count": len(document_case.history_operations),
        "business_operation_result": document_case.business_operation_result,
        "validation_result": document_case.validation_result,
    }


def main() -> None:
    inbox_path = Path(settings.input_dir)

    files = [
        item
        for item in inbox_path.iterdir()
        if item.is_file() and item.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]
    ]

    if not files:
        print(f"No document files found in {settings.input_dir}")
        return

    first_file = files[0]
    print(f"Testing full flow with file: {first_file.name}")

    build_trace_context(
        session_id=f"document-processing-{first_file.stem}",
        user_id="local-user",
        tags=["document-to-erp", "mvp", "hitl"],
        metadata={
            "project": "document_to_erp_multiagent",
            "pipeline_version": "mvp_v1",
            "file_name": first_file.name,
            "source_file": str(first_file),
        },
    )

    result = process_document(first_file)
    flush_langfuse()

    print("\n=== DocumentCase after ParserAgent + BuhgalterAgent + ValidatorAgent ===")
    print(f"file_name: {result['file_name']}")
    print(f"file_type: {result['file_type']}")
    print(f"final_status: {result['final_status']}")
    print(f"hitl_status: {result['hitl_status']}")

    print("\nExtracted data:")
    print(result["extracted_data"])

    print("\nCounterparty result:")
    print(result["counterparty_result"])

    print("\nHistory operations count:")
    print(result["history_operations_count"])

    print("\nBusiness operation result:")
    print(result["business_operation_result"])

    print("\nValidation result:")
    print(result["validation_result"])

    print("\nSaved JSON:")
    print(result["saved_json"])


if __name__ == "__main__":
    main()