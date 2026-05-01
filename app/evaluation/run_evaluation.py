import json
from datetime import datetime
from pathlib import Path

from app.evaluation.evaluator import EvaluationRunner
from app.observability.langfuse_client import (
    build_trace_context,
    create_current_trace_score,
    flush_langfuse,
    observe,
)


@observe(name="run_golden_dataset_evaluation")
def run_golden_dataset_evaluation() -> dict:
    runner = EvaluationRunner()
    report = runner.run()

    create_current_trace_score(
        name="golden_dataset_accuracy",
        value=report["accuracy"],
        comment=(
            f"Golden Dataset evaluation: "
            f"{report['passed_cases']}/{report['total_cases']} cases passed"
        ),
    )

    return report


def main() -> None:
    session_id = "evaluation-golden-dataset"

    build_trace_context(
        session_id=session_id,
        user_id="local-user",
        tags=["evaluation", "golden-dataset", "document-to-erp"],
        metadata={
            "project": "document_to_erp_multiagent",
            "evaluation_type": "golden_dataset_deterministic",
        },
    )

    report = run_golden_dataset_evaluation()

    output_dir = Path("data/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "evaluation_report.json"

    report_with_metadata = {
        "metadata": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "evaluation_type": "golden_dataset_deterministic",
            "description": (
                "Deterministic evaluation of counterparty matching, "
                "business decision, and HITL routing against a small golden dataset."
            ),
            "langfuse_score": {
                "session_id": session_id,
                "score_name": "golden_dataset_accuracy",
                "score_value": report["accuracy"],
                "score_scope": "current_trace",
            },
        },
        "report": report,
    }

    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(
            report_with_metadata,
            file_obj,
            ensure_ascii=False,
            indent=2,
        )

    flush_langfuse()

    print("\n=== Evaluation Report ===")
    print(f"Total cases: {report['total_cases']}")
    print(f"Passed cases: {report['passed_cases']}")
    print(f"Failed cases: {report['failed_cases']}")
    print(f"Accuracy: {report['accuracy']}")

    print("\nLangfuse score:")
    print(f"session_id: {session_id}")
    print("score_name: golden_dataset_accuracy")
    print(f"score_value: {report['accuracy']}")
    print("score_scope: current_trace")

    print("\nDetails:")
    for item in report["details"]:
        status = "PASSED" if item["passed"] else "FAILED"
        print(f"- {item['case_id']}: {status}")

        if not item["passed"]:
            print(f"  Expected: {item.get('expected')}")
            print(f"  Actual:   {item.get('actual')}")
            print(f"  Checks:   {item.get('checks')}")

    print("\nSaved evaluation report:")
    print(output_path)


if __name__ == "__main__":
    main()