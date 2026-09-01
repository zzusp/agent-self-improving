#!/usr/bin/env python3
"""只读校验 knowledge/memory 条目、仓库作用域和确定性导航。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


KNOWLEDGE_REQUIRED_FIELDS = ("id", "title", "scope", "tags", "learned_at", "source")
MEMORY_REQUIRED_FIELDS = KNOWLEDGE_REQUIRED_FIELDS + ("type", "modified_at")
OPTIONAL_FIELDS = ("supersedes",)
MEMORY_TYPES = {"user", "feedback", "project", "reference", "lesson"}
RECURRENCE_SIGNALS = {"correction", "feature-request", "knowledge-gap", "error"}
KNOWLEDGE_DIRECTORIES = ("knowledge/current", "knowledge/archive")
INDEX_MAX_LINES = 200
INDEX_MAX_BYTES = 25 * 1024
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
PROJECT_KEY_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}-[0-9a-f]{12}\Z")
FENCE_RE = re.compile(r"(?m)^\s*(```+|~~~+).*$")
LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
LINE_PREFIX_RE = re.compile(r"(?m)^\s{0,3}(?:#{1,6}\s+|>\s*|[-+*]\s+|\d+[.)]\s+)")
CONTROL_RE = re.compile(r"[`*_~]")


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Failure:
    code: str
    path: str
    expected: Any
    actual: Any
    remediation: str


@dataclass(frozen=True)
class Entry:
    path: Path
    metadata: dict[str, Any]
    body: str
    effective_text: str


@dataclass(frozen=True)
class DirectorySpec:
    relative: str
    path: Path
    index_name: str


def failure(code: str, path: Path, expected: Any, actual: Any, remediation: str) -> Failure:
    return Failure(code, str(path), expected, actual, remediation)


def strict_text(path: Path) -> tuple[str | None, list[Failure]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, [failure("E_READ", path, "readable file", str(exc), "修复读取条件后重试，不覆盖原文件。")]
    failures: list[Failure] = []
    if data.startswith(b"\xef\xbb\xbf"):
        failures.append(failure("E_BOM", path, "UTF-8 without BOM", "BOM", "移除 BOM 后重验。"))
    try:
        text = data.decode("utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8")
    except UnicodeDecodeError as exc:
        return None, failures + [failure("E_ENCODING", path, "strict UTF-8", str(exc), "转换为严格 UTF-8 后重验。")]
    trailing = [i for i, line in enumerate(text.splitlines(), 1) if line.endswith((" ", "\t"))]
    if trailing:
        failures.append(failure("E_TRAILING", path, [], trailing, "移除行尾空白后重验。"))
    return text, failures


def split_document(path: Path, text: str) -> tuple[dict[str, Any] | None, str, list[Failure]]:
    lines = text.splitlines()
    delimiters = [i for i, line in enumerate(lines) if line == "---"]
    if len(delimiters) < 2 or delimiters[0] != 0:
        return None, "", [failure("E_FRONTMATTER", path, "two --- delimiters", delimiters, "补齐合法 frontmatter。")]
    metadata, failures = parse_frontmatter(path, lines[1 : delimiters[1]])
    body = "\n".join(lines[delimiters[1] + 1 :]).strip("\n") + "\n"
    return metadata, body, failures


def parse_frontmatter(path: Path, lines: list[str]) -> tuple[dict[str, Any], list[Failure]]:
    result: dict[str, Any] = {}
    failures: list[Failure] = []
    active_list: str | None = None
    for line in lines:
        if active_list and re.match(r"^\s+-\s+", line):
            result[active_list].append(unquote(re.sub(r"^\s+-\s+", "", line).strip()))
            continue
        match = re.match(r"^([a-z_]+):(?:\s*(.*))?$", line)
        if not match:
            failures.append(failure("E_FRONTMATTER_LINE", path, "key: value or list item", line, "修正该 frontmatter 行。"))
            active_list = None
            continue
        key, raw = match.group(1), (match.group(2) or "").strip()
        if key in result:
            failures.append(failure("E_FIELD_DUPLICATE", path, "unique field", key, "删除重复字段。"))
        if raw:
            if raw.startswith("[") and raw.endswith("]"):
                result[key] = [unquote(value.strip()) for value in raw[1:-1].split(",") if value.strip()]
            else:
                result[key] = unquote(raw)
            active_list = None
        else:
            result[key] = []
            active_list = key
    return result, failures


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def effective_text(body: str) -> str:
    text = FENCE_RE.sub("", body)
    text = LINK_RE.sub(lambda match: match.group(1), text)
    text = LINE_PREFIX_RE.sub("", text)
    text = CONTROL_RE.sub("", text)
    return "".join(char for char in text if not char.isspace())


def first_summary(body: str) -> str:
    paragraphs: list[str] = []
    current: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if re.match(r"^(?:#{1,6}\s+|```|~~~)", line):
            continue
        current.append(re.sub(r"^(?:>\s*|[-+*]\s+|\d+[.)]\s+)", "", line))
    if current:
        paragraphs.append(" ".join(current))
    summary = effective_text(paragraphs[0] if paragraphs else "")
    return summary[:88]


def memory_location(path: Path) -> tuple[str, str | None] | None:
    parts = path.parts
    try:
        index = parts.index("memory")
    except ValueError:
        return None
    suffix = parts[index + 1 :]
    if len(suffix) >= 2 and suffix[0] == "global":
        return "global", None
    if len(suffix) >= 3 and suffix[0] == "projects":
        return "project", suffix[1]
    return "invalid", None


def load_entry(path: Path, enforce_length: bool = True) -> tuple[Entry | None, list[Failure]]:
    text, failures = strict_text(path)
    if text is None:
        return None, failures
    metadata, body, parse_failures = split_document(path, text)
    failures.extend(parse_failures)
    if metadata is None:
        return None, failures
    location = memory_location(path)
    is_memory = location is not None
    required_fields = MEMORY_REQUIRED_FIELDS if is_memory else KNOWLEDGE_REQUIRED_FIELDS
    allowed = set(required_fields + OPTIONAL_FIELDS)
    actual_fields = set(metadata)
    if not set(required_fields).issubset(actual_fields) or not actual_fields.issubset(allowed):
        failures.append(failure("E_FIELDS", path, {"required": required_fields, "optional": OPTIONAL_FIELDS}, sorted(actual_fields), "只保留该认知类型的必填字段及可选 supersedes。"))
        if not set(required_fields).issubset(actual_fields):
            return None, failures
    entry_id = metadata.get("id")
    if entry_id != path.stem:
        failures.append(failure("E_ID_FILENAME", path, path.stem, entry_id, "让 id 与文件名一致。"))
    expected_prefix = "m-" if is_memory else "k-"
    if not isinstance(entry_id, str) or not entry_id.startswith(expected_prefix):
        failures.append(failure("E_ID_PREFIX", path, expected_prefix, entry_id, "按认知类型修正 id 前缀。"))
    if not DATE_RE.fullmatch(str(metadata.get("learned_at", ""))):
        failures.append(failure("E_DATE", path, "YYYY-MM-DD", metadata.get("learned_at"), "修正 learned_at。"))
    if is_memory:
        if location and location[0] == "invalid":
            failures.append(failure("E_MEMORY_LOCATION", path, "memory/global or memory/projects/<key>", str(path.parent), "移动到合法记忆作用域。"))
        if metadata.get("type") not in MEMORY_TYPES:
            failures.append(failure("E_MEMORY_TYPE", path, sorted(MEMORY_TYPES), metadata.get("type"), "使用五类记忆 type 之一。"))
        if not TIMESTAMP_RE.fullmatch(str(metadata.get("modified_at", ""))):
            failures.append(failure("E_MODIFIED_AT", path, "UTC YYYY-MM-DDTHH:MM:SSZ", metadata.get("modified_at"), "写入可比较的 UTC 修改时点。"))
        scope = str(metadata.get("scope", ""))
        if location and location[0] == "global" and scope != "global":
            failures.append(failure("E_MEMORY_SCOPE", path, "global", scope, "全局记忆必须使用 global scope。"))
        if location and location[0] == "project":
            project_key = location[1] or ""
            if not scope.startswith(f"repo:{project_key}"):
                failures.append(failure("E_MEMORY_SCOPE", path, f"repo:{project_key}", scope, "让项目记忆 scope 与物理仓库桶一致。"))
    if not isinstance(metadata.get("tags"), list) or not metadata.get("tags"):
        failures.append(failure("E_TAGS", path, "non-empty inline list", metadata.get("tags"), "写入非空 tags 列表。"))
    source = metadata.get("source")
    source_values = source if isinstance(source, list) else [source]
    if not source_values or any(not isinstance(value, str) or not value.strip() for value in source_values):
        failures.append(failure("E_SOURCE", path, "non-empty source or source list", source, "保留可回查的非空来源。"))
    else:
        for value in source_values:
            if value.startswith("file:"):
                source_path = Path(value[5:])
                if not source_path.is_absolute() or not source_path.is_file():
                    failures.append(failure("E_SOURCE_PATH", path, "existing absolute file source", value, "回查并修正 file source；不要猜路径。"))
            elif value != "human-confirmation" and not value.startswith(("conversation:", "command:")):
                failures.append(failure("E_SOURCE_KIND", path, "file:/conversation:/command:/human-confirmation", value, "使用受支持且可追溯的 source。"))
    compact = effective_text(body)
    minimum, maximum = (40, 800) if is_memory else (300, 400)
    if enforce_length and not minimum <= len(compact) <= maximum:
        failures.append(failure("E_BODY_LENGTH", path, f"{minimum}..{maximum} Unicode code points", len(compact), "依据原证据扩充或压缩正文，不得机械凑字。"))
    if not first_summary(body):
        failures.append(failure("E_SUMMARY_EMPTY", path, "content-specific first summary", "", "让正文首个概括表达条目特异内容。"))
    return Entry(path, metadata, body, compact), failures


def display_source(value: Any) -> str:
    values = value if isinstance(value, list) else [value]
    shown: list[str] = []
    for item in values:
        text = str(item)
        if text.startswith("file:"):
            normalized = text[5:].replace("\\", "/")
            parts = [part for part in normalized.split("/") if part]
            suffix = parts[-3:] if len(parts) >= 3 and parts[-2:] == [".git", "config"] else parts[-2:]
            shown.append("file:" + "/".join(suffix))
        else:
            shown.append(text[:56])
    return "<br>".join(shown)


def load_recurrences(root: Path, allowed_ids: set[str]) -> tuple[dict[str, list[dict[str, str]]], list[Failure]]:
    directory = root / "recurrence"
    if not directory.exists():
        return {}, []
    if not directory.is_dir():
        return {}, [failure("E_RECURRENCE_DIRECTORY", directory, "directory", "not a directory", "恢复 recurrence 目录后重验。")]
    records: dict[str, list[dict[str, str]]] = {}
    failures: list[Failure] = []
    expected_header = "| observed_at | source | scope | signal | summary |"
    expected_rule = "|---|---|---|---|---|"
    for path in sorted(directory.glob("*.md")):
        text, item_failures = strict_text(path)
        failures.extend(item_failures)
        if text is None:
            continue
        entry_id = path.stem
        if entry_id not in allowed_ids:
            failures.append(failure("E_RECURRENCE_ORPHAN", path, "knowledge or lesson memory id", entry_id, "迁移、删除孤儿记录或恢复对应条目。"))
        lines = text.splitlines()
        if len(lines) < 5 or lines[0] != f"# {entry_id} 复现记录" or lines[2] != expected_header or lines[3] != expected_rule:
            failures.append(failure("E_RECURRENCE_FORMAT", path, "title + fixed five-column table", lines[:4], "按 Skill 的复现表格格式修正。"))
            continue
        seen_sources: set[str] = set()
        rows: list[dict[str, str]] = []
        for number, line in enumerate(lines[4:], 5):
            if not line.strip():
                continue
            cells = [value.strip() for value in line.strip().strip("|").split("|")]
            if len(cells) != 5:
                failures.append(failure("E_RECURRENCE_ROW", path, "five cells", {"line": number, "value": line}, "修正该证据行。"))
                continue
            observed_at, source, scope, signal, summary = cells
            if not DATE_RE.fullmatch(observed_at):
                failures.append(failure("E_RECURRENCE_DATE", path, "YYYY-MM-DD", observed_at, "修正复现日期。"))
            if not source or source in seen_sources:
                failures.append(failure("E_RECURRENCE_SOURCE", path, "unique non-empty source", source, "移除重复来源或补充新的独立来源。"))
            elif source.startswith("file:"):
                source_path = Path(source[5:])
                if not source_path.is_absolute() or not source_path.is_file():
                    failures.append(failure("E_RECURRENCE_SOURCE_PATH", path, "existing absolute file source", source, "回查并修正复现来源；不要猜路径。"))
            elif not source.startswith(("conversation:", "command:")) and source != "human-confirmation":
                failures.append(failure("E_RECURRENCE_SOURCE_KIND", path, "traceable source", source, "使用受支持来源。"))
            seen_sources.add(source)
            if not scope or not summary:
                failures.append(failure("E_RECURRENCE_CONTENT", path, "non-empty scope and summary", cells, "补齐适用范围和特异概括。"))
            if signal not in RECURRENCE_SIGNALS:
                failures.append(failure("E_RECURRENCE_SIGNAL", path, sorted(RECURRENCE_SIGNALS), signal, "使用四类学习信号之一。"))
            rows.append({"observed_at": observed_at, "source": source, "scope": scope, "signal": signal, "summary": summary})
        if not rows:
            failures.append(failure("E_RECURRENCE_EMPTY", path, "at least one evidence row", 0, "没有复现时删除该文件。"))
        records[entry_id] = rows
    return records, failures


def cell(value: Any) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def recurrence_label(records: list[dict[str, str]]) -> str:
    if not records:
        return "0"
    return f"{len(records)}（最近 {max(item['observed_at'] for item in records)}）"


def is_current_memory_directory(directory: Path) -> bool:
    return directory.name == "current" and memory_location(directory / "placeholder.md") is not None


def render_index(directory: Path, entries: list[Entry], recurrences: dict[str, list[dict[str, str]]] | None = None) -> str:
    if is_current_memory_directory(directory):
        lines = [
            "# Memory",
            "",
            "当前作用域的精简召回入口；每条一行，命中后再打开主题文件并按来源复核。",
            "",
        ]
        ordered = sorted(entries, key=lambda entry: str(entry.metadata["id"]))
        ordered.sort(key=lambda entry: str(entry.metadata["modified_at"]), reverse=True)
        for entry in ordered:
            meta = entry.metadata
            recurrence = (recurrences or {}).get(str(meta["id"]), [])
            recurrence_text = f" | recurrence:{recurrence_label(recurrence)}" if recurrence else ""
            lines.append(
                f"- [{cell(meta['id'])}](./{entry.path.name}) | {cell(meta['type'])} | {cell(meta['scope'])} | "
                f"{cell(meta['modified_at'])} | tags:{cell(meta['tags'])} | {cell(meta['title'])} | "
                f"{cell(first_summary(entry.body))}{recurrence_text}"
            )
        return "\n".join(lines) + "\n"
    kind = "知识" if "knowledge" in directory.parts else "记忆"
    state = "当前" if directory.name == "current" else "归档"
    lines = [
        f"# {state}{kind}导航",
        "",
        "本文件只用于缩小只读检索候选；结论仍须打开条目并按来源回查。",
        "",
        "| 条目 | title | scope | tags | learned_at | source | 复现 | 特异概括 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(entries, key=lambda entry: str(entry.metadata["id"]))
    ordered.sort(key=lambda entry: str(entry.metadata["learned_at"]), reverse=True)
    for entry in ordered:
        meta = entry.metadata
        link = f"[{cell(meta['id'])}](./{entry.path.name})"
        lines.append(
            "| " + " | ".join(
                (
                    link,
                    cell(meta["title"]),
                    cell(meta["scope"]),
                    cell(meta["tags"]),
                    cell(meta["learned_at"]),
                    cell(display_source(meta["source"])),
                    cell(recurrence_label((recurrences or {}).get(str(meta["id"]), []))),
                    cell(first_summary(entry.body)),
                )
            ) + " |"
        )
    return "\n".join(lines) + "\n"


def index_limit_failures(path: Path, text: str) -> list[Failure]:
    if path.name != "MEMORY.md":
        return []
    failures: list[Failure] = []
    line_count = len(text.splitlines())
    byte_count = len(text.encode("utf-8"))
    if line_count > INDEX_MAX_LINES:
        failures.append(failure("E_MEMORY_INDEX_LINES", path, f"<= {INDEX_MAX_LINES}", line_count, "合并或归档低价值记忆后重建索引。"))
    if byte_count > INDEX_MAX_BYTES:
        failures.append(failure("E_MEMORY_INDEX_BYTES", path, f"<= {INDEX_MAX_BYTES}", byte_count, "缩短索引概括、合并或归档记忆后重建。"))
    return failures


def read_directory(directory: Path) -> tuple[list[Entry], list[Failure]]:
    entries: list[Entry] = []
    failures: list[Failure] = []
    for path in sorted(directory.glob("*.md")):
        if path.name in {"INDEX.md", "MEMORY.md"}:
            continue
        entry, item_failures = load_entry(path)
        failures.extend(item_failures)
        if entry:
            entries.append(entry)
    return entries, failures


def load_project_scope(project_directory: Path) -> list[Failure]:
    path = project_directory / "scope.json"
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [failure("E_PROJECT_SCOPE_FILE", path, "readable UTF-8 JSON", str(exc), "重建仓库作用域清单。")]
    if not isinstance(data, dict):
        return [failure("E_PROJECT_SCOPE_FIELDS", path, "JSON object", type(data).__name__, "重建固定字段的作用域对象。")]
    failures: list[Failure] = []
    key = project_directory.name
    expected_fields = {"project_key", "git_common_dir", "roots"}
    if set(data) != expected_fields:
        failures.append(failure("E_PROJECT_SCOPE_FIELDS", path, sorted(expected_fields), sorted(data), "只保留固定作用域字段。"))
    if data.get("project_key") != key or not PROJECT_KEY_RE.fullmatch(key):
        failures.append(failure("E_PROJECT_KEY", path, key, data.get("project_key"), "使用 slug + 12 位 identity hash。"))
    if not isinstance(data.get("git_common_dir"), str) or not Path(data.get("git_common_dir", "")).is_absolute():
        failures.append(failure("E_GIT_COMMON_DIR", path, "absolute normalized path", data.get("git_common_dir"), "记录 git rev-parse 得到的绝对 common dir。"))
    roots = data.get("roots")
    if not isinstance(roots, list) or not roots or any(not isinstance(item, str) or not Path(item).is_absolute() for item in roots):
        failures.append(failure("E_PROJECT_ROOTS", path, "non-empty absolute path list", roots, "记录至少一个仓库根路径别名。"))
    return failures


def discover_directories(root: Path) -> tuple[list[DirectorySpec], list[Failure]]:
    specs = [
        DirectorySpec(relative, root / relative, "INDEX.md")
        for relative in KNOWLEDGE_DIRECTORIES
    ]
    specs.extend(
        (
            DirectorySpec("memory/global/current", root / "memory/global/current", "MEMORY.md"),
            DirectorySpec("memory/global/archive", root / "memory/global/archive", "INDEX.md"),
        )
    )
    failures: list[Failure] = []
    projects = root / "memory/projects"
    if not projects.is_dir():
        failures.append(failure("E_DIRECTORY", projects, "existing directory", "missing", "初始化 memory/projects。"))
        return specs, failures
    for project in sorted(path for path in projects.iterdir() if path.is_dir()):
        is_junction = getattr(project, "is_junction", lambda: False)
        if project.is_symlink() or is_junction():
            failures.append(failure("E_PROJECT_LINK", project, "real directory", "link or junction", "移除重解析入口并使用真实目录。"))
            continue
        failures.extend(load_project_scope(project))
        relative = f"memory/projects/{project.name}"
        specs.extend(
            (
                DirectorySpec(f"{relative}/current", project / "current", "MEMORY.md"),
                DirectorySpec(f"{relative}/archive", project / "archive", "INDEX.md"),
            )
        )
    return specs, failures


def report(mode: str, entries: list[Entry], failures: list[Failure]) -> dict[str, Any]:
    lengths = [len(entry.effective_text) for entry in entries]
    return {
        "status": "pass" if not failures else "fail",
        "mode": mode,
        "counts": {
            "entries": len(entries),
            "failures": len(failures),
            "min_effective_chars": min(lengths) if lengths else None,
            "max_effective_chars": max(lengths) if lengths else None,
        },
        "failures": [asdict(item) for item in failures],
    }


def command_check_root(root: Path) -> tuple[dict[str, Any], int]:
    specs, failures = discover_directories(root)
    legacy = root / "experience"
    if legacy.exists():
        failures.append(failure("E_LEGACY_EXPERIENCE", legacy, "migrated or absent", "present", "先运行 migrate_experience.py --check，完成迁移后再校验。"))
    entries: list[Entry] = []
    per_directory: dict[str, int] = {}
    for spec in specs:
        if not spec.path.is_dir():
            failures.append(failure("E_DIRECTORY", spec.path, "existing directory", "missing", "补齐认知目录。"))
            continue
        found, item_failures = read_directory(spec.path)
        entries.extend(found)
        failures.extend(item_failures)
        per_directory[spec.relative] = len(found)
    allowed_recurrence_ids = {
        str(entry.metadata["id"])
        for entry in entries
        if "knowledge" in entry.path.parts or entry.metadata.get("type") == "lesson"
    }
    recurrences, recurrence_failures = load_recurrences(root, allowed_recurrence_ids)
    failures.extend(recurrence_failures)
    for spec in specs:
        if not spec.path.is_dir():
            continue
        directory_entries = [entry for entry in entries if entry.path.parent == spec.path]
        index_path = spec.path / spec.index_name
        actual, index_failures = strict_text(index_path)
        failures.extend(index_failures)
        if actual is not None:
            expected = render_index(spec.path, directory_entries, recurrences)
            failures.extend(index_limit_failures(index_path, actual))
            if actual != expected:
                failures.append(failure("E_INDEX_MISMATCH", index_path, expected, actual, "用 render-index 原子重建并读回该目录索引。"))
    result = report("root", entries, failures)
    result["counts"]["directories"] = per_directory
    result["counts"]["recurrence_files"] = len(recurrences)
    result["counts"]["recurrences"] = sum(len(items) for items in recurrences.values())
    return result, 0 if not failures else 1


def command_check_file(path: Path) -> tuple[dict[str, Any], int]:
    entry, failures = load_entry(path)
    result = report("file", [entry] if entry else [], failures)
    return result, 0 if not failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    target = check.add_mutually_exclusive_group(required=True)
    target.add_argument("--root", type=Path)
    target.add_argument("--file", type=Path)
    check.add_argument("--json", action="store_true")
    render = subparsers.add_parser("render-index")
    render.add_argument("--directory", type=Path, required=True)
    return parser


def main() -> int:
    configure_utf8()
    args = build_parser().parse_args()
    if args.command == "render-index":
        entries, failures = read_directory(args.directory)
        root = args.directory
        while root.parent != root and not (root / "knowledge").exists():
            root = root.parent
        specs, discovery_failures = discover_directories(root)
        failures.extend(discovery_failures)
        all_entries: list[Entry] = []
        for spec in specs:
            if spec.path.is_dir():
                found, _ = read_directory(spec.path)
                all_entries.extend(found)
        allowed_ids = {
            str(entry.metadata["id"])
            for entry in all_entries
            if "knowledge" in entry.path.parts or entry.metadata.get("type") == "lesson"
        }
        recurrences, recurrence_failures = load_recurrences(root, allowed_ids)
        failures.extend(recurrence_failures)
        rendered = render_index(args.directory, entries, recurrences)
        index_name = "MEMORY.md" if is_current_memory_directory(args.directory) else "INDEX.md"
        failures.extend(index_limit_failures(args.directory / index_name, rendered))
        if failures:
            print(json.dumps(report("render-index", entries, failures), ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        sys.stdout.write(rendered)
        return 0
    result, code = command_check_root(args.root) if args.root else command_check_file(args.file)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status={result['status']} entries={result['counts']['entries']} failures={result['counts']['failures']}")
        for item in result["failures"]:
            print(f"{item['code']} {item['path']}: actual={item['actual']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
