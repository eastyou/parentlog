"""家校沟通记录的数据模型、CSV 校验、筛选与汇总。"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Union

CSV_HEADER: Tuple[str, ...] = ("日期", "学生", "方式", "事项", "后续")
COMMUNICATION_METHODS: Tuple[str, ...] = ("电话", "微信", "面谈", "家访", "短信", "其他")
MIN_RECORDS = 1
MAX_RECORDS = 200
MAX_STUDENT_LENGTH = 20
MAX_MATTER_LENGTH = 80
MAX_FOLLOW_UP_LENGTH = 80


class ParentLogError(ValueError):
    """沟通记录内容或查询参数不合法。"""


@dataclass(frozen=True)
class CommunicationRecord:
    """一条家校沟通记录，日期使用真实 ISO YYYY-MM-DD 文本。"""

    date: str
    student: str
    method: str
    matter: str
    follow_up: str

    def __post_init__(self) -> None:
        fields = (
            ("date", "日期"),
            ("student", "学生"),
            ("method", "方式"),
            ("matter", "事项"),
            ("follow_up", "后续"),
        )
        for attribute, label in fields:
            value = getattr(self, attribute)
            if not isinstance(value, str):
                raise ParentLogError("%s必须是文本" % label)
            object.__setattr__(self, attribute, value.strip())

        _validate_date(self.date)
        _validate_student_name(self.student)
        if self.method not in COMMUNICATION_METHODS:
            raise ParentLogError("方式必须是：%s" % "、".join(COMMUNICATION_METHODS))
        if not self.matter:
            raise ParentLogError("事项不能为空")
        if len(self.matter) > MAX_MATTER_LENGTH:
            raise ParentLogError("事项最多 %d 个字符" % MAX_MATTER_LENGTH)
        if len(self.follow_up) > MAX_FOLLOW_UP_LENGTH:
            raise ParentLogError("后续最多 %d 个字符" % MAX_FOLLOW_UP_LENGTH)


@dataclass(frozen=True)
class CommunicationSummary:
    """记录总数、学生总数及各已出现沟通方式的次数。"""

    record_count: int
    student_count: int
    method_counts: Tuple[Tuple[str, int], ...]


def _validate_date(value: str) -> None:
    if not value:
        raise ParentLogError("日期不能为空")
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ParentLogError("日期必须使用 ISO YYYY-MM-DD 格式")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ParentLogError("日期必须是真实日期：%s" % value) from exc
    if parsed.isoformat() != value:
        raise ParentLogError("日期必须使用 ISO YYYY-MM-DD 格式")


def _validate_student_name(student: str) -> None:
    if not student:
        raise ParentLogError("学生不能为空")
    if len(student) > MAX_STUDENT_LENGTH:
        raise ParentLogError("学生最多 %d 个字符" % MAX_STUDENT_LENGTH)


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ParentLogError("无法识别文件编码，请另存为 UTF-8 或 GBK 后重试")


def parse_csv(text: str) -> Tuple[CommunicationRecord, ...]:
    """解析并校验固定表头的 CSV，返回保持原顺序的只读记录元组。"""
    if not isinstance(text, str):
        raise ParentLogError("CSV 内容必须是文本")

    reader = csv.reader(io.StringIO(text.lstrip("\ufeff"), newline=""))
    records: List[CommunicationRecord] = []
    header_seen = False
    try:
        for row in reader:
            line_number = reader.line_num
            if not row or not any(cell.strip() for cell in row):
                continue
            if not header_seen:
                if tuple(row) != CSV_HEADER:
                    raise ParentLogError(
                        "第 %d 行：表头必须为「%s」（顺序固定）"
                        % (line_number, ",".join(CSV_HEADER))
                    )
                header_seen = True
                continue
            if len(row) != len(CSV_HEADER):
                raise ParentLogError(
                    "第 %d 行：当前有 %d 列，应为 %d 列"
                    % (line_number, len(row), len(CSV_HEADER))
                )
            if len(records) >= MAX_RECORDS:
                raise ParentLogError(
                    "第 %d 行：记录总数不能超过 %d 条" % (line_number, MAX_RECORDS)
                )
            try:
                record = CommunicationRecord(
                    date=row[0],
                    student=row[1],
                    method=row[2],
                    matter=row[3],
                    follow_up=row[4],
                )
            except ParentLogError as exc:
                raise ParentLogError("第 %d 行：%s" % (line_number, exc)) from exc
            records.append(record)
    except csv.Error as exc:
        line_number = reader.line_num
        raise ParentLogError("第 %d 行：CSV 格式错误：%s" % (line_number, exc)) from exc

    if not header_seen:
        raise ParentLogError("CSV 中没有内容")
    if len(records) < MIN_RECORDS:
        raise ParentLogError("CSV 中只有表头，至少需要 1 条记录")
    return tuple(records)


def load_records(path: Union[str, Path]) -> Tuple[CommunicationRecord, ...]:
    """从 UTF-8、带 BOM 的 UTF-8 或 GBK 文件读取沟通记录。"""
    target = Path(path)
    return parse_csv(_decode(target.read_bytes()))


def _checked_records(
    records: Sequence[CommunicationRecord],
) -> Tuple[CommunicationRecord, ...]:
    try:
        checked = tuple(records)
    except TypeError as exc:
        raise ParentLogError("记录必须是序列") from exc
    for record in checked:
        if not isinstance(record, CommunicationRecord):
            raise ParentLogError("记录项必须是 CommunicationRecord 对象")
    return checked


def filter_records(
    records: Sequence[CommunicationRecord], student: str
) -> Tuple[CommunicationRecord, ...]:
    """按去空白后的学生姓名精确筛选，保持 CSV 原顺序。"""
    if not isinstance(student, str):
        raise ParentLogError("学生必须是文本")
    student = student.strip()
    _validate_student_name(student)
    selected = tuple(record for record in _checked_records(records) if record.student == student)
    if not selected:
        raise ParentLogError("没有找到学生「%s」的沟通记录" % student)
    return selected


def summarize_records(records: Sequence[CommunicationRecord]) -> CommunicationSummary:
    """在线性时间内汇总记录数、学生数及非零沟通方式次数。"""
    checked = _checked_records(records)
    students = {record.student for record in checked}
    counts: Dict[str, int] = {method: 0 for method in COMMUNICATION_METHODS}
    for record in checked:
        counts[record.method] += 1
    method_counts = tuple(
        (method, counts[method]) for method in COMMUNICATION_METHODS if counts[method] > 0
    )
    return CommunicationSummary(
        record_count=len(checked),
        student_count=len(students),
        method_counts=method_counts,
    )
