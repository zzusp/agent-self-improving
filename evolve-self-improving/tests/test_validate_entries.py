from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module("validate_entries", SCRIPTS / "validate_entries.py")
migrator = load_module("migrate_experience", SCRIPTS / "migrate_experience.py")


class ValidateEntriesTest(unittest.TestCase):
    def write_bytes(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def initialize_root(self, root: Path) -> None:
        directories = (
            (root / "knowledge/current", "INDEX.md"),
            (root / "knowledge/archive", "INDEX.md"),
            (root / "memory/current", "MEMORY.md"),
            (root / "memory/archive", "INDEX.md"),
        )
        for directory, index_name in directories:
            directory.mkdir(parents=True)
            self.write_bytes(directory / index_name, validator.render_index(directory, []))
        (root / "recurrence").mkdir()

    def write_memory(
        self,
        directory: Path,
        *,
        memory_type: str,
        scope: str,
        entry_id: str = "m-20260901-120000-testing",
        tags: str = "testing, workflow",
        body: str | None = None,
    ) -> Path:
        path = directory / f"{entry_id}.md"
        self.write_bytes(
            path,
            "---\n"
            f"id: {entry_id}\n"
            "title: 测试记忆\n"
            f"scope: {scope}\n"
            f"tags: [{tags}]\n"
            "learned_at: 2026-09-01\n"
            "source: human-confirmation\n"
            f"type: {memory_type}\n"
            "modified_at: 2026-09-01T12:00:00Z\n"
            "---\n"
            + (body or "用户明确确认测试前应先读取当前实现；这条记忆会影响后续会话的判断顺序，但不是强制执行规则。")
            + "\n",
        )
        return path

    def write_legacy_experience(self, root: Path, *, scope: str = "global") -> Path:
        for state in ("current", "archive"):
            directory = root / "experience" / state
            directory.mkdir(parents=True)
            self.write_bytes(directory / "INDEX.md", "# legacy\n")
        body = (
            "适用条件：诊断已经由当前运行证据收敛，并且同类任务以后仍可能遇到。"
            "问题模式：只保存原始错误会让后续会话重复排查，也无法区分偶发现象和稳定方法。"
            "推荐做法：记录触发条件、根因、最短复核路径、有效处理方式和失败边界；调用前仍需核对当前版本与现场。"
            "失败边界：证据尚未闭环、只能从代码直接推导或包含敏感原文时不得沉淀。"
            "回查方法：重新运行最小验证并读取权威来源，若现场冲突则纠正或归档旧记录。"
            "本条只用于验证迁移保持方法型学习，不代表强制规则，也不替代当前证据。"
            "再次使用时先确认任务对象、运行版本、配置入口和失败症状与原记录相同；只要关键条件不同，就只能把它当作候选线索，不能直接照搬旧结论。"
            "若复核发现原方法遗漏了必要条件，应追加独立来源并修正适用边界；若结论被明确证伪，则建立替代记录后归档旧条目。"
        )
        self.assertGreaterEqual(len(validator.effective_text(body)), 300)
        self.assertLessEqual(len(validator.effective_text(body)), 400)
        path = root / "experience/current/e-20260901-120000-testing.md"
        self.write_bytes(
            path,
            "---\n"
            "id: e-20260901-120000-testing\n"
            "title: 已验证的诊断方法\n"
            f"scope: {scope}\n"
            "tags: [diagnosis, error]\n"
            "learned_at: 2026-09-01\n"
            "source: human-confirmation\n"
            "---\n"
            + body
            + "\n",
        )
        return path

    def test_all_five_memory_types_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            for index, memory_type in enumerate(sorted(validator.MEMORY_TYPES)):
                path = self.write_memory(
                    root / "memory/current",
                    memory_type=memory_type,
                    scope="workspace:example",
                    entry_id=f"m-20260901-12000{index}-{memory_type}",
                )
                _, failures = validator.load_entry(path)
                self.assertEqual([], failures, memory_type)

    def test_memory_index_contains_tags_for_recall(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            path = self.write_memory(
                root / "memory/current",
                memory_type="lesson",
                scope="workspace:example",
                tags="oauth, callback-listener",
            )
            entry, failures = validator.load_entry(path)
            self.assertEqual([], failures)
            rendered = validator.render_index(root / "memory/current", [entry])
            self.assertIn("tags:oauth, callback-listener", rendered)

    def test_memory_rejects_unknown_type_and_empty_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            path = self.write_memory(
                root / "memory/current",
                memory_type="experience",
                scope="",
            )
            _, failures = validator.load_entry(path)
            codes = {item.code for item in failures}
            self.assertIn("E_MEMORY_TYPE", codes)
            self.assertIn("E_MEMORY_SCOPE", codes)

    def test_root_discovers_unified_memory_and_lesson_recurrence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            path = self.write_memory(
                root / "memory/current",
                memory_type="lesson",
                scope="workspace:example",
            )
            recurrence = (
                "# m-20260901-120000-testing 复现记录\n\n"
                "| observed_at | source | scope | signal | summary |\n"
                "|---|---|---|---|---|\n"
                "| 2026-09-02 | human-confirmation | workspace:example | error | 再次验证同一问题模式 |\n"
            )
            self.write_bytes(root / "recurrence/m-20260901-120000-testing.md", recurrence)
            entry, failures = validator.load_entry(path)
            self.assertEqual([], failures)
            records, failures = validator.load_recurrences(root, {str(entry.metadata["id"])})
            self.assertEqual([], failures)
            self.write_bytes(root / "memory/current/MEMORY.md", validator.render_index(root / "memory/current", [entry], records))

            result, code = validator.command_check_root(root)

            self.assertEqual(0, code, result["failures"])
            self.assertEqual(1, result["counts"]["recurrences"])

    def test_cli_render_and_root_check_match_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            directory = root / "memory/current"
            expected = (directory / "MEMORY.md").read_text(encoding="utf-8")

            rendered = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "validate_entries.py"), "render-index", "--directory", str(directory)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            checked = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "validate_entries.py"), "check", "--root", str(root), "--json"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(expected, rendered.stdout)
            self.assertEqual("pass", json.loads(checked.stdout)["status"])

    def test_memory_index_enforces_line_limit_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "memory/current"
            directory.mkdir(parents=True)
            entries = []
            for index in range(197):
                path = self.write_memory(
                    directory,
                    memory_type="user",
                    scope="global",
                    entry_id=f"m-20260901-12{index:04d}-entry",
                    tags="very-long-recall-tag-" + ("x" * 120),
                )
                entry, failures = validator.load_entry(path)
                self.assertEqual([], failures)
                entries.append(entry)
            rendered = validator.render_index(directory, entries)
            codes = {item.code for item in validator.index_limit_failures(directory / "MEMORY.md", rendered)}
            self.assertIn("E_MEMORY_INDEX_LINES", codes)
            self.assertNotIn("E_MEMORY_INDEX_BYTES", codes)

    def test_root_rejects_unmigrated_experience(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            self.write_legacy_experience(root)

            result, code = validator.command_check_root(root)

            self.assertEqual(1, code)
            self.assertIn("E_LEGACY_EXPERIENCE", {item["code"] for item in result["failures"]})

    def test_root_rejects_old_project_memory_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.initialize_root(root)
            (root / "memory/projects").mkdir()

            result, code = validator.command_check_root(root)

            self.assertEqual(1, code)
            self.assertIn("E_MEMORY_LAYOUT", {item["code"] for item in result["failures"]})

    def test_migration_preserves_legacy_lesson_and_recurrence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for state in ("current", "archive"):
                directory = root / "knowledge" / state
                directory.mkdir(parents=True)
                self.write_bytes(directory / "INDEX.md", validator.render_index(directory, []))
            (root / "recurrence").mkdir()
            self.write_legacy_experience(root)
            self.write_bytes(
                root / "recurrence/e-20260901-120000-testing.md",
                "# e-20260901-120000-testing 复现记录\n\n"
                "| observed_at | source | scope | signal | summary |\n"
                "|---|---|---|---|---|\n"
                "| 2026-09-02 | human-confirmation | global | error | 再次验证同一问题模式 |\n",
            )
            plan = migrator.make_plan(root)
            self.assertEqual("ready", plan["status"], plan["blockers"])

            result = migrator.apply_plan(root, plan)

            self.assertEqual("pass", result["status"])
            self.assertFalse((root / "experience").exists())
            migrated = root / "memory/current/m-20260901-120000-testing.md"
            self.assertTrue(migrated.is_file())
            self.assertIn("type: lesson", migrated.read_text(encoding="utf-8"))
            self.assertTrue((root / "recurrence/m-20260901-120000-testing.md").is_file())
            self.assertTrue(Path(result["backup"]).is_dir())
            checked, code = validator.command_check_root(root)
            self.assertEqual(0, code, checked["failures"])

    def test_non_global_scope_migrates_without_project_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "knowledge-root"
            for state in ("current", "archive"):
                directory = root / "knowledge" / state
                directory.mkdir(parents=True)
                self.write_bytes(directory / "INDEX.md", validator.render_index(directory, []))
            (root / "recurrence").mkdir()
            self.write_legacy_experience(root, scope="workspace:example")

            plan = migrator.make_plan(root)

            self.assertEqual("ready", plan["status"], plan["blockers"])
            result = migrator.apply_plan(root, plan)
            migrated = root / "memory/current/m-20260901-120000-testing.md"
            self.assertEqual("pass", result["status"])
            self.assertTrue(migrated.is_file())
            self.assertIn("scope: workspace:example", migrated.read_text(encoding="utf-8"))

    def test_failed_post_validation_restores_legacy_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for state in ("current", "archive"):
                directory = root / "knowledge" / state
                directory.mkdir(parents=True)
                self.write_bytes(directory / "INDEX.md", validator.render_index(directory, []))
            self.write_bytes(root / "knowledge/current/INDEX.md", "broken\n")
            (root / "recurrence").mkdir()
            self.write_legacy_experience(root)
            plan = migrator.make_plan(root)
            self.assertEqual("ready", plan["status"], plan["blockers"])

            with self.assertRaises(ValueError):
                migrator.apply_plan(root, plan)

            self.assertTrue((root / "experience/current/e-20260901-120000-testing.md").is_file())
            self.assertFalse((root / "memory").exists())
            self.assertFalse((root / "legacy").exists())

    def test_staging_failure_removes_temporary_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "recurrence").mkdir()
            legacy = self.write_legacy_experience(root)
            plan = migrator.make_plan(root)
            self.assertEqual("ready", plan["status"], plan["blockers"])
            self.write_bytes(legacy, "changed after check\n")

            with self.assertRaises(ValueError):
                migrator.build_staging(root, plan)

            self.assertEqual([], list(root.glob(".memory-migration-*")))
            self.assertTrue((root / "experience").is_dir())

    def test_check_accepts_non_global_scope_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "recurrence").mkdir()
            self.write_legacy_experience(root, scope="workspace:example")
            before = sorted(str(path.relative_to(root)) for path in root.rglob("*"))

            plan = migrator.make_plan(root)

            after = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            self.assertEqual("ready", plan["status"], plan["blockers"])
            self.assertEqual(before, after)

    def test_migration_check_ignores_non_legacy_recurrence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "recurrence").mkdir()
            self.write_legacy_experience(root)
            self.write_bytes(
                root / "recurrence/k-20260901-120000-existing.md",
                "# k-20260901-120000-existing 复现记录\n\n"
                "| observed_at | source | scope | signal | summary |\n"
                "|---|---|---|---|---|\n"
                "| 2026-09-01 | human-confirmation | global | feedback | 已有知识复现不属于本次经验迁移 |\n",
            )

            plan = migrator.make_plan(root)

            self.assertEqual("ready", plan["status"], plan["blockers"])
            self.assertEqual(0, plan["counts"]["legacy_recurrences"])

if __name__ == "__main__":
    unittest.main()
