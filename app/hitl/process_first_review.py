from pathlib import Path

from app.config import settings
from app.hitl.review_processor import ReviewProcessor


def main() -> None:
    review_pending_dir = Path(settings.review_pending_dir)

    review_files = sorted(review_pending_dir.glob("*.review.json"))

    if not review_files:
        print("No review files found")
        return

    first_review_file = review_files[0]

    print(f"Processing review file: {first_review_file}")

    processor = ReviewProcessor()
    approved_review_path = processor.process_review_file(first_review_file)

    print("Approved review file:")
    print(approved_review_path)


if __name__ == "__main__":
    main()