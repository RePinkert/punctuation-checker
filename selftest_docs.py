#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README / SKILL.md 自测脚本：校验文档中的命令、示例、链接与指标是否与代码实际一致。"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not ok else ""))


def run(args, stdin=None):
    # Force child stdout/stderr to UTF-8 so Windows console codepage (cp936) doesn't
    # corrupt captured text; the checker itself is UTF-8 source.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True, text=True,
                          encoding="utf-8", env=env)


print("=" * 70)
print("1. 文档文件存在性")
print("=" * 70)
for f in ["README.md", "README_en.md", "SKILL.md", "CLAUSE_COVERAGE.md",
          "WORKFLOW.md", "program.md", "LICENSE", "punctuation_checker.py"]:
    check(f"{f} 存在", os.path.isfile(f))
check("旧文件 punctuation_checker_readme.md 已删除", not os.path.exists("punctuation_checker_readme.md"))
# Case-sensitive existence checks (Windows FS is case-insensitive; use the dir listing)
_dirents = set(os.listdir("."))
check("旧文件 readme.md 不再残留（小写）", "readme.md" not in _dirents, str(sorted(_dirents)))
check("旧文件 readme_en.md 不再残留（小写）", "readme_en.md" not in _dirents, str(sorted(_dirents)))
check("README.md / README_en.md 存在（正确大小写）", {"README.md", "README_en.md"} <= _dirents)

print("\n" + "=" * 70)
print("2. SKILL.md frontmatter 合规（Agent Skills 规范）")
print("=" * 70)
import yaml
skill = open("SKILL.md", encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check("SKILL.md 以 YAML frontmatter 开头", bool(m))
fm = yaml.safe_load(m.group(1)) if m else {}
check("frontmatter 是合法 YAML mapping", isinstance(fm, dict))
name = fm.get("name", "")
desc = fm.get("description", "")
check("name 存在且非空", bool(name.strip()), repr(name))
check("name 符合 [a-z0-9-] 且无首尾/连续连字符",
      bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)), repr(name))
check("name 长度 <= 64", len(name) <= 64, f"len={len(name)}")
check("description 存在且非空", bool(desc.strip()))
check("description 长度 <= 1024", len(desc) <= 1024, f"len={len(desc)}")
check("frontmatter 字段均在规范允许集合内",
      set(fm) <= {"name", "description", "license", "compatibility",
                  "metadata", "allowed-tools", "disable-model-invocation"},
      str(set(fm)))
check("description 含触发场景关键词（校对/检查）",
      any(k in desc for k in ["校对", "检查", "check", "Check"]))
check("SKILL.md 正文含命令入口 punctuation_checker.py",
      "punctuation_checker.py" in skill)

print("\n" + "=" * 70)
print("3. README.md 内部链接可解析")
print("=" * 70)
for doc in ["README.md", "README_en.md", "SKILL.md"]:
    text = open(doc, encoding="utf-8").read()
    links = re.findall(r"\]\((?!https?://)([^)#]+?)(?:#[^)]*)?\)", text)
    bad = [l for l in links if not os.path.exists(l)]
    check(f"{doc} 全部相对链接指向存在的文件 ({len(links)} 个)", not bad, str(bad))

print("\n" + "=" * 70)
print("4. 徽章 / 跳转链接")
print("=" * 70)
for doc, other in [("README.md", "README_en.md"), ("README_en.md", "README.md")]:
    text = open(doc, encoding="utf-8").read()
    check(f"{doc} 含 <p align=\"center\"> 徽章块", '<p align="center">' in text)
    check(f"{doc} 徽章块内含跳转链接 href=\"{other}\"", f'href="{other}"' in text)
    check(f"{doc} 使用 img.shields.io 徽章", "img.shields.io" in text)
    check(f"{doc} 引用 skills.sh 徽章", "skills.sh" in text)
    for link in re.findall(r'href="([^"]+)"', text):
        if link.endswith(".md") and os.path.exists(link):
            check(f"{doc} -> {link} 跳转目标存在", True)

print("\n" + "=" * 70)
print("5. README.md 文档命令实测（逐条执行）")
print("=" * 70)
os.makedirs("selftest_tmp", exist_ok=True)
sample = "selftest_tmp/selftest.txt"
with open(sample, "w", encoding="utf-8") as fh:
    fh.write("这是中文句子,用了英文逗号。\n")

r = run(["punctuation_checker.py", sample])
check("基本用法可运行（退出码 0）", r.returncode == 0, r.stderr[-300:])
check("基本用法输出报告标题", "标点符号检查报告" in r.stdout)

r = run(["punctuation_checker.py", sample, "--strict"])
check("--strict 可运行", r.returncode == 0 and "标点符号检查报告" in r.stdout, r.stderr[-300:])

