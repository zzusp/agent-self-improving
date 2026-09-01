# Round 3

## 目标

在用户明确授权后，把当前本机数据根 `~/.agent-knowledge/README.md` 从 legacy knowledge/experience 契约更新为实际 knowledge/memory 结构；保留既有项目、文件与 collection 蒸馏规则，不改写任何认知条目。

## 更新内容

- 三个 Skill 的分工改为 distill 只维护索引与 collection、evolve 维护 knowledge 和五类 memory、use 只读 global 与当前项目的精简导航。
- 目录树改为 `knowledge/`、`memory/global/`、`memory/projects/<project-key>/`、`recurrence/` 与 `legacy/`，并记录 Git common dir、非 Git workspace root 和 `scope.json` 规则。
- 导航规则改为 knowledge/archive 使用 `INDEX.md`、current memory 使用 `MEMORY.md`；补充 200 行/25KB 门禁。
- 字段与正文规则改为 knowledge `k-*`/300–400 字符、memory `m-*` + `type/modified_at`/40–800 字符；manifest 附加 id 改为 `memory:<id>`。
- 明确只有 knowledge 与 lesson 可记录独立复现，memory 是可审计上下文而非强制规则。

## 独立读回

- 固定字符串搜索 legacy `experience`、`K/E`、`knowledge/experience` 等旧契约词，退出码 1，零命中。
- 当前契约搜索命中五类 memory、`memory/global`、项目 `scope.json`、`MEMORY.md` 容量门禁和 40–800 字符规则。
- 文件可按严格 UTF-8 读取，无 BOM、无尾随空白、以换行结尾，共 118 行。
- `validate_entries.py check --root ... --json` 仍为 88 个条目、0 failure、2 个复现文件/3 条记录，证明 README 更新没有破坏认知数据。

## 边界

本轮只更新当前本机数据根 README 和仓库验收事实，没有修改 knowledge、memory、recurrence、legacy 数据，也没有发布 Skill 到市场或部署到其他 Agent 运行环境。
