import re
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports" / "investigations"

FILENAME_PATTERN = re.compile(
    r"^(?P<metric_date>\d{4}-\d{2}-\d{2})_(?P<metric_name>.+)\.md$"
)


def report_filename(metric_date: str, metric_name: str) -> str:
    safe_name = metric_name.strip().lower().replace(" ", "_")
    return f"{metric_date}_{safe_name}.md"


def report_path_for(anomaly: dict) -> Path:
    return REPORTS_DIR / report_filename(anomaly["metric_date"], anomaly["metric_name"])


def save_report(anomaly: dict, content: str) -> Path:
    """Write investigation markdown to reports/investigations/."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = report_path_for(anomaly)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def list_reports() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("*.md"), reverse=True)


def parse_report_filename(path: Path) -> dict | None:
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        return None
    return {
        "metric_date": date.fromisoformat(match.group("metric_date")),
        "metric_name": match.group("metric_name"),
        "path": path,
    }


def load_report(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def filter_reports(
    start: date | None = None,
    end: date | None = None,
) -> list[Path]:
    reports = []
    for path in list_reports():
        meta = parse_report_filename(path)
        if meta is None:
            continue
        report_date = meta["metric_date"]
        if start and report_date < start:
            continue
        if end and report_date > end:
            continue
        reports.append(path)
    return reports