r = run(["punctuation_checker.py", sample, "--json"])
check("--json 可运行", r.returncode == 0, r.stderr[-300:])
try:
    j = json.loads(r.stdout)
    check("--json 输出可被 json.loads 解析", True)
    check("--json 含 file/total_errors/errors 键",
          {"file", "total_errors", "errors"} <= set(j))
    e0 = j["errors"][0]
    check("--json 单条含文档所述全部字段",
          {"line", "column", "level", "type", "message", "context", "suggestion"} <= set(e0),
          str(set(e0)))
    check("--json level 取值合法（错误/警告/建议）",
          e0["level"] in {"错误", "警告", "建议"}, e0["level"])
    check("--json 示例 line=1 column=6 与实际输出一致",
          e0["line"] == 1 and e0["column"] == 6, f"got {e0['line']}/{e0['column']}")
    real_json_shape = json.dumps(j, ensure_ascii=False, indent=2)
except Exception as exc:  # noqa: BLE001
    check("--json 可解析", False, str(exc))
    real_json_shape = ""

r = run(["punctuation_checker.py", sample, "-o", "selftest_tmp/out.txt"])
check("-o 可运行并提示保存", r.returncode == 0 and "报告已保存" in r.stdout, r.stdout[-200:])
check("-o 生成的文件存在", os.path.isfile("selftest_tmp/out.txt"))

r = run(["punctuation_checker.py", sample, "--no-suggestion"])
check("--no-suggestion 可运行", r.returncode == 0, r.stderr[-300:])
check("--no-suggestion 隐藏了建议行", "建议:" not in r.stdout)

r = run(["punctuation_checker.py", sample, "-e", "utf-8"])
check("-e 可运行", r.returncode == 0, r.stderr[-300:])

r = run(["punctuation_checker.py", "--help"])
check("--help 可运行", r.returncode == 0)
for flag in ["--strict", "--output", "--encoding", "--no-suggestion", "--json"]:
    check(f"--help 中列出 {flag}", flag in r.stdout)

r = run(["punctuation_checker.py", "selftest_tmp/does_not_exist.txt"])
check("文件不存在时给出友好错误而非 traceback",
      r.returncode == 0 and "Traceback" not in r.stderr and "不存在" in r.stdout,
      r.stderr[-200:])

print("\n" + "=" * 70)
print("6. README.md 库用法示例逐字实测")
print("=" * 70)
lib = run(["-c", (
    "from punctuation_checker import PunctuationChecker, format_report\n"
    "checker = PunctuationChecker(strict_mode=True)\n"
    "text = '这是一个测试,看看标点检测是否正常。'\n"
    "errors = checker.check(text)\n"
    "for error in errors:\n"
    "    print(f'第{error.line}行 第{error.column}列 [{error.level.value}] {error.error_type}: {error.message}')\n"
    "print(format_report(errors, show_suggestion=True)[:40])\n"
)])
check("README 库示例可直接运行", lib.returncode == 0, lib.stderr[-400:])
check("库示例输出了预期文案", "中英文标点混用" in lib.stdout)
fields = run(["-c", (
    "from punctuation_checker import PunctuationChecker\n"
    "errs = PunctuationChecker().check('这是中文句子,用了英文逗号。')\n"
    "e = errs[0]\n"
    "need = ['line','column','level','error_type','message','context','suggestion']\n"
    "print('MISSING:' + ','.join(f for f in need if not hasattr(e, f)))\n"
)])
missing = fields.stdout.strip()
check("PunctuationError 文档所述 7 个字段均存在", fields.returncode == 0 and missing == "MISSING:",
      f"{missing} | {fields.stderr[-200:]}")

print("\n" + "=" * 70)
print("7. README 文本报告示例与真实输出一致")
print("=" * 70)
txt = run(["punctuation_checker.py", sample]).stdout
for line in ["统计: 错误 1 个", "类型: 中英文标点混用", "问题: 中文标点后使用了英文逗号",
             "建议: 应使用中文标点「，」", "第1行, 第6列 [错误]"]:
    check(f"文本报告实测含：{line}", line in txt)
rm = open("README.md", encoding="utf-8").read()
check("文档示例未残留旧的错误列号 第9列", "第9列" not in rm)
check("文档示例列号与实测一致（第6列）", "第6列" in rm)
check("README 文本报告示例与真实输出逐行一致",
      all(l in txt for l in ["统计: 错误 1 个, 警告 0 个, 建议 0 个",
                             "第1行, 第6列 [错误]",
                             "  类型: 中英文标点混用",
                             "  问题: 中文标点后使用了英文逗号",
                             "  上下文: 这是中文句子,用了英文逗号。",
                             "  建议: 应使用中文标点「，」"]))

# Strict: the documented JSON example must equal real --json output field-for-field
if real_json_shape:
    doc_json = re.search(r"```json\n(.*?)\n```", rm, re.S)
    if doc_json:
        try:
            documented = json.loads(doc_json.group(1))
            real = json.loads(real_json_shape)
            # normalise the `file` field, which is a temp path
            documented["file"] = real["file"] = "<path>"
            check("README 的 JSON 示例与真实 --json 输出逐字段一致",
                  documented == real,
                  json.dumps({"documented": documented, "real": real}, ensure_ascii=False)[:400])
        except json.JSONDecodeError as exc:
            check("README 的 JSON 示例可解析", False, str(exc))
    else:
        check("README 含 JSON 示例代码块", False)

