# Memory model 验收报告

## 结论

源码、fixture 与当前本机真实数据验收全绿。memory 是 experience 的超集并保留 `lesson`，但不再按项目拆分：所有记忆只进入 `memory/current` 或 `memory/archive`，scope 只作业务标签。项目识别、Git/非 Git 判断、project key、roots、`scope.json` 和 25KB byte 门禁均已从当前设计删除。

## 证据

- 14 个当前 unittest 全部通过。
- 3 个 Python 文件 AST 解析通过。
- legacy experience 迁移现在无需 scope map；非 global scope 原样进入统一 memory，正文、来源、日期、归档状态和复现仍保持。
- 本机项目桶迁移 `-Check` 得到 59 条源 memory、0 重复 id、0 blocker；`-Apply` 后独立 root 校验得到 88 个条目、0 failure。
- 旧备份与新目录逐条比较为 59/59、0 mismatch；新目录只含 current/archive，`scope: repo:` 和 staging 残留均为 0。
- 统一 `MEMORY.md` 为 63 行、25696 bytes，验证只保留 200 行门禁即可承载当前数据，无需项目桶或 25KB 门禁。
- 本地数据根 README 与两个 Skill 都只声明统一 memory 目录及标签式 scope。

## 边界

- 未发布新 Skill 版本，也未验证 skills.sh、SkillHub 或 ClawHub 安装后的运行态。

因此本报告证明当前本机数据迁移闭环与源码行为，不声称已完成 Skill 市场发布或其他运行环境部署。
