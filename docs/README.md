# Document to ERP Multi-Agent System

MVP project for automatic processing of work completion acts / service delivery acts.

The system takes a PDF or image from the `data/inbox` folder, processes the document through Docling, extracts structured data using a local LLM via Ollama, matches the supplier against the counterparty database, classifies the transaction as business-related or non-business-related, and generates a JSON result for further processing or manual accountant review.

## Features

* OCR / document parsing via Docling.
* Extraction of structured act details using a local LLM.
* Prompt files stored separately in `app/prompts`.
* Counterparty matching against an Excel-based counterparty database.
* Fuzzy matching of counterparty names using RapidFuzz.
* Check against historical known non-business operations.
* LLM-based transaction classification as:

  * `business`
  * `non_business`
  * `not_identified`
* Rule-based validation of extracted and enriched results.
* HITL flow for accountant review.
* Separate simplified `.review.json` file for the accountant.
* Saving of technical and review JSON files to `data/approved` or `data/review_pending`.
.

---

## Current MVP Flow

```text
data/inbox
    ↓
ParserAgent
    ↓
DoclingClient
    ↓
ExtractionAgent
    ↓
DocumentCase
    ↓
BuhgalterAgent
    ↓
ValidatorAgent
    ↓
CaseStorage
    ↓
validated       → data/approved
review_required → data/review_pending
    ↓
ReviewPackageBuilder
    ↓
accountant fills accountant_answer
    ↓
ReviewProcessor
    ↓
data/approved
```

---

## Project Structure

```text
document_to_erp_multiagent/
├── app/
│   ├── config.py
│   ├── main.py
│   │
│   ├── agents/
│   │   ├── parser_agent.py
│   │   ├── buhgalter_agent.py
│   │   └── validator_agent.py
│   │
│   ├── extraction/
│   │   └── extraction_agent.py
│   │
│   ├── hitl/
│   │   ├── review_processor.py
│   │   └── process_first_review.py
│   │
│   ├── ingestion/
│   │   ├── file_loader.py
│   │   └── file_detector.py
│   │
│   ├── models/
│   │   └── document_case.py
│   │
│   ├── parsing/
│   │   └── docling_client.py
│   │
│   ├── prompts/
│   │   ├── extraction_agent_prompt.txt
│   │   └── buhgalter_agent_policy.txt
│   │
│   ├── reference/
│   │   ├── contragent_repository.py
│   │   └── non_business_repository.py
│   │
│   └── storage/
│       ├── case_storage.py
│       └── review_package_builder.py
│
├── data/
│   ├── inbox/
│   ├── review_pending/
│   ├── approved/
│   ├── rejected/
│   └── reference/
│       ├── contragents.xls
│       └── non_business_operations_mvp.xlsx
│
├── requirements.txt
├── .env
└── README.md
```

---

## Main Components

### ParserAgent

`ParserAgent` coordinates the first stage of document processing:

1. detects file type;
2. sends the file to Docling;
3. receives OCR / markdown text;
4. sends text to `ExtractionAgent`;
5. returns a `DocumentCase` object.

### ExtractionAgent

`ExtractionAgent` calls Ollama and extracts structured data from document text.

Expected fields:

```json
{
  "document_type": null,
  "document_number": null,
  "document_date": null,
  "customer_name": null,
  "supplier_name": null,
  "supplier_edrpou": null,
  "supplier_ipn": null,
  "total_amount": null,
  "vat_amount": null,
  "currency": null,
  "description": null
}
```

The prompt is stored separately in:

```text
app/prompts/extraction_agent_prompt.txt
```

### BuhgalterAgent

`BuhgalterAgent` enriches the parsed document with accounting logic:

- resolves counterparty;
- checks non-business history;
- calls LLM for business / non-business classification;
- sets initial HITL requirement.

The accounting policy prompt is stored in:

```text
app/prompts/buhgalter_agent_policy.txt
```

### ValidatorAgent

`ValidatorAgent` performs rule-based checks after `BuhgalterAgent`.

It checks:

- required fields;
- amount parsing;
- `total_amount >= vat_amount`;
- counterparty matching status;
- whether supplier may be confused with customer;
- whether business classification requires HITL.

If a document was already marked as requiring HITL by `BuhgalterAgent`, the validator does not cancel that decision.

### CaseStorage

`CaseStorage` saves processing results.

If the document is validated automatically:

```text
data/approved/*.technical.json
```

If the document requires accountant review:

```text
data/review_pending/*.technical.json
data/review_pending/*.review.json
```

