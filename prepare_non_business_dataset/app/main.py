from app.cleaner import (
    clean_rows,
    find_input_excel,
    keep_required_columns,
    load_excel,
    save_outputs,
)


def main() -> None:
    input_file = find_input_excel()
    print(f"Input file found: {input_file.name}")

    df = load_excel(input_file)
    print(f"Original rows: {len(df)}")
    print(f"Original columns: {len(df.columns)}")

    df = keep_required_columns(df)
    df = clean_rows(df)

    print(f"Cleaned rows: {len(df)}")
    print(f"Cleaned columns: {len(df.columns)}")

    xlsx_path, csv_path = save_outputs(df)

    print(f"Saved XLSX: {xlsx_path}")
    print(f"Saved CSV: {csv_path}")


if __name__ == "__main__":
    main()