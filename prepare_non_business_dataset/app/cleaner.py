from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "Дата",
    "Контрагент",
    "Комментарий",
    "Номенклатура",
    "Содержание",
    "СтатьяЗатрат",
    "НалоговоеНазначение",
    "НалоговоеНазначениеДоходовИЗатрат",
    "НомерВходящегоДокумента",
    "СуммаДокумента",
]


OUTPUT_XLSX_NAME = "non_business_operations_mvp.xlsx"
OUTPUT_CSV_NAME = "non_business_operations_mvp.csv"


def find_input_excel(input_dir: str = "input") -> Path:
    input_path = Path(input_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_path}")

    excel_files = [
        file_path
        for file_path in input_path.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in {".xlsx", ".xls"}
    ]

    if not excel_files:
        raise FileNotFoundError("No Excel files found in input directory")

    return excel_files[0]


def load_excel(file_path: Path) -> pd.DataFrame:
    df = pd.read_excel(file_path)
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    return df


def keep_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    return df[REQUIRED_COLUMNS].copy()


def clean_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    text_columns = [
        "Контрагент",
        "Комментарий",
        "Номенклатура",
        "Содержание",
        "СтатьяЗатрат",
        "НалоговоеНазначение",
        "НалоговоеНазначениеДоходовИЗатрат",
        "НомерВходящегоДокумента",
    ]

    for column in text_columns:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df = df.dropna(how="all")

    meaningful_mask = (
        (df["Контрагент"] != "")
        | (df["Комментарий"] != "")
        | (df["Номенклатура"] != "")
        | (df["Содержание"] != "")
    )

    df = df[meaningful_mask].copy()

    return df.reset_index(drop=True)


def save_outputs(df: pd.DataFrame, output_dir: str = "output") -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    xlsx_path = output_path / OUTPUT_XLSX_NAME
    csv_path = output_path / OUTPUT_CSV_NAME

    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return xlsx_path, csv_path