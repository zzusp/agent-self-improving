# Round 4：统一 memory 目录

## 目标

验证取消整个项目桶设计，而非只删除 Git/非 Git 分支：memory 仅保留 current/archive，scope 只作标签；legacy 迁移不再要求 scope map；本机旧项目桶安全合并且正文不丢失。

## 源码验证

执行：

```powershell
python -B -m unittest discover -s evolve-self-improving/tests -p "test_*.py" -v
python -B -c "import ast, pathlib; files=[pathlib.Path('evolve-self-improving/scripts/validate_entries.py'), pathlib.Path('evolve-self-improving/scripts/migrate_experience.py'), pathlib.Path('evolve-self-improving/tests/test_validate_entries.py')]; [ast.parse(path.read_text(encoding='utf-8'), filename=str(path)) for path in files]; print('AST PASS', len(files))"
```

结果：14 个 unittest 全部通过，3 个 Python 文件 AST 解析通过。覆盖统一目录发现、五类 memory、任意非空 scope、旧项目布局拒绝、仅 200 行索引门禁、非 global legacy scope 无映射迁移、零副作用检查和失败回滚。

## 本机迁移

先执行：

```powershell
./docs/acceptance/memory-model/scripts/flatten-memory.ps1 `
  -Root "$env:USERPROFILE\.agent-knowledge" `
  -Validator "$PWD\evolve-self-improving\scripts\validate_entries.py" `
  -Check
```

结果：59 条源 memory、0 重复 id、3 个旧 scope 文件、0 blocker；检查未写入。

再以相同参数执行 `-Apply`。结果：统一目录安装完成，完整数据根为 88 条认知、0 failure；`memory/current` 59 条、`memory/archive` 0 条。旧目录备份到 `legacy/memory-project-buckets-20260901T060812Z`。

## 独立回读

- `validate_entries.py check --root ... --json` 独立返回 `pass`、88 entries、0 failures、2 个 recurrence 文件和 3 条复现。
- 旧备份与新目录逐文件比较：59 对 59；只允许删除 `repo:<project-key>/` scope 路由前缀，0 content mismatch。
- 新 `memory/` 的直接子项只有 `current,archive`，`scope: repo:` 命中 0，临时 staging 残留 0。
- 统一 `MEMORY.md` 为 63 行、25696 bytes；超过旧 25KB 边界但低于 200 行，验证取消 byte 门禁后无需为了索引体积重新引入项目拆分。
- 本地数据根 README 已改为统一目录契约，不再声明 `scope.json`、project key 或 Git/非 Git 项目路由。
