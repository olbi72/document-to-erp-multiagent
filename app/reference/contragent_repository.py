from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

from app.config import settings


class ContragentRepository:
    def __init__(self) -> None:
        self.file_path = Path(settings.contragents_file)
        self.df = self._load_dataframe()

    def _load_dataframe(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Contragents file not found: {self.file_path}")

        df = pd.read_excel(self.file_path)

        column_mapping = {
            "Найменування": "short_name",
            "Повне найменування": "full_name",
            "ИНН": "inn",
            "Код по ЕГРПОУ/ДРФО": "edrpou",
        }

        df = df.rename(columns=column_mapping)

        required_columns = ["id", "short_name", "full_name", "inn", "edrpou"]
        for column in required_columns:
            if column not in df.columns:
                df[column] = None

        df = df[required_columns].copy()

        df["id"] = df["id"].apply(self._safe_to_string)
        df["short_name"] = df["short_name"].fillna("").astype(str).str.strip()
        df["full_name"] = df["full_name"].fillna("").astype(str).str.strip()

        df["inn"] = df["inn"].apply(self._normalize_code).astype(object)
        df["edrpou"] = df["edrpou"].apply(self._normalize_code).astype(object)

        df["inn"] = df["inn"].where(pd.notna(df["inn"]), None)
        df["edrpou"] = df["edrpou"].where(pd.notna(df["edrpou"]), None)

        df["normalized_name"] = df["short_name"].apply(self._normalize_name)

        return df

    def _safe_to_string(self, value: Any) -> str:
        if pd.isna(value):
            return ""

        return str(value).strip()

    def _normalize_code(self, value: Any) -> str | None:
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        if not value_str:
            return None

        if value_str.endswith(".0"):
            value_str = value_str[:-2]

        digits_only = "".join(char for char in value_str if char.isdigit())

        return digits_only or None

    def _normalize_name(self, value: str | None) -> str:
        if value is None or pd.isna(value):
            return ""

        normalized = str(value).lower().strip()

        replacements = ['"', "'", "«", "»", ",", ".", "’"]
        for char in replacements:
            normalized = normalized.replace(char, " ")

        legal_forms = [
            "товариство з обмеженою відповідальністю",
            "тов",
            "тзов",
            "пп",
            "прат",
            "пат",
            "дп",
            "фоп",
        ]

        parts = normalized.split()
        parts = [part for part in parts if part not in legal_forms]

        normalized = " ".join(parts)
        normalized = " ".join(normalized.split())

        return normalized

    def _row_to_dict(self, row: pd.Series) -> dict:
        result = row.to_dict()

        for key, value in result.items():
            if pd.isna(value):
                result[key] = None

        return result

    def find_by_edrpou(self, edrpou: str | None) -> dict | None:
        normalized = self._normalize_code(edrpou)

        if not normalized:
            return None

        matches = self.df[self.df["edrpou"] == normalized]

        if matches.empty:
            return None

        return self._row_to_dict(matches.iloc[0])

    def find_by_inn(self, inn: str | None) -> dict | None:
        normalized = self._normalize_code(inn)

        if not normalized:
            return None

        matches = self.df[self.df["inn"] == normalized]

        if matches.empty:
            return None

        return self._row_to_dict(matches.iloc[0])

    def find_name_candidates(self, supplier_name: str | None, limit: int = 5) -> list[dict]:
        normalized_input = self._normalize_name(supplier_name)

        if not normalized_input:
            return []

        candidates = []

        for _, row in self.df.iterrows():
            score = fuzz.token_sort_ratio(
                normalized_input,
                row["normalized_name"],
            )

            candidate = {
                "id": row["id"],
                "short_name": row["short_name"],
                "full_name": row["full_name"],
                "inn": row["inn"],
                "edrpou": row["edrpou"],
                "normalized_name": row["normalized_name"],
                "score": score,
            }

            for key, value in candidate.items():
                if pd.isna(value):
                    candidate[key] = None

            candidates.append(candidate)

        candidates.sort(key=lambda item: item["score"], reverse=True)

        return candidates[:limit]