"""Field mapper — renames fields and casts types in tabular data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...logging_config import get_logger

logger = get_logger(__name__)


class FieldMapper:
    """Transforms data fields by renaming and type-casting."""

    @staticmethod
    def map_fields(data: list[dict[str, Any]], mapping: dict[str, str]) -> list[dict[str, Any]]:
        """
        Rename or restructure fields based on a mapping dict.

        Args:
            data: List of row dicts.
            mapping: Dict of {old_name: new_name}. Fields not in mapping are kept as-is.

        Returns:
            New list with renamed fields.
        """
        if not data or not mapping:
            return data

        result: list[dict[str, Any]] = []
        for row in data:
            new_row: dict[str, Any] = {}
            for key, value in row.items():
                new_key = mapping.get(key, key)
                new_row[new_key] = value
            result.append(new_row)
        return result

    @staticmethod
    def cast_types(
        data: list[dict[str, Any]],
        type_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        """
        Cast field values to specified types.

        Args:
            data: List of row dicts.
            type_map: Dict of {field_name: target_type}.
                      Supported types: int, float, str, bool, date.

        Returns:
            New list with cast values. Cast failures keep original value.
        """
        if not data or not type_map:
            return data

        result: list[dict[str, Any]] = []
        for row in data:
            new_row: dict[str, Any] = dict(row)
            for field, target_type in type_map.items():
                if field not in new_row:
                    continue
                original = new_row[field]
                try:
                    if target_type == "int" or target_type == "integer":
                        new_row[field] = (
                            int(float(original)) if original not in (None, "") else None
                        )
                    elif target_type == "float" or target_type == "number":
                        new_row[field] = float(original) if original not in (None, "") else None
                    elif target_type == "str" or target_type == "string":
                        new_row[field] = str(original) if original is not None else None
                    elif target_type == "bool" or target_type == "boolean":
                        if isinstance(original, bool):
                            new_row[field] = original
                        elif isinstance(original, str):
                            new_row[field] = original.strip().lower() in ("true", "1", "yes", "y")
                        else:
                            new_row[field] = bool(original)
                    elif target_type == "date":
                        if isinstance(original, datetime):
                            new_row[field] = original.date().isoformat()
                        elif isinstance(original, str):
                            # Try common date formats
                            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
                                try:
                                    parsed = datetime.strptime(original.strip(), fmt)
                                    new_row[field] = parsed.date().isoformat()
                                    break
                                except ValueError:
                                    continue
                except (ValueError, TypeError):
                    # Keep original value on cast failure (data-quality note).
                    logger.debug(
                        "Cast of field %r to %s failed; keeping original value",
                        field,
                        target_type,
                        exc_info=True,
                    )
            result.append(new_row)
        return result
