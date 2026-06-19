"""
Export Service - Exports analyzed logs and incidents to JSON, CSV, and Excel formats.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExportService:
    """Service for exporting data to various file formats."""

    def __init__(self):
        self.export_dir = Path(settings.export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, prefix: str, extension: str) -> Path:
        """Generate a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.export_dir / f"{prefix}_{timestamp}.{extension}"

    def export_to_json(self, data: list[dict[str, Any]], prefix: str = "export") -> Path:
        """Export data to a JSON file."""
        filepath = self._generate_filename(prefix, "json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Exported {len(data)} records to {filepath}")
        return filepath

    def export_to_csv(self, data: list[dict[str, Any]], prefix: str = "export") -> Path:
        """Export data to a CSV file."""
        filepath = self._generate_filename(prefix, "csv")
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info(f"Exported {len(data)} records to {filepath}")
        return filepath

    def export_to_excel(self, data: list[dict[str, Any]], prefix: str = "export") -> Path:
        """Export data to an Excel file with formatted sheets."""
        filepath = self._generate_filename(prefix, "xlsx")
        df = pd.DataFrame(data)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Data", index=False)

            # Auto-adjust column widths
            worksheet = writer.sheets["Data"]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except (TypeError, AttributeError):
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        logger.info(f"Exported {len(data)} records to {filepath}")
        return filepath

    def export_incidents_report(
        self,
        incidents: list[dict[str, Any]],
        format: str = "xlsx",
    ) -> Path:
        """
        Export a formatted incidents report.
        Separates HIGH, MEDIUM, LOW into different sheets for Excel.
        """
        if format == "json":
            return self.export_to_json(incidents, prefix="incidents_report")
        elif format == "csv":
            return self.export_to_csv(incidents, prefix="incidents_report")
        elif format == "xlsx":
            filepath = self._generate_filename("incidents_report", "xlsx")
            df = pd.DataFrame(incidents)

            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                # All incidents
                df.to_excel(writer, sheet_name="All Incidents", index=False)

                # Priority-specific sheets
                for priority in ["HIGH", "MEDIUM", "LOW"]:
                    priority_df = df[df.get("priority", pd.Series()) == priority]
                    if not priority_df.empty:
                        priority_df.to_excel(
                            writer, sheet_name=f"{priority} Priority", index=False
                        )

            logger.info(f"Exported incidents report to {filepath}")
            return filepath
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Singleton instance
export_service = ExportService()
