import tempfile
import unittest
from pathlib import Path
from typing import Iterable, List

from parentlog.model import (
    COMMUNICATION_METHODS,
    CSV_HEADER,
    CommunicationRecord,
    ParentLogError,
    filter_records,
    load_records,
    parse_csv,
    summarize_records,
)


HEADER_TEXT = ",".join(CSV_HEADER) + "\n"
VALID_ROW = "2026-01-05,张三,电话,沟通近期学习情况,继续观察"


def csv_text(rows: Iterable[str]) -> str:
    return HEADER_TEXT + "\n".join(rows) + "\n"


def make_record(
    student: str = "张三",
    method: str = "电话",
    matter: str = "沟通学习情况",
    follow_up: str = "继续观察",
) -> CommunicationRecord:
    return CommunicationRecord(
        date="2026-01-05",
        student=student,
        method=method,
        matter=matter,
        follow_up=follow_up,
    )


class ParseTests(unittest.TestCase):
    def test_parse_valid_record(self) -> None:
        records = parse_csv(csv_text([VALID_ROW]))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].date, "2026-01-05")
        self.assertEqual(records[0].student, "张三")
        self.assertEqual(records[0].method, "电话")
        self.assertEqual(records[0].matter, "沟通近期学习情况")
        self.assertEqual(records[0].follow_up, "继续观察")

    def test_parse_preserves_csv_order(self) -> None:
        rows = [
            "2026-01-03,学生丙,面谈,事项丙,",
            "2026-01-01,学生甲,电话,事项甲,",
            "2026-01-02,学生乙,微信,事项乙,",
        ]
        records = parse_csv(csv_text(rows))
        self.assertEqual([item.student for item in records], ["学生丙", "学生甲", "学生乙"])

    def test_parse_strips_field_whitespace(self) -> None:
        row = " 2026-01-05 , 张三 , 微信 ,  事项内容  ,  后续安排  "
        record = parse_csv(csv_text([row]))[0]
        self.assertEqual(record.date, "2026-01-05")
        self.assertEqual(record.student, "张三")
        self.assertEqual(record.method, "微信")
        self.assertEqual(record.matter, "事项内容")
        self.assertEqual(record.follow_up, "后续安排")

    def test_parse_supports_quoted_comma(self) -> None:
        record = parse_csv(csv_text(['2026-01-05,张三,面谈,"分析阅读,写作",']))[0]
        self.assertEqual(record.matter, "分析阅读,写作")

    def test_parse_accepts_utf8_bom_text(self) -> None:
        records = parse_csv("\ufeff" + csv_text([VALID_ROW]))
        self.assertEqual(len(records), 1)

    def test_load_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bom.csv"
            path.write_bytes(csv_text([VALID_ROW]).encode("utf-8-sig"))
            records = load_records(path)
        self.assertEqual(records[0].student, "张三")

    def test_load_gbk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gbk.csv"
            path.write_bytes(csv_text([VALID_ROW]).encode("gbk"))
            records = load_records(path)
        self.assertEqual(records[0].matter, "沟通近期学习情况")

    def test_load_unknown_encoding_has_chinese_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_bytes(b"\xff\xff\xff")
            with self.assertRaisesRegex(ParentLogError, "编码"):
                load_records(path)

    def test_load_missing_file_propagates_oserror(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_records("不存在的沟通记录.csv")

    def test_empty_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "没有内容"):
            parse_csv("")

    def test_non_text_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "文本"):
            parse_csv(b"not text")  # type: ignore[arg-type]

    def test_header_only_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "只有表头"):
            parse_csv(HEADER_TEXT)

    def test_wrong_header_order_is_rejected(self) -> None:
        text = "学生,日期,方式,事项,后续\n" + VALID_ROW + "\n"
        with self.assertRaisesRegex(ParentLogError, "第 1 行.*表头"):
            parse_csv(text)

    def test_wrong_header_name_is_rejected(self) -> None:
        text = "日期,姓名,方式,事项,后续\n" + VALID_ROW + "\n"
        with self.assertRaisesRegex(ParentLogError, "顺序固定"):
            parse_csv(text)

    def test_header_with_extra_whitespace_is_rejected(self) -> None:
        text = "日期, 学生,方式,事项,后续\n" + VALID_ROW + "\n"
        with self.assertRaisesRegex(ParentLogError, "表头"):
            parse_csv(text)

    def test_too_few_columns_reports_line(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "第 2 行.*4 列.*5 列"):
            parse_csv(csv_text(["2026-01-05,张三,电话,事项"]))

    def test_too_many_columns_reports_line(self) -> None:
        row = VALID_ROW + ",额外"
        with self.assertRaisesRegex(ParentLogError, "第 2 行.*6 列.*5 列"):
            parse_csv(csv_text([row]))

    def test_blank_rows_are_ignored(self) -> None:
        records = parse_csv("\n" + HEADER_TEXT + "\n" + VALID_ROW + "\n\n")
        self.assertEqual(len(records), 1)

    def test_one_record_is_accepted(self) -> None:
        self.assertEqual(len(parse_csv(csv_text([VALID_ROW]))), 1)

    def test_two_hundred_records_are_accepted(self) -> None:
        records = parse_csv(csv_text([VALID_ROW] * 200))
        self.assertEqual(len(records), 200)

    def test_two_hundred_one_records_are_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "第 202 行.*200"):
            parse_csv(csv_text([VALID_ROW] * 201))

    def test_error_uses_physical_csv_line_number(self) -> None:
        text = HEADER_TEXT + VALID_ROW + "\n\n2026-01-05, ,电话,事项,\n"
        with self.assertRaisesRegex(ParentLogError, "第 4 行.*学生"):
            parse_csv(text)


