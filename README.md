# parentlog

[![CI](https://github.com/eastyou/parentlog/actions/workflows/ci.yml/badge.svg)](https://github.com/eastyou/parentlog/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](pyproject.toml)

给老师用的家校沟通记录整理工具：把「日期,学生,方式,事项,后续」CSV 一键转成清晰、A4 纵向可打印的沟通记录表。**零依赖，不联网，打印即用。**

支持按学生精确筛选，自动统计记录数、涉及学生数和已出现沟通方式的次数；原始顺序保持不变，空后续统一显示「无」。

## 特性

- **固定五列表格**：序号、日期、学生、方式、事项、后续，保留 CSV 原顺序
- **学生精确筛选**：`--student 张三` 只保留该学生的记录，无匹配时给出中文错误
- **自动汇总**：页面顶部展示记录数、学生数及各沟通方式次数，不显示零次方式
- **A4 纵向分页**：每页最多 12 条，自动添加页码，每页重复标题、汇总和表头
- **安全排版**：所有文本均进行 HTML 转义，长事项与后续自动换行，不依赖外部 CSS 或字体
- **逐行校验**：非法日期、方式、列数及字段长度均指出具体 CSV 行号
- **编码兼容**：自动识别 UTF-8、带 BOM 的 UTF-8 与 GBK
- **88 个单元测试**：覆盖编码、字段边界、筛选汇总、分页、HTML 转义与命令行

## 安装

```bash
pip install parentlog
```

也可以直接下载源码，在项目目录里运行，无需安装第三方依赖：

```bash
python -m parentlog --help
```

## 用法

项目附带 `examples/沟通记录.csv`，可直接生成示例：

```bash
python -m parentlog -i examples/沟通记录.csv --title 三年级一班家校沟通记录 -o examples/家校沟通记录.html
```

只看张三的沟通记录：

```bash
python -m parentlog -i examples/沟通记录.csv --student 张三 -o 张三沟通记录.html
```

安装后也可以使用 `parentlog` 命令，参数完全相同。

### 参数

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `-i, --input` | 沟通记录 CSV | 必填 |
| `-o, --output` | 输出 HTML 路径 | `家校沟通记录.html` |
| `--title` | 页面标题，去空白后最多 80 字 | `家校沟通记录` |
| `--student` | 学生姓名精确筛选，姓名两端空白会被去除 | 不筛选 |
| `--version` | 显示版本 | — |
| `-h, --help` | 显示帮助 | — |

退出码：`0` 表示成功，`1` 表示文件读取或写入失败，`2` 表示 CSV 数据、筛选条件或参数不合法。命令行参数解析错误也返回 `2`。

### CSV 格式

第一行必须是以下表头，名称与顺序均固定：

```csv
日期,学生,方式,事项,后续
2026-09-01,张三,电话,沟通开学适应与作息安排,一周后再次了解状态
2026-09-02,李四,微信,反馈语文作业完成质量,
```

| 字段 | 规则 |
| --- | --- |
| 日期 | 真实 ISO 日期，严格使用 `YYYY-MM-DD`，会检查闰年和不存在的日期 |
| 学生 | 去除两端空白后为 1~20 个字符 |
| 方式 | 仅支持 `电话`、`微信`、`面谈`、`家访`、`短信`、`其他` |
| 事项 | 去除两端空白后为 1~80 个字符 |
| 后续 | 允许为空；非空时去除两端空白，最多 80 个字符，HTML 中空值显示「无」 |

- 数据记录为 1~200 条，空白行不计入记录数。
- 每条数据必须恰好 5 列；含逗号字段可按 CSV 标准使用双引号。
- 所有字段错误均使用中文提示，数据校验错误包含实际 CSV 行号。

## 打印

用浏览器打开生成的 HTML，按 `Ctrl/Cmd + P`：

- 纸张：A4 纵向，缩放 100%
- 边距：无（页面已预留内边距）
- 勾选「背景图形」，汇总标签和表头底色才会打印
- 每页最多 12 条记录；浏览器预览中可核对自动页码与重复表头

## 独立 API

`filter_records` 与 `summarize_records` 可脱离 CLI 单独使用：

```python
from parentlog import filter_records, load_records, summarize_records

records = load_records("examples/沟通记录.csv")
selected = filter_records(records, "张三")
summary = summarize_records(selected)
print(summary.record_count, summary.student_count, summary.method_counts)
```

## 项目结构

```text
parentlog/
├── parentlog/
│   ├── __init__.py   # 公共模型与 API
│   ├── __main__.py   # python -m parentlog 入口
│   ├── cli.py        # 参数、退出码与文件写入
│   ├── model.py      # dataclass、CSV 校验、筛选与汇总
│   └── render.py     # 12 条分页与 A4 纵向 HTML/CSS
├── tests/            # 88 个 unittest 单元测试
├── examples/         # 示例 CSV 与已生成 HTML
└── .github/workflows/ci.yml
```

CI 覆盖 Ubuntu、macOS、Windows 的 Python 3.10/3.13，以及 Ubuntu 22.04 的 Python 3.9；单元测试后还会运行示例与学生筛选并断言输出内容。

## 开发

```bash
python -m unittest discover -s tests
```

## 许可证

[MIT](LICENSE) © 2026 eastyou
