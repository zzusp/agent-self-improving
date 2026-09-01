# Memory model 验收报告

## 结论

源码、fixture 与当前本机真实迁移验收全绿：memory 已成为 experience 的超集，保留 `lesson` 学习；global 与项目 memory 物理隔离；同仓库 worktree 共享 Git identity，非 Git 工作区使用规范化根目录 identity；索引含 tags 并执行 200 行/25KB 双门禁；legacy 迁移已完成零副作用检查、显式 scope map、正文/复现保留、备份和安装后全根校验。

## 证据

- 15 个 unittest 全部通过。
- 3 个 Python 文件 AST 解析通过。
- 当前真实数据 `--check` 扫描并计划 59 条 experience，形成 3 个项目桶、识别 1 个旧复现，0 blocker；预检前后根目录清单未变化。
- `--apply` 成功后独立 root 校验得到 88 个条目、0 failure；59 条迁移正文和关键字段逐条比较 0 mismatch，1 个旧复现转换一致且既有 knowledge 复现保留。
- 三个项目 `MEMORY.md` 均低于 200 行/25KB；旧 `experience/` 已移动到带 UTC 时间戳的 legacy 备份，staging 残留为 0。
- 用户随后明确授权更新本地数据根 README；旧 experience 契约词零命中，当前 knowledge/memory 结构、五类 memory、项目 identity、导航和正文门禁均已写入。文件为 UTF-8 无 BOM、无尾随空白，更新后 root 校验仍为 88 个条目、0 failure。

## 边界

- 未发布新 Skill 版本，也未验证 skills.sh、SkillHub 或 ClawHub 安装后的运行态。

因此本报告证明当前本机数据迁移闭环与源码行为，不声称已完成 Skill 市场发布或其他运行环境部署。