class FieldValidationTests(unittest.TestCase):
    def assert_row_error(self, row: str, pattern: str) -> None:
        with self.assertRaisesRegex(ParentLogError, pattern):
            parse_csv(csv_text([row]))

    def test_blank_date_is_rejected(self) -> None:
        self.assert_row_error(" ,张三,电话,事项,", "第 2 行.*日期不能为空")

    def test_non_iso_date_is_rejected(self) -> None:
        self.assert_row_error("2026/01/05,张三,电话,事项,", "YYYY-MM-DD")

    def test_non_padded_date_is_rejected(self) -> None:
        self.assert_row_error("2026-1-5,张三,电话,事项,", "YYYY-MM-DD")

    def test_impossible_date_is_rejected(self) -> None:
        self.assert_row_error("2026-02-29,张三,电话,事项,", "真实日期")

    def test_leap_day_is_accepted(self) -> None:
        records = parse_csv(csv_text(["2028-02-29,张三,电话,事项,"]))
        self.assertEqual(records[0].date, "2028-02-29")

    def test_blank_student_is_rejected(self) -> None:
        self.assert_row_error("2026-01-05,   ,电话,事项,", "学生不能为空")

    def test_twenty_character_student_is_accepted(self) -> None:
        student = "生" * 20
        records = parse_csv(csv_text(["2026-01-05,%s,电话,事项," % student]))
        self.assertEqual(records[0].student, student)

    def test_twenty_one_character_student_is_rejected(self) -> None:
        self.assert_row_error("2026-01-05,%s,电话,事项," % ("生" * 21), "学生.*20")

    def test_all_supported_methods_are_accepted(self) -> None:
        self.assertEqual(COMMUNICATION_METHODS, ("电话", "微信", "面谈", "家访", "短信", "其他"))
        for method in COMMUNICATION_METHODS:
            with self.subTest(method=method):
                records = parse_csv(csv_text(["2026-01-05,张三,%s,事项," % method]))
                self.assertEqual(records[0].method, method)

    def test_unsupported_method_is_rejected(self) -> None:
        self.assert_row_error("2026-01-05,张三,邮件,事项,", "方式.*电话")

    def test_blank_matter_is_rejected(self) -> None:
        self.assert_row_error("2026-01-05,张三,电话,   ,", "事项不能为空")

    def test_eighty_character_matter_is_accepted(self) -> None:
        matter = "事" * 80
        records = parse_csv(csv_text(["2026-01-05,张三,电话,%s," % matter]))
        self.assertEqual(records[0].matter, matter)

    def test_eighty_one_character_matter_is_rejected(self) -> None:
        self.assert_row_error("2026-01-05,张三,电话,%s," % ("事" * 81), "事项.*80")

    def test_blank_follow_up_is_stored_as_empty_string(self) -> None:
        records = parse_csv(csv_text(["2026-01-05,张三,电话,事项,   "]))
        self.assertEqual(records[0].follow_up, "")

    def test_eighty_character_follow_up_is_accepted(self) -> None:
        follow_up = "后" * 80
        records = parse_csv(csv_text(["2026-01-05,张三,电话,事项,%s" % follow_up]))
        self.assertEqual(records[0].follow_up, follow_up)

    def test_eighty_one_character_follow_up_is_rejected(self) -> None:
        self.assert_row_error("2026-01-05,张三,电话,事项,%s" % ("后" * 81), "后续.*80")

    def test_direct_model_strips_and_validates(self) -> None:
        record = CommunicationRecord(
            date=" 2026-01-05 ",
            student=" 张三 ",
            method=" 其他 ",
            matter=" 事项 ",
            follow_up=" ",
        )
        self.assertEqual(record.student, "张三")
        self.assertEqual(record.follow_up, "")

    def test_direct_model_rejects_non_text_field(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "日期必须是文本"):
            CommunicationRecord(
                date=20260105,  # type: ignore[arg-type]
                student="张三",
                method="电话",
                matter="事项",
                follow_up="",
            )


