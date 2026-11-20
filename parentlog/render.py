"""把家校沟通记录渲染为自包含的 A4 纵向分页 HTML。"""

from __future__ import annotations

import html
from typing import List, Sequence, Tuple

from .model import CommunicationRecord, ParentLogError, summarize_records

PAGE_SIZE = 12
MAX_TITLE_LENGTH = 80


def paginate(
    records: Sequence[CommunicationRecord], page_size: int = PAGE_SIZE
) -> Tuple[Tuple[CommunicationRecord, ...], ...]:
    """按原顺序分页；空记录返回空元组，最后一页可不足 page_size 条。"""
    if isinstance(page_size, bool) or not isinstance(page_size, int):
        raise ParentLogError("每页条数必须是整数")
    if page_size < 1:
        raise ParentLogError("每页条数必须大于 0")
    try:
        items = tuple(records)
    except TypeError as exc:
        raise ParentLogError("记录必须是序列") from exc
    for record in items:
        if not isinstance(record, CommunicationRecord):
            raise ParentLogError("记录项必须是 CommunicationRecord 对象")
    return tuple(items[start : start + page_size] for start in range(0, len(items), page_size))


def _table_markup(records: Tuple[CommunicationRecord, ...], offset: int) -> str:
    header = (
        "<thead><tr><th>序号</th><th>日期</th><th>学生</th>"
        "<th>方式</th><th>事项</th><th>后续</th></tr></thead>"
    )
    rows: List[str] = []
    for index, record in enumerate(records, start=offset + 1):
        if record.follow_up:
            follow_up = '<td class="follow-up">%s</td>' % html.escape(record.follow_up)
        else:
            follow_up = '<td class="follow-up empty">无</td>'
        rows.append(
            "<tr>"
            '<td class="number">%d</td>'
            '<td class="date">%s</td>'
            '<td class="student">%s</td>'
            '<td class="method">%s</td>'
            '<td class="matter">%s</td>'
            "%s</tr>"
            % (
                index,
                html.escape(record.date),
                html.escape(record.student),
                html.escape(record.method),
                html.escape(record.matter),
                follow_up,
            )
        )
    return (
        '<table class="records">'
        "<colgroup>"
        '<col class="col-number"><col class="col-date"><col class="col-student">'
        '<col class="col-method"><col class="col-matter"><col class="col-follow-up">'
        "</colgroup>%s<tbody>%s</tbody></table>" % (header, "".join(rows))
    )


def _page_markup(
    records: Tuple[CommunicationRecord, ...],
    title: str,
    summary_markup: str,
    page_number: int,
    page_count: int,
) -> str:
    offset = (page_number - 1) * PAGE_SIZE
    return (
        '<section class="sheet">'
        '<header class="head"><h1>%s</h1>%s</header>'
        "%s"
        '<footer class="foot"><span>家校沟通记录 · A4 纵向</span>'
        "<span>第 %d / %d 页</span></footer></section>"
        % (
            html.escape(title),
            summary_markup,
            _table_markup(records, offset),
            page_number,
            page_count,
        )
    )


def render_html(
    records: Sequence[CommunicationRecord], title: str = "家校沟通记录"
) -> str:
    """生成完整打印页面，每页最多 12 条并重复标题、汇总与表头。"""
    if not isinstance(title, str):
        raise ParentLogError("标题必须是文本")
    title = title.strip()
    if not title:
        raise ParentLogError("标题不能为空")
    if len(title) > MAX_TITLE_LENGTH:
        raise ParentLogError("标题最多 %d 个字符" % MAX_TITLE_LENGTH)

    try:
        checked = tuple(records)
    except TypeError as exc:
        raise ParentLogError("记录必须是序列") from exc
    if not checked:
        raise ParentLogError("至少需要 1 条记录才能生成 HTML")
    summary = summarize_records(checked)
    pages = paginate(checked)
    methods = "".join(
        "<span>%s %d 次</span>" % (html.escape(method), count)
        for method, count in summary.method_counts
    )
    summary_markup = (
        '<div class="summary"><span>共 %d 条记录</span>'
        "<span>涉及 %d 名学生</span></div>"
        '<div class="methods">%s</div>'
        % (summary.record_count, summary.student_count, methods)
    )
    page_count = len(pages)
    body = "\n".join(
        _page_markup(page, title, summary_markup, number, page_count)
        for number, page in enumerate(pages, start=1)
    )
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n%s\n</body>\n</html>\n"
        % (html.escape(title), _STYLE, body)
    )


_STYLE = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 8mm 0;
    background: #e2e8f0;
    color: #172033;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  }
  .sheet {
    width: 210mm;
    height: 297mm;
    margin: 0 auto 8mm;
    padding: 8mm 9mm 7mm;
    background: #fff;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.14);
    display: flex;
    flex-direction: column;
    page-break-after: always;
    break-after: page;
  }
  .sheet:last-child { page-break-after: auto; break-after: auto; }
  .head { text-align: center; }
  .head h1 {
    margin: 0 0 2mm;
    font-size: 17pt;
    line-height: 1.25;
    font-weight: 600;
    letter-spacing: 1.5pt;
    overflow-wrap: anywhere;
  }
  .summary {
    display: flex;
    justify-content: center;
    gap: 5mm;
    margin-bottom: 1.5mm;
    color: #334155;
    font-size: 10pt;
    line-height: 1.3;
  }
  .methods {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 1mm 2mm;
    margin-bottom: 2.5mm;
    font-size: 8.5pt;
    line-height: 1.25;
  }
  .methods span { padding: 0.7mm 2mm; background: #f1f5f9; border-radius: 2mm; }
  table.records { width: 100%; border-collapse: collapse; table-layout: fixed; }
  .col-number { width: 5%; }
  .col-date { width: 12%; }
  .col-student { width: 12%; }
  .col-method { width: 8%; }
  .col-matter { width: 36%; }
  .col-follow-up { width: 27%; }
  table.records th, table.records td {
    border: 0.25mm solid #94a3b8;
    padding: 1mm 1.2mm;
    vertical-align: middle;
    text-align: left;
    font-size: 8pt;
    line-height: 1.25;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
  table.records th {
    height: 7mm;
    background: #eaf0f7;
    text-align: center;
    font-size: 8.5pt;
    font-weight: 600;
  }
  table.records td.number, table.records td.method { text-align: center; }
  table.records td.date { text-align: center; white-space: nowrap; }
  table.records td.empty { color: #64748b; text-align: center; }
  .foot {
    margin-top: auto;
    padding-top: 2mm;
    display: flex;
    justify-content: space-between;
    color: #64748b;
    font-size: 8pt;
    line-height: 1.2;
  }
  @page { size: A4 portrait; margin: 0; }
  @media print {
    body { padding: 0; background: #fff; }
    .sheet { margin: 0; box-shadow: none; }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""
