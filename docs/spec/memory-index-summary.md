# Memory 索引摘要

## 问题

当前 `MEMORY.md` 通过 `first_summary(body)[:88]` 从正文首段截取文本。它既没有生成真正的召回摘要，也会把适用条件截成半句。索引还重复输出 id、type、modified_at、tags、title 和复现信息，使本机 63 条 current memory 的索引达到 27733 bytes。

## 目标

- 每条 memory 由 Agent 在写入时提供一条语义摘要，回答“什么情况下应打开这条记忆”。
- 渲染器原样使用摘要，不从正文抽取，也不静默截断。
- `MEMORY.md` 只保留路由所需信息，并同时限制行数与字节数。

## 契约

memory frontmatter 新增必填 `summary`：单行、20–120 个 Unicode 字符。摘要由 Agent 根据完整记忆概括；缺失、过短或过长均校验失败，由 Agent 改写。

`MEMORY.md` 每条固定为：

```markdown
- [title](./m-*.md) | scope | summary
```

只保留：

- `title` 与主题文件链接：定位正文；
- `scope`：召回前的业务范围过滤；
- `summary`：判断是否需要打开正文。

id 已包含在链接目标中；type、tags、modified_at、source 与 recurrence 留在主题文件或证据文件中，命中后读取。`modified_at` 仍用于索引排序，但不显示。

`MEMORY.md` 必须同时不超过 200 行和 25000 bytes。超过任一门禁都失败，要求合并或归档低价值记忆；不得裁剪单条摘要或丢弃尾部条目。

## 迁移

- 已有 memory 必须由 Agent 逐条阅读后补写 `summary`，不能从正文首句机械复制。
- legacy experience 只有在已经补齐语义 `summary` 后才能迁移；迁移器只原样保留该字段，不负责生成摘要。
- 更新主题文件后重新渲染 `MEMORY.md`，再执行完整数据根校验。

## 验证

- 缺失、多行、少于 20 字或超过 120 字的 summary 被拒绝。
- 索引逐字包含 summary，正文再长也不会影响索引摘要。
- current 索引不再输出显示 id、type、tags、modified_at 或 recurrence。
- 200 行与 25000 bytes 两项门禁分别有失败用例。
- 本机全部 current memory 补齐 summary 后，完整数据根校验通过且索引低于 25000 bytes。
