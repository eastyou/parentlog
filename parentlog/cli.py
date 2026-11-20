"""命令行入口：筛选家校沟通记录并生成 A4 可打印 HTML。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .model import ParentLogError, filter_records, load_records, summarize_records
from .render import render_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parentlog",
        description="家校沟通记录 CSV 一键生成 A4 纵向可打印记录表",
    )
    parser.add_argument("--version", action="version", version="parentlog 0.1.0")
    parser.add_argument(
        "-i", "--input", required=True, help="沟通记录 CSV（日期,学生,方式,事项,后续）"
    )
    parser.add_argument("-o", "--output", default="家校沟通记录.html", help="输出 HTML 路径")
    parser.add_argument("--title", default="家校沟通记录", help="页面标题，最多 80 个字符")
    parser.add_argument("--student", default=None, help="按学生姓名精确筛选")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """执行命令；成功返回 0，文件系统错误返回 1，数据或参数错误返回 2。"""
    args = build_parser().parse_args(argv)
    try:
        records = load_records(args.input)
    except ParentLogError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("错误: 读取文件失败: %s" % exc, file=sys.stderr)
        return 1

    try:
        if args.student is not None:
            records = filter_records(records, args.student)
        page = render_html(records, title=args.title)
    except ParentLogError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2

    try:
        Path(args.output).write_text(page, encoding="utf-8")
    except OSError as exc:
        print("错误: 写入文件失败: %s" % exc, file=sys.stderr)
        return 1

    summary = summarize_records(records)
    print(
        "已生成 %s：%d 条记录，涉及 %d 名学生"
        % (args.output, summary.record_count, summary.student_count)
    )
    print("用浏览器打开后按 Ctrl/Cmd + P，纸张选 A4 纵向即可打印")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
