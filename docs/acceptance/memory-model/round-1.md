# Round 1

## 目标

验证 memory 模型是旧 experience 的能力超集、不同仓库物理隔离、worktree 共享 identity、索引可召回且有容量边界，并证明迁移工具在写入前完整预检、失败可恢复。

## 自动化验证

执行：

```powershell
python -B -m unittest discover -s evolve-self-improving\tests -v
```

结果：13 个测试全部通过。覆盖五类 memory、错误 type/scope、tags 索引、行数和字节门禁、项目桶发现、lesson 复现、global/project 两类迁移、worktree identity、staging 清理、安装后失败回滚，以及 CLI `render-index`/`check --root`。

执行：

```powershell
python -B -c "import ast,pathlib; ..."
git diff --cached --check
```

结果：3 个 Python 文件均可由 `ast.parse` 解析；暂存 diff 无空白错误。

## 当前本机数据只读预检

执行 `migrate_experience.py --check`，未提供 scope map。观察结果：

- `status=blocked`、退出码 1；
- 扫描 59 条旧 experience 和 1 个旧复现文件；
- 将重复项合并为 22 个唯一 scope 映射 blocker；
- `~/.agent-knowledge/` 根目录清单执行前后完全一致；
- 没有创建 `memory/`、`legacy/` 或临时迁移目录。

随后执行新校验器检查真实数据根，按预期拒绝 legacy `experience/`、缺失的新 memory 目录和尚未迁移的 `e-*` recurrence。该失败是迁移门禁证据，不是功能通过声明。

## 边界

没有对当前本机 59 条旧数据执行 `--apply`，因为 22 个旧 scope 尚未获得“scope → 仓库绝对路径”的用户确认映射。本轮只证明 fixture 上的迁移、备份和回滚闭环，以及真实数据预检零写入。
