import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Tuple

from parentlog.cli import main


CSV_TEXT = """日期,学生,方式,事项,后续
2026-01-05,张三,电话,沟通学习情况,继续观察
2026-01-06,李四,微信,反馈作业情况,
2026-01-07,张三,面谈,沟通课堂表现,约定下周复盘
"""


class CliTests(unittest.TestCase):
    def run_cli(self, arguments: Tuple[str, ...]) -> Tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_generate_with_custom_title_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "output.html"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, stdout, stderr = self.run_cli(
                ("-i", str(source), "--title", "三年级一班家校沟通记录", "-o", str(output))
            )
            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertIn("已生成", stdout)
            self.assertIn("3 条记录", stdout)
            self.assertTrue(output.is_file())
            self.assertIn("三年级一班家校沟通记录", output.read_text(encoding="utf-8"))

    def test_default_output_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            source.write_text(CSV_TEXT, encoding="utf-8")
            previous = os.getcwd()
            try:
                os.chdir(directory)
                code, _, _ = self.run_cli(("-i", str(source)))
                self.assertTrue((Path(directory) / "家校沟通记录.html").is_file())
            finally:
                os.chdir(previous)
            self.assertEqual(code, 0)

    def test_student_filter_generates_exact_subset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "output.html"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, stdout, _ = self.run_cli(
                ("-i", str(source), "--student", "张三", "-o", str(output))
            )
            page = output.read_text(encoding="utf-8")
            self.assertEqual(code, 0)
            self.assertIn("2 条记录", stdout)
            self.assertIn("共 2 条记录", page)
            self.assertIn("涉及 1 名学生", page)
            self.assertIn("沟通学习情况", page)
            self.assertIn("沟通课堂表现", page)
            self.assertNotIn("反馈作业情况", page)

    def test_student_filter_without_match_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "output.html"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, _, stderr = self.run_cli(
                ("-i", str(source), "--student", "王五", "-o", str(output))
            )
            self.assertEqual(code, 2)
            self.assertIn("没有找到学生", stderr)
            self.assertFalse(output.exists())

    def test_blank_student_filter_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, _, stderr = self.run_cli(("-i", str(source), "--student", " "))
            self.assertEqual(code, 2)
            self.assertIn("学生不能为空", stderr)

    def test_invalid_csv_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            source.write_text(CSV_TEXT.replace("2026-01-05", "2026-02-30"), encoding="utf-8")
            code, _, stderr = self.run_cli(("-i", str(source)))
            self.assertEqual(code, 2)
            self.assertIn("第 2 行", stderr)
            self.assertIn("真实日期", stderr)

    def test_missing_input_returns_one(self) -> None:
        code, _, stderr = self.run_cli(("-i", "不存在的输入.csv"))
        self.assertEqual(code, 1)
        self.assertIn("读取文件失败", stderr)

    def test_unknown_encoding_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            source.write_bytes(b"\xff\xff\xff")
            code, _, stderr = self.run_cli(("-i", str(source)))
            self.assertEqual(code, 2)
            self.assertIn("编码", stderr)

    def test_gbk_input_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "output.html"
            source.write_bytes(CSV_TEXT.encode("gbk"))
            code, _, stderr = self.run_cli(("-i", str(source), "-o", str(output)))
            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertIn("沟通学习情况", output.read_text(encoding="utf-8"))

    def test_output_oserror_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, _, stderr = self.run_cli(("-i", str(source), "-o", directory))
            self.assertEqual(code, 1)
            self.assertIn("写入文件失败", stderr)

    def test_blank_title_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, _, stderr = self.run_cli(("-i", str(source), "--title", " "))
            self.assertEqual(code, 2)
            self.assertIn("标题不能为空", stderr)

    def test_success_message_mentions_a4_portrait_printing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "output.html"
            source.write_text(CSV_TEXT, encoding="utf-8")
            code, stdout, _ = self.run_cli(("-i", str(source), "-o", str(output)))
            self.assertEqual(code, 0)
            self.assertIn("A4 纵向", stdout)
            self.assertIn("Ctrl/Cmd + P", stdout)

    def test_module_entry_point(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "output.html"
            source.write_text(CSV_TEXT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "parentlog", "-i", str(source), "-o", str(output)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(output.is_file())

    def test_help_exits_zero(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
            main(("--help",))
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("--student", stdout.getvalue())

    def test_missing_required_input_exits_two(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            main(())
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
