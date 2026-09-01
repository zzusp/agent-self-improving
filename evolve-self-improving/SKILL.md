---
name: evolve-self-improving
description: 在当前对话中自动发现值得跨会话保留的 user、feedback、project、reference、lesson 五类记忆，以及需要严格证据摘要的稳定知识；用户无需先说“记住”。适用于用户偏好与角色、明确纠正和确认做法、无法从代码或 git 恢复的项目决定、外部权威入口，以及由错误、知识缺口和运行证据收敛出的可复用方法、失败模式与护栏。自动发现只启动评估：未来确实有用、来源可回查、边界清楚且无法从代码或固定指令直接推导才保存；普通任务完成、临时诉求、猜测、原始报错和未收敛事件不写。
---

# 维护本机知识与记忆

## When to use

- **user**：用户角色、专业背景、稳定工作偏好，或用户明确要求以后沿用的交互方式。
- **feedback**：用户对 Agent 的明确纠正，或用户明确确认有效、以后仍应复用的做法。
- **project**：进行中的决定、承诺、外部依赖和上下文，且无法从当前代码或 git 历史直接恢复。
- **reference**：权威文档、问题跟踪器、仪表盘或远程系统等项目外信息的定位入口与核验方式。
- **lesson**：correction、feature-request、knowledge-gap 或 error 经独立证据闭环后形成的可复用方法、诊断路径、失败模式与护栏；原始报错和未定位事件不写。
- 稳定事实、定义、职责和约束需要完整证据摘要时归 knowledge。
- 用户主动话术：“记住这条规则”“以后都这样做”“把这次纠正记下来”“把已确认根因和方法沉淀下来”“归档这条记忆”“忘掉我指定的记录”。
- 不触发保存：普通任务完成、代码或 git 可直接推导的信息、固定项目指令已有内容、一次性要求、猜测、原始错误、未定位事件和长篇会话摘要。没有稳定内容时不写。

## Workflow

1. **准备并确定作用域。** 数据根使用 `~/.agent-knowledge/`。确保 `knowledge/{current,archive}`、`memory/global/{current,archive}`、`memory/projects/`、导航文件和 `maintenance.md` 存在；数据根已存在但缺新目录时补缺项，不覆盖已有内容。若发现 legacy `experience/`，先运行 `scripts/migrate_experience.py --root <根> --check [--scope-map <json>]`；check 零副作用，存在 blocker 或未获明确迁移授权时不执行 `--apply`，也不绕过旧数据继续写。
2. **解析项目桶。** 全局用户偏好或明确跨项目反馈写入 `memory/global/current/`，scope 必须为 `global`。Git 项目读取 `git rev-parse --path-format=absolute --git-common-dir` 和仓库根，以规范化 common dir 作为 identity，同一仓库所有 worktree 共用；非 Git 项目必须使用已明确的工作区绝对根目录，以规范化根路径作为 identity，不从当前任意子目录猜根。查找或创建 `memory/projects/<slug>-<identity-sha256前12位>/scope.json`，其中保存 `project_key/git_common_dir/roots`；非 Git 工作区的 `git_common_dir` 为 null。已有桶缺已确认根别名时只追加 roots。项目条目的 scope 以 `repo:<project-key>` 开头。无法确定唯一项目时不猜，最多问一个自然问题。
3. **判断是否值得记。** 条目必须同时满足：有原文件、命令回读、运行现场或明确确认支持；跨会话仍会影响判断或行动；无法直接从代码、git 或固定项目指令恢复；scope 与失败边界清楚；已脱敏。易变现值只记权威入口、核验方法和已知时点。条件不全时说明未沉淀原因，不为每次会话硬造记忆。
4. **去重、冲突和纠正。** 先读 global 与当前项目的 `MEMORY.md`、再读 `knowledge/current/INDEX.md`，用 title、type、scope、tags 和特异概括缩小候选；命中后才打开正文，纠错追溯才读 archive。等价记忆不新增，只追加独立 source、修正文与 `modified_at`。明确证伪时先写带 `supersedes` 的新条目并读回，再归档旧条目。knowledge 与 lesson 可在 `recurrence/<entry-id>.md` 记录后来独立发生的复现；其他记忆不统计复现次数。
5. **原子写入并读回。** knowledge 使用 `k-` id，必填 `id/title/scope/tags/learned_at/source`，正文有效字符 300–400。memory 使用 `m-` id，另有必填 `type/modified_at`，正文有效字符 40–800；`modified_at` 使用 UTC `YYYY-MM-DDTHH:MM:SSZ`：

   ```markdown
   ---
   id: m-YYYYMMDD-HHmmss-short-slug
   title: 简短标题
   scope: repo:example-a1b2c3d4e5f6
   tags: [diagnosis, oauth]
   learned_at: YYYY-MM-DD
   source: conversation:<opaque-ref>
   type: lesson
   modified_at: YYYY-MM-DDTHH:MM:SSZ
   ---
   正文写清记忆内容、使用场景、不适用边界和必要的复核方式。
   ```

   写入同目录临时文件，运行 `scripts/validate_entries.py check --file <条目>` 后原子替换。再用 `render-index --directory <current或archive目录>` 生成完整导航临时文本：current memory 写 `MEMORY.md`，archive 与 knowledge 写 `INDEX.md`。`MEMORY.md` 不得超过 200 行或 25KB，超限时合并或归档低价值内容，不截断、不丢条目。最后运行 `check --root ~/.agent-knowledge/` 并逐项读回；失败则恢复本项写前状态，不把部分成功说成完成。
6. **自然维护并报告。** 每次调用读取 `maintenance.md`；距 `last_reviewed_at` 满 7 天才检查 current 的来源、重复、冲突、过时风险、可从代码推导的冗余和敏感泄漏。删除只在用户明确指定条目或范围时执行，先验证目标在拥有目录内且不是链接。报告实际新增、修正、归档、迁移或未保存内容及原因。

## Tools and data sources

- 只读原文件、代码、git 历史、配置、命令回读和运行现场；正常写入仅限 `knowledge/`、`memory/`、knowledge/lesson 使用的 `recurrence/`、根最小 README 与 `maintenance.md`。
- 校验器只读；迁移工具是唯一可移动 legacy `experience/` 的脚本，必须先 `--check`，`--apply` 成功后把原目录与旧复现文件保存在 `legacy/experience-<UTC时间>/`，可回查恢复。
- `source` 可为非空列表；新确认只能追加。记忆是上下文而非强制规则；需要强制执行的行为应进入项目指令、Skill、hook 或权限配置。

## Gotchas

- `current` 只表示允许召回，不表示无需复核；`archive` 默认不检索。不要增加 candidate、confidence、访问次数或普通使用次数。
- 不要保存代码结构、依赖列表、文件路径清单或已提交修复的可推导细节；但无法从代码恢复的诊断条件、取舍和失败护栏可作为 lesson。
- 项目记忆不得写入 global 桶；同一 git common dir 或同一非 Git 工作区根必须复用同一 project key。仓库或工作区整体移动会改变本方案的本机 identity，须显式迁移项目桶，不自动猜测或只改 roots。
- 小修可原位更新；实质纠正必须保住完整新旧内容后再归档。模糊的“忘记”不能扩大成广泛删除。
- 一项失败不回滚其他已验证项；不确定时宁可不写，也不伪造 source 或强行消解冲突。
