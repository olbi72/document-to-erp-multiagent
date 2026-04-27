from pathlib import Path

import pandas as pd

from rapidfuzz import fuzz

from app.config import settings


class NonBusinessRepository:
    def __init__(self) -> None:
        self.file_path = Path(settings.non_business_operations_file)
        self.df = self._load_dataframe()

    def _load_dataframe(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Non-business operations file not found: {self.file_path}"
            )

        df = pd.read_excel(self.file_path)

        required_columns = [
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

        missing_columns = [
            column for column in required_columns if column not in df.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        df = df[required_columns].copy()

        text_columns = [
            "Дата",
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

        df["supplier_name_normalized"] = df["Контрагент"].apply(self._normalize_name)
        df["operation_text"] = df.apply(self._build_operation_text, axis=1)
        df["operation_text_normalized"] = df["operation_text"].apply(
            self._normalize_text
        )
        df["business_status"] = df["НалоговоеНазначениеДоходовИЗатрат"].apply(
            self._map_business_status
        )

        return df

    def _normalize_name(self, value: str) -> str:
        normalized = value.lower().strip()
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

    def _normalize_text(self, value: str) -> str:
        normalized = value.lower().strip()
        replacements = ['"', "'", "«", "»", ",", ".", "’", "(", ")", ";", ":"]

        for char in replacements:
            normalized = normalized.replace(char, " ")

        normalized = " ".join(normalized.split())
        return normalized

    def _build_operation_text(self, row: pd.Series) -> str:
        parts = [
            row.get("Комментарий", ""),
            row.get("Номенклатура", ""),
            row.get("Содержание", ""),
        ]
        parts = [
            part.strip()
            for part in parts
            if isinstance(part, str) and part.strip()
        ]
        return " | ".join(parts)

    def _map_business_status(self, value: str) -> str:
        normalized = self._normalize_text(value)

        if "нехоз" in normalized:
            return "non_business"

        if normalized:
            return "business"

        return "not_identified"

    def find_operations_for_counterparty(self, counterparty_name: str) -> list[dict]:
        normalized_name = self._normalize_name(counterparty_name)

        if not normalized_name:
            return []

        matches = self.df[self.df["supplier_name_normalized"] == normalized_name]

        if matches.empty:
            return []

        return matches.to_dict(orient="records")

    def find_similar_operations(
            self,
            description: str | None,
            history_operations: list[dict],
            limit: int = 5,
    ) -> list[dict]:
        normalized_description = self._normalize_text(description or "")

        if not normalized_description or not history_operations:
            return []

        scored_operations = []

        for item in history_operations:
            operation_text = item.get("operation_text_normalized", "")
            score = fuzz.token_sort_ratio(normalized_description, operation_text)

            result_item = {
                "date": item.get("Дата"),
                "counterparty": item.get("Контрагент"),
                "operation_text": item.get("operation_text"),
                "expense_type": item.get("СтатьяЗатрат"),
                "tax_purpose": item.get("НалоговоеНазначение"),
                "tax_income_expense_purpose": item.get("НалоговоеНазначениеДоходовИЗатрат"),
                "document_number": item.get("НомерВходящегоДокумента"),
                "amount": item.get("СуммаДокумента"),
                "business_status": item.get("business_status"),
                "similarity_score": score,
            }

            scored_operations.append(result_item)

        scored_operations.sort(key=lambda item: item["similarity_score"], reverse=True)
        return scored_operations[:limit]

    def has_non_business_history(self, counterparty_name: str) -> bool:
        operations = self.find_operations_for_counterparty(counterparty_name)
        return len(operations) > 0