### ReviewPackageBuilder

Creates a simplified JSON file for the accountant.

The accountant should not review the full technical JSON. Instead, the accountant reviews only key document fields and fills one field:

```json
"accountant_answer": null
```

If system decision is `business` or `non_business`, allowed answers are:

```json
["Y", "N"]
```

If system decision is `not_identified`, allowed answers are:

```json
["business", "non_business"]
```

### ReviewProcessor

Processes accountant review files from `data/review_pending`.

It:

1. reads `.review.json`;
2. checks `accountant_answer`;
3. resolves the final business decision;
4. updates the technical JSON;
5. moves final approved files to `data/approved`.

---

## Configuration

Create a `.env` file in the project root.

Example:

```env
OLLAMA_BASE_URL=http://localhost:11434
PARSER_MODEL=gemma3:4b
BUHGALTER_MODEL=gemma3:4b

DOCLING_BASE_URL=http://localhost:5002

INPUT_DIR=data/inbox
REVIEW_PENDING_DIR=data/review_pending
APPROVED_DIR=data/approved
REJECTED_DIR=data/rejected

CONTRAGENTS_FILE=data/reference/contragents.xls
NON_BUSINESS_OPERATIONS_FILE=data/reference/non_business_operations_mvp.xlsx

CLIENT_NAME=
CLIENT_EDRPOU=
CLIENT_IPN=
```

`CLIENT_NAME`, `CLIENT_EDRPOU`, and `CLIENT_IPN` are used as guardrails so the model does not confuse the customer with the supplier.

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd document_to_erp_multiagent
```

### 2. Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Prepare local services

Start Docling locally and make sure it is available at:

```text
http://localhost:5002
```

Start Ollama and make sure it is available at:

```text
http://localhost:11434
```

Check available Ollama models:

```bash
ollama list
```

---

## Usage

### 1. Put a document into inbox

Supported formats:

```text
.pdf
.png
.jpg
.jpeg
```

Place the file into:

```text
data/inbox
```

### 2. Run main pipeline

```bash
python -m app.main
```

The current MVP version processes the first file from `data/inbox`.

### 3. Check output

If the document is automatically validated:

```text
data/approved/<file_name>.technical.json
```

If the document requires accountant review:

```text
data/review_pending/<file_name>.technical.json
data/review_pending/<file_name>.review.json
```

### 4. Accountant review

Open the `.review.json` file and edit only this field:

```json
"accountant_answer": null
```

If the system already classified the operation as `business` or `non_business`:

```json
"accountant_answer": "Y"
```

or:

```json
"accountant_answer": "N"
```

If the system returned `not_identified`:

```json
"accountant_answer": "business"
```

or:

```json
"accountant_answer": "non_business"
```

### 5. Process accountant review

```bash
python -m app.hitl.process_first_review
```

After processing, approved files are saved to:

```text
data/approved
```

## Reference Data

### Counterparties

Expected file:

```text
data/reference/contragents.xls
```

Used by:

```text
app/reference/contragent_repository.py
```

### Non-business operations history

Expected file:

```text
data/reference/non_business_operations_mvp.xlsx
```

Used by:

```text
app/reference/non_business_repository.py
```

This file contains known non-business operations and is used as a historical signal.

---

## Requirements

Current `requirements.txt`:

```text
pydantic>=2.0
pydantic-settings>=2.0
python-dotenv>=1.0
requests>=2.31.0
pandas
xlrd
rapidfuzz
```

---

## Current Limitations

This is an MVP version. Current limitations:

- `app/main.py` processes only the first file from `data/inbox`.
- Accountant review is done by manually editing `.review.json`.
- There is no web UI for HITL yet.
- Original source files are not automatically moved to archive.
- There is no separate ERP export format yet.
- Date extraction can still be unstable because of OCR / LLM noise.
- No unit tests are implemented yet.
- No centralized logging is implemented yet.

---

## Next Steps

Recommended next development steps:

1. Process all files from `data/inbox`, not only the first file.
2. Move original documents after processing to archive / processed folders.
3. Add final ERP export JSON without technical metadata.
4. Add stricter date validation.
5. Add document number validation.
6. Add UI for accountant review.
7. Add logging and error handling.
8. Add unit tests for repositories, validator, storage, and HITL processor.
9. Add support for batch processing.
10. Add README examples with real anonymized test cases.

---

## Status

The project is complete as a first working MVP.

It supports the full flow:

```text
document → OCR → extraction → counterparty matching → accounting classification → validation → JSON storage → HITL review → final approved JSON
```

