# Round 5：从原始 experience 重新迁移

## 目标

不复用已扁平化的 memory 作为迁移源，直接从最早的 legacy experience 备份重新运行当前统一 memory 迁移器，并在完整校验后原子替换本机 memory 与 recurrence。

## 迁移源与预检

- 原始备份：`legacy/experience-20260901T045151Z`，含 current 59 条、archive 0 条、旧 `e-*` 复现 1 个；目录不是链接或 junction。
- 执行前数据根校验为 pass：88 条认知，memory current/archive 为 59/0，2 个复现文件共 3 条记录。
- 在隔离临时根复制 knowledge、recurrence 和原始 experience 后运行 `migrate_experience.py --check`：扫描 59 条、计划 59 条、识别 1 个旧复现、0 blocker。检查未改写真实数据根。

## 执行

在同结构的全新临时根运行 `migrate_experience.py --apply`，完整 root 校验通过后，将真实数据根的旧 memory 与 recurrence 移到 `legacy/before-experience-remigration-20260901T063258Z`，再原子安装新结果。安装后完整校验再次通过，临时根已清理。

## 独立回读

- `validate_entries.py check --root ... --json` 返回 pass：88 条认知，memory current/archive 为 59/0，2 个复现文件共 3 条记录。
- 原始 59 条 `e-*` 与新 59 条 `m-*` 一一对应；正文、title、scope、learned_at 比较为 59/59、0 mismatch。
- 原始 `e-*` 复现只替换标题 id 后，与新 `m-*` 复现完全一致；既有 knowledge 复现保留。
- 新 memory 与本轮替换前的 memory 逐文件 SHA-256 比较为 59/59、0 mismatch，说明上一轮扁平迁移和本轮从原始 experience 直迁得到相同结果。
- 回滚备份含 memory 59 条、recurrence 2 个；原始 experience 备份仍为 59 条并保持原位；系统临时目录残留为 0。

首次正文比对把旧 frontmatter 后的空白行算入正文，误报 50 条差异；抽样定位后改为比较去除边界空白的正文以及 title/scope/date，结果为 0 mismatch。整文件 SHA 比较同时证明新结果与替换前 memory 完全一致。