print("\n" + "=" * 70)
print("8. README 指标与仓库数据一致")
print("=" * 70)
er = json.load(open("eval_results.json", encoding="utf-8"))
rm = open("README.md", encoding="utf-8").read()
check("合成 F1=1.0 与 eval_results.json 一致", er["f1_score"] == 1.0 and "F1 = 1.0" in rm)
check("447 用例数一致", er["total_cases"] == 447 and "447" in rm)
check("7 类错误全覆盖一致", len(er["type_recall"]) == 7 and "7 类" in rm)
ext = json.load(open("eval_external_results.json", encoding="utf-8"))
check("真实错误检出率 587/1402 与数据一致",
      ext["real_error_test"]["detected"] == 587
      and ext["real_error_test"]["punct_diff_lines"] == 1402
      and "587/1,402" in rm)
check("真实错误召回 41.87% 与数据一致",
      abs(ext["real_error_test"]["recall"] - 0.4187) < 0.0001 and "41.87%" in rm)
cov = open("CLAUSE_COVERAGE.md", encoding="utf-8").read()
check("覆盖矩阵声明 101 条", "101" in cov and "101 条" in rm)
for token in ["37", "4", "18", "27", "14"]:
    check(f"覆盖矩阵状态计数 {token} 在 README 中出现", token in rm)

print("\n" + "=" * 70)
print("9. README 依赖/环境声明与代码一致")
print("=" * 70)
src = open("punctuation_checker.py", encoding="utf-8").read()
stdlib = {"re", "argparse", "json", "dataclasses", "typing", "enum"}
imported = set(re.findall(r"^(?:import|from)\s+([a-zA-Z_][\w.]*)", src, re.M))
check("检查器仅依赖标准库", imported <= stdlib, str(imported - stdlib))
check("README 声明零依赖", "零依赖" in rm and "无需 `pip install`" in rm)
check("Python 版本满足 README 声明（>=3）", sys.version_info >= (3, 0))
check("README 提及的编码回退链与代码一致",
      all(e in src for e in ["utf-8", "gbk", "gb2312", "utf-8-sig"]))
check("代码行跳过规则 # 与 // 与 README 一致",
      "#" in src and "//" in src and "以 `#` 或 `//` 开头" in rm)

print("\n" + "=" * 70)
print("10. 评估脚本可运行（README 记录的评估管线）")
print("=" * 70)
r = run(["evaluate.py"])
check("evaluate.py 可运行", r.returncode == 0, r.stderr[-300:])
for k in ["f1_score", "precision", "recall"]:
    mm = re.search(rf"^{k}:\s*([\d.]+)$", r.stdout, re.M)
    check(f"evaluate.py 输出 {k}", bool(mm))
if re.search(r"^f1_score:\s*1\.0+", r.stdout, re.M):
    check("evaluate.py 复现 F1=1.0（与 README 一致）", True)
else:
    fm2 = re.search(r"^f1_score:\s*([\d.]+)$", r.stdout, re.M)
    check("evaluate.py 复现 F1=1.0（与 README 一致）", False, f"actual={fm2.group(1) if fm2 else '?'}")

print("\n" + "=" * 70)
print("11. 外部链接可达性")
print("=" * 70)
# NOTE: skills.sh/<owner>/<repo> returns 404 until the skill is actually published to
# the registry. That is expected pre-publication; the badge image still resolves.
EXPECTED_404 = {"https://skills.sh/RePinkert/punctuation-checker"}
for doc in ["README.md", "README_en.md", "SKILL.md"]:
    text = open(doc, encoding="utf-8").read()
    urls = sorted(set(re.findall(r'(?:href="|src=")(https?://[^"]+)', text)))
    for u in urls:
        quoted = urllib.parse.quote(u, safe=":/?&=%")
        try:
            req = urllib.request.Request(quoted, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception as exc:  # noqa: BLE001
            code = f"ERR {type(exc).__name__}"
        if u in EXPECTED_404:
            check(f"{doc}: {u[:72]} -> {code}（未发布前预期 404）", str(code) in {"200", "404"}, str(code))
        else:
            check(f"{doc}: {u[:72]} -> {code}", str(code).startswith("2"), str(code))

# Chinese-containing badge URLs must be percent-encoded so strict clients work
for doc in ["README.md", "README_en.md"]:
    text = open(doc, encoding="utf-8").read()
    bad = [u for u in re.findall(r'src="(https://img\.shields\.io/[^"]+)"', text)
           if any(ord(c) > 127 for c in u)]
    check(f"{doc} 徽章 URL 已百分号编码（无裸非 ASCII）", not bad, str(bad))

print("\n" + "=" * 70)
print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
print("=" * 70)
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部自测通过 ✅")