class RecordApiTests(unittest.TestCase):
    def test_filter_is_exact_and_preserves_order(self) -> None:
        records = (
            make_record(student="张三", matter="第一条"),
            make_record(student="张三丰", matter="第二条"),
            make_record(student="张三", matter="第三条"),
        )
        selected = filter_records(records, "张三")
        self.assertEqual([item.matter for item in selected], ["第一条", "第三条"])

    def test_filter_strips_outer_whitespace(self) -> None:
        selected = filter_records((make_record(),), " 张三 ")
        self.assertEqual(len(selected), 1)

    def test_filter_partial_name_does_not_match(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "没有找到"):
            filter_records((make_record(student="张三丰"),), "张三")

    def test_filter_no_match_has_chinese_error(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "没有找到学生「李四」"):
            filter_records((make_record(),), "李四")

    def test_filter_rejects_blank_student(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "学生不能为空"):
            filter_records((make_record(),), "  ")

    def test_filter_rejects_overlong_student(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "20"):
            filter_records((make_record(),), "生" * 21)

    def test_summary_counts_records_students_and_methods(self) -> None:
        records = (
            make_record(student="张三", method="微信"),
            make_record(student="李四", method="电话"),
            make_record(student="张三", method="微信"),
        )
        summary = summarize_records(records)
        self.assertEqual(summary.record_count, 3)
        self.assertEqual(summary.student_count, 2)
        self.assertEqual(summary.method_counts, (("电话", 1), ("微信", 2)))

    def test_summary_omits_zero_count_methods(self) -> None:
        summary = summarize_records((make_record(method="家访"),))
        self.assertEqual(summary.method_counts, (("家访", 1),))

    def test_summary_handles_empty_sequence(self) -> None:
        summary = summarize_records(())
        self.assertEqual(summary.record_count, 0)
        self.assertEqual(summary.student_count, 0)
        self.assertEqual(summary.method_counts, ())

    def test_summary_rejects_invalid_record_item(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "CommunicationRecord"):
            summarize_records((object(),))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
