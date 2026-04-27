from pathlib import Path

from app.agents.buhgalter_agent import BuhgalterAgent
from app.agents.parser_agent import ParserAgent
from app.agents.validator_agent import ValidatorAgent
from app.storage.case_storage import CaseStorage


def main() -> None:
    parser_agent = ParserAgent()
    buhgalter_agent = BuhgalterAgent()
    validator_agent = ValidatorAgent()
    case_storage = CaseStorage()

    inbox_path = Path("data/inbox")
    files = [item for item in inbox_path.iterdir() if item.is_file()]

    if not files:
        print("No files found in data/inbox")
        return

    first_file = files[0]
    print(f"Testing full flow with file: {first_file.name}")

    document_case = parser_agent.parse_document(first_file)
    document_case = buhgalter_agent.enrich_document_case(document_case)
    document_case = validator_agent.validate(document_case)
    output_path = case_storage.save(document_case)

    print("\n=== DocumentCase after ParserAgent + BuhgalterAgent + ValidatorAgent ===")
    print(f"file_name: {document_case.file_name}")
    print(f"file_type: {document_case.file_type}")
    print(f"final_status: {document_case.final_status}")
    print(f"hitl_status: {document_case.hitl_status}")

    print("\nExtracted data:")
    print(document_case.extracted_data)

    print("\nCounterparty result:")
    print(document_case.counterparty_result)

    print("\nHistory operations count:")
    print(len(document_case.history_operations))

    print("\nBusiness operation result:")
    print(document_case.business_operation_result)

    print("\nValidation result:")
    print(document_case.validation_result)

    print("\nSaved JSON:")
    print(output_path)


if __name__ == "__main__":
    main()