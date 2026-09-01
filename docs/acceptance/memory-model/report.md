# Memory model 验收报告

## 结论

源码、fixture 与当前本机真实数据验收全绿。memory 不按项目拆分，所有记忆只进入 `memory/current` 或 `memory/archive`，scope 只作业务标签。每条 memory 现在必须包含 Agent 编写的语义 `summary`；`MEMORY.md` 只保留 title link、scope 和 summary，并同时执行 200 行与 25000 bytes 门禁。

## 证据

- 17 个当前 unittest 全部通过。
- 3 个 Python 文件 AST 解析通过。
- 两个 Skill 经 `skill-creator` quick validate 通过；Windows 首次 GBK 读取失败后使用 Python UTF-8 模式成功复验。
- summary 缺失、过短或过长会被拒绝；渲染器原样使用 summary，正文首句不会进入 current 索引。
- legacy experience 迁移现在无需 scope map，但必须先由 Agent 补齐语义 summary；迁移器只校验和保留摘要，不机械生成。
- 本机 63 条 current memory 已逐条阅读并补写 summary；统一 `MEMORY.md` 为 67 行、17426 bytes、63 个条目。
- 索引中的 tags、modified_at、type、recurrence 均为 0；这些细节仍保留在主题文件或复现文件中，命中后读取。
- 本机完整 root 校验得到 92 个条目、0 failure；knowledge current/archive 为 27/2，memory current/archive 为 63/0，2 个复现文件共 3 条记录。
- 本地数据根 README 与两个 Skill 已同步语义 summary、统一目录和索引双门禁契约。

## 边界

- 未发布新 Skill 版本，也未验证 skills.sh、SkillHub 或 ClawHub 安装后的运行态。

因此本报告证明当前本机数据迁移闭环与源码行为，不声称已完成 Skill 市场发布或其他运行环境部署。
