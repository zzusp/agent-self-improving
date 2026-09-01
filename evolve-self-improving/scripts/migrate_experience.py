#!/usr/bin/env python3
"""把 legacy experience 迁移到统一 memory；默认 --check 零副作用。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import validate_entries as validator


def is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", lambda: False)
    return path.is_symlink() or is_junction()


def load_legacy(path: Path) -> tuple[dict[str, Any] | None, str, list[str]]:
    text, failures = validator.strict_text(path)
    if text is None:
        return None, "", [item.code for item in failures]
    metadata, body, parse_failures = validator.split_document(path, text)
    errors = [item.code for item in failures + parse_failures]
    if metadata is None:
        return None, body, errors
    required = set(validator.KNOWLEDGE_REQUIRED_FIELDS)
    allowed = required | set(validator.OPTIONAL_FIELDS)
    if not required.issubset(metadata) or not set(metadata).issubset(allowed):
        errors.append("E_LEGACY_FIELDS")
    if metadata.get("id") != path.stem or not str(metadata.get("id", "")).startswith("e-"):
        errors.append("E_LEGACY_ID")
    if not validator.DATE_RE.fullmatch(str(metadata.get("learned_at", ""))):
        errors.append("E_LEGACY_DATE")
    if not isinstance(metadata.get("tags"), list) or not metadata.get("tags"):
        errors.append("E_LEGACY_TAGS")
    source = metadata.get("source")
    source_values = source if isinstance(source, list) else [source]
    if not source_values or any(not isinstance(value, str) or not value.strip() for value in source_values):
        errors.append("E_LEGACY_SOURCE")
    else:
        for value in source_values:
            if value.startswith("file:"):
                source_path = Path(value[5:])
                if not source_path.is_absolute() or not source_path.is_file():
                    errors.append("E_LEGACY_SOURCE_PATH")
            elif value != "human-confirmation" and not value.startswith(("conversation:", "command:")):
                errors.append("E_LEGACY_SOURCE_KIND")
    if not 300 <= len(validator.effective_text(body)) <= 400:
        errors.append("E_LEGACY_BODY_LENGTH")
    return metadata, body, errors


def make_plan(root: Path) -> dict[str, Any]:
    experience = root / "experience"
    blockers: list[str] = []
    entries: list[dict[str, Any]] = []
    legacy_ids: set[str] = set()
    scanned_entries = 0
    if not experience.is_dir():
        blockers.append("legacy experience directory is missing")
    elif is_linklike(experience):
        blockers.append("legacy experience directory must not be a link or junction")
    if (root / "memory").exists():
        blockers.append("memory directory already exists; migration only accepts a clean target")
    for state in ("current", "archive"):
        directory = experience / state
        if not directory.is_dir():
            blockers.append(f"legacy directory is missing: experience/{state}")
            continue
        for path in sorted(directory.glob("e-*.md")):
            scanned_entries += 1
            metadata, _, errors = load_legacy(path)
            if metadata is None or errors:
                blockers.append(f"{path.name}: {', '.join(errors) or 'unreadable'}")
                continue
            old_scope = str(metadata["scope"])
            legacy_ids.add(str(metadata["id"]))
            entries.append(
                {
                    "source": str(path),
                    "state": state,
                    "old_id": metadata["id"],
                    "new_id": "m-" + str(metadata["id"])[2:],
                    "old_scope": old_scope,
                    "scope": old_scope,
                }
            )
    recurrence_directory = root / "recurrence"
    recurrence_ids = {
        path.stem for path in recurrence_directory.glob("e-*.md")
    } if recurrence_directory.is_dir() else set()
    for orphan in sorted(recurrence_ids - legacy_ids):
        blockers.append(f"orphan legacy recurrence: {orphan}")
    duplicate_new_ids = sorted({item["new_id"] for item in entries if sum(other["new_id"] == item["new_id"] for other in entries) > 1})
    if duplicate_new_ids:
        blockers.append("duplicate migrated ids: " + ", ".join(duplicate_new_ids))
    if not blockers:
        legacy_records, recurrence_failures = validator.load_recurrences(root, legacy_ids, "e-*.md")
        blockers.extend(f"legacy recurrence invalid: {item.code} {item.path}" for item in recurrence_failures)
        migrated_records = {
            "m-" + entry_id[2:]: records
            for entry_id, records in legacy_records.items()
        }
        groups: dict[Path, list[validator.Entry]] = {}
        for item in entries:
            metadata, body, errors = load_legacy(Path(item["source"]))
            if metadata is None or errors:
                blockers.append(f"legacy entry changed during check: {item['source']}")
                continue
            directory = root / "memory" / item["state"]
            destination = directory / f"{item['new_id']}.md"
            values = migrated_metadata(metadata, item)
            groups.setdefault(directory, []).append(
                validator.Entry(destination, values, body, validator.effective_text(body))
            )
        for directory, projected_entries in groups.items():
            if directory.name != "current":
                continue
            rendered = validator.render_index(directory, projected_entries, migrated_records)
            for item in validator.index_limit_failures(directory / "MEMORY.md", rendered):
                blockers.append(f"projected index exceeds limit: {directory}: {item.code}")
    return {
        "status": "ready" if not blockers else "blocked",
        "mode": "check",
        "root": str(root),
        "counts": {
            "scanned_entries": scanned_entries,
            "planned_entries": len(entries),
            "legacy_recurrences": len(recurrence_ids),
            "blockers": len(blockers),
        },
        "entries": entries,
        "blockers": blockers,
    }


def frontmatter_value(value: Any) -> list[str]:
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            lines.append(f"  - {str(item).replace(chr(10), ' ').replace(chr(13), ' ')}")
        return lines
    return [str(value).replace("\n", " ").replace("\r", " ")]


def migrated_metadata(metadata: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    migrated: dict[str, Any] = {
        "id": item["new_id"],
        "title": metadata["title"],
        "scope": item["scope"],
        "tags": metadata["tags"],
        "learned_at": metadata["learned_at"],
        "source": metadata["source"],
        "type": "lesson",
        "modified_at": f"{metadata['learned_at']}T00:00:00Z",
    }
    if "supersedes" in metadata:
        supersedes = str(metadata["supersedes"])
        migrated["supersedes"] = "m-" + supersedes[2:] if supersedes.startswith("e-") else supersedes
    return migrated


def serialize_memory(metadata: dict[str, Any], body: str, item: dict[str, Any]) -> str:
    migrated = migrated_metadata(metadata, item)
    lines = ["---"]
    for key in validator.MEMORY_REQUIRED_FIELDS + validator.OPTIONAL_FIELDS:
        if key not in migrated:
            continue
        values = frontmatter_value(migrated[key])
        if isinstance(migrated[key], list):
            lines.append(f"{key}:")
            lines.extend(values)
        else:
            lines.append(f"{key}: {values[0]}")
    lines.extend(("---", body.rstrip("\n"), ""))
    return "\n".join(lines)


def convert_recurrence(text: str, old_id: str, new_id: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0] != f"# {old_id} 复现记录":
        raise ValueError(f"unexpected recurrence heading for {old_id}")
    lines[0] = f"# {new_id} 复现记录"
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(text.encode("utf-8"))
    os.replace(temporary, path)


def build_staging(root: Path, plan: dict[str, Any]) -> Path:
    stage_root = root / f".memory-migration-{uuid.uuid4().hex}"
    try:
        return build_staging_contents(root, plan, stage_root)
    except Exception:
        if stage_root.parent == root and stage_root.name.startswith(".memory-migration-") and stage_root.exists():
            shutil.rmtree(stage_root)
        raise


def build_staging_contents(root: Path, plan: dict[str, Any], stage_root: Path) -> Path:
    memory_root = stage_root / "memory"
    for relative in ("current", "archive"):
        (memory_root / relative).mkdir(parents=True, exist_ok=True)
    recurrence_stage = stage_root / "recurrence"
    recurrence_stage.mkdir()
    for item in plan["entries"]:
        source = Path(item["source"])
        metadata, body, errors = load_legacy(source)
        if metadata is None or errors:
            raise ValueError(f"legacy entry changed after check: {source}")
        directory = memory_root / item["state"]
        destination = directory / f"{item['new_id']}.md"
        write_atomic(destination, serialize_memory(metadata, body, item))
        _, entry_failures = validator.load_entry(destination)
        if entry_failures:
            raise ValueError(f"migrated entry invalid: {destination}: {[item.code for item in entry_failures]}")
        old_recurrence = root / "recurrence" / f"{item['old_id']}.md"
        if old_recurrence.is_file():
            text = old_recurrence.read_text(encoding="utf-8")
            write_atomic(
                recurrence_stage / f"{item['new_id']}.md",
                convert_recurrence(text, str(item["old_id"]), str(item["new_id"])),
            )
    all_entries: list[validator.Entry] = []
    directories: list[Path] = [memory_root / "current", memory_root / "archive"]
    for directory in directories:
        entries, failures = validator.read_directory(directory)
        if failures:
            raise ValueError(f"staged directory invalid: {directory}: {[item.code for item in failures]}")
        all_entries.extend(entries)
    recurrence_records, recurrence_failures = validator.load_recurrences(
        stage_root,
        {str(entry.metadata["id"]) for entry in all_entries if entry.metadata.get("type") == "lesson"},
    )
    if recurrence_failures:
        raise ValueError(f"staged recurrence invalid: {[item.code for item in recurrence_failures]}")
    for directory in directories:
        entries = [entry for entry in all_entries if entry.path.parent == directory]
        index_name = "MEMORY.md" if directory.name == "current" else "INDEX.md"
        rendered = validator.render_index(directory, entries, recurrence_records)
        limits = validator.index_limit_failures(directory / index_name, rendered)
        if limits:
            raise ValueError(f"staged index exceeds limits: {directory}: {[item.code for item in limits]}")
        write_atomic(directory / index_name, rendered)
    return stage_root


def apply_plan(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    if plan["status"] != "ready":
        raise ValueError("migration plan is blocked")
    stage_root = build_staging(root, plan)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    legacy_backup = root / "legacy" / f"experience-{timestamp}"
    legacy_backup.parent.mkdir(parents=True, exist_ok=True)
    experience = root / "experience"
    installed_memory = root / "memory"
    moved_recurrences: list[tuple[Path, Path]] = []
    installed_recurrences: list[Path] = []
    recurrence_backup: Path | None = None
    try:
        os.replace(experience, legacy_backup)
        recurrence_backup = legacy_backup / "recurrence"
        recurrence_backup.mkdir()
        for item in plan["entries"]:
            old = root / "recurrence" / f"{item['old_id']}.md"
            if old.exists():
                backup = recurrence_backup / old.name
                os.replace(old, backup)
                moved_recurrences.append((backup, old))
        os.replace(stage_root / "memory", installed_memory)
        for staged in (stage_root / "recurrence").glob("*.md"):
            destination = root / "recurrence" / staged.name
            os.replace(staged, destination)
            installed_recurrences.append(destination)
        result, code = validator.command_check_root(root)
        if code != 0:
            raise ValueError(f"post-migration validation failed: {[item['code'] for item in result['failures']]}")
    except Exception:
        for path in installed_recurrences:
            if path.exists():
                os.replace(path, stage_root / "recurrence" / path.name)
        if installed_memory.exists():
            os.replace(installed_memory, stage_root / "memory")
        for backup, original in reversed(moved_recurrences):
            if backup.exists():
                os.replace(backup, original)
        if recurrence_backup and recurrence_backup.is_dir() and not any(recurrence_backup.iterdir()):
            recurrence_backup.rmdir()
        if legacy_backup.exists() and not experience.exists():
            os.replace(legacy_backup, experience)
        legacy_parent = root / "legacy"
        if legacy_parent.is_dir() and not any(legacy_parent.iterdir()):
            legacy_parent.rmdir()
        raise
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)
    return {
        "status": "pass",
        "mode": "apply",
        "root": str(root),
        "backup": str(legacy_backup),
        "counts": plan["counts"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    validator.configure_utf8()
    args = build_parser().parse_args()
    root = args.root.resolve()
    plan = make_plan(root)
    if args.check or plan["status"] != "ready":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if plan["status"] == "ready" else 1
    try:
        result = apply_plan(root, plan)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "fail", "mode": "apply", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
