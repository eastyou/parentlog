import unittest
from typing import Tuple

from parentlog.model import CommunicationRecord, ParentLogError
from parentlog.render import PAGE_SIZE, paginate, render_html


def make_record(
    index: int = 1,
    student: str = "张三",
    method: str = "电话",
    matter: str = "沟通学习情况",
    follow_up: str = "继续观察",
) -> CommunicationRecord:
    return CommunicationRecord(
        date="2026-01-%02d" % ((index - 1) % 28 + 1),
        student=student,
        method=method,
        matter=matter,
        follow_up=follow_up,
    )


def make_records(count: int) -> Tuple[CommunicationRecord, ...]:
    return tuple(make_record(index=number, matter="事项 %d" % number) for number in range(1, count + 1))


class PaginationTests(unittest.TestCase):
    def test_page_size_is_twelve(self) -> None:
        self.assertEqual(PAGE_SIZE, 12)

    def test_empty_records_have_no_pages(self) -> None:
        self.assertEqual(paginate(()), ())

    def test_pagination_boundaries(self) -> None:
        expected = {1: [1], 12: [12], 13: [12, 1], 24: [12, 12], 25: [12, 12, 1]}
        for count, lengths in expected.items():
            with self.subTest(count=count):
                pages = paginate(make_records(count))
                self.assertEqual([len(page) for page in pages], lengths)

    def test_pagination_preserves_order(self) -> None:
        pages = paginate(make_records(13))
        self.assertEqual(pages[0][0].matter, "事项 1")
        self.assertEqual(pages[0][-1].matter, "事项 12")
        self.assertEqual(pages[1][0].matter, "事项 13")

    def test_invalid_page_sizes_are_rejected(self) -> None:
        for size in (0, -1, True, 1.5):
            with self.subTest(size=size):
                with self.assertRaises(ParentLogError):
                    paginate(make_records(1), page_size=size)  # type: ignore[arg-type]


class RenderTests(unittest.TestCase):
    def test_complete_html_and_chinese_language(self) -> None:
        page = render_html(make_records(1), title="三年级一班家校沟通记录")
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('<html lang="zh-CN">', page)
        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn("<title>三年级一班家校沟通记录</title>", page)

    def test_a4_portrait_print_style(self) -> None:
        page = render_html(make_records(1))
        self.assertIn("@page { size: A4 portrait;", page)
        self.assertIn("width: 210mm", page)
        self.assertIn("height: 297mm", page)
        self.assertIn("@media print", page)

    def test_one_page_contains_twelve_rows(self) -> None:
        page = render_html(make_records(12))
        self.assertEqual(page.count('<section class="sheet">'), 1)
        self.assertEqual(page.count('<td class="number">'), 12)
        self.assertIn("第 1 / 1 页", page)

    def test_thirteen_records_create_two_pages(self) -> None:
        page = render_html(make_records(13))
        self.assertEqual(page.count('<section class="sheet">'), 2)
        self.assertEqual(page.count('<td class="number">'), 13)
        self.assertIn("第 1 / 2 页", page)
        self.assertIn("第 2 / 2 页", page)

    def test_twenty_five_records_create_three_pages(self) -> None:
        page = render_html(make_records(25))
        self.assertEqual(page.count('<section class="sheet">'), 3)
        self.assertEqual(page.count('<td class="number">'), 25)

    def test_every_page_repeats_table_header(self) -> None:
        page = render_html(make_records(13))
        self.assertEqual(page.count("<thead>"), 2)
        self.assertEqual(page.count("<th>日期</th>"), 2)
        self.assertEqual(page.count("<th>后续</th>"), 2)

    def test_row_numbers_continue_across_pages(self) -> None:
        page = render_html(make_records(13))
        self.assertIn('<td class="number">1</td>', page)
        self.assertIn('<td class="number">12</td>', page)
        self.assertIn('<td class="number">13</td>', page)
        self.assertNotIn('<td class="number">0</td>', page)

    def test_summary_shows_counts_and_only_present_methods(self) -> None:
        records = (
            make_record(student="张三", method="微信"),
            make_record(student="李四", method="电话"),
            make_record(student="张三", method="微信"),
        )
        page = render_html(records)
        self.assertIn("共 3 条记录", page)
        self.assertIn("涉及 2 名学生", page)
        self.assertIn("电话 1 次", page)
        self.assertIn("微信 2 次", page)
        self.assertNotIn("短信 0 次", page)
        self.assertNotIn("家访 0 次", page)

    def test_summary_appears_on_each_page(self) -> None:
        page = render_html(make_records(13))
        self.assertEqual(page.count("共 13 条记录"), 2)
        self.assertEqual(page.count("涉及 1 名学生"), 2)

    def test_empty_follow_up_displays_none(self) -> None:
        page = render_html((make_record(follow_up=""),))
        self.assertIn('<td class="follow-up empty">无</td>', page)

    def test_all_dynamic_text_is_escaped(self) -> None:
        record = make_record(
            student='<学生&"\'>',
            matter="阅读 & 写作 <b>重点</b> \"引号\" '单引号'",
            follow_up="<script>alert('x')</script>",
        )
        page = render_html((record,), title='<标题 & "测试">')
        self.assertIn("&lt;标题 &amp; &quot;测试&quot;&gt;", page)
        self.assertIn("&lt;学生&amp;&quot;&#x27;&gt;", page)
        self.assertIn("阅读 &amp; 写作 &lt;b&gt;重点&lt;/b&gt;", page)
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<学生&", page)

    def test_long_text_has_wrapping_styles(self) -> None:
        page = render_html((make_record(matter="事" * 80, follow_up="后" * 80),))
        self.assertIn("table-layout: fixed", page)
        self.assertIn("overflow-wrap: anywhere", page)
        self.assertIn("word-break: break-word", page)
        self.assertIn("事" * 80, page)
        self.assertIn("后" * 80, page)

    def test_columns_are_in_required_order(self) -> None:
        page = render_html(make_records(1))
        positions = [page.index("<th>%s</th>" % name) for name in ("序号", "日期", "学生", "方式", "事项", "后续")]
        self.assertEqual(positions, sorted(positions))

    def test_empty_records_cannot_be_rendered(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "至少需要 1 条"):
            render_html(())

    def test_blank_title_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "标题不能为空"):
            render_html(make_records(1), title="  ")

    def test_overlong_title_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "80"):
            render_html(make_records(1), title="题" * 81)

    def test_non_text_title_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "标题必须是文本"):
            render_html(make_records(1), title=123)  # type: ignore[arg-type]

    def test_invalid_record_item_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParentLogError, "CommunicationRecord"):
            render_html((object(),))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
