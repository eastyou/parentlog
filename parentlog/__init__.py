"""parentlog：家校沟通记录 CSV 转 A4 可打印 HTML。"""

from .model import (
    COMMUNICATION_METHODS,
    CSV_HEADER,
    CommunicationRecord,
    CommunicationSummary,
    ParentLogError,
    filter_records,
    load_records,
    parse_csv,
    summarize_records,
)

__version__ = "0.1.0"

__all__ = [
    "COMMUNICATION_METHODS",
    "CSV_HEADER",
    "CommunicationRecord",
    "CommunicationSummary",
    "ParentLogError",
    "filter_records",
    "load_records",
    "parse_csv",
    "summarize_records",
]
