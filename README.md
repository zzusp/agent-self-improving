# Agent Self-Improving Skills

[![skills.sh](https://skills.sh/b/zzusp/agent-self-improving)](https://skills.sh/zzusp/agent-self-improving)

一组面向本机知识与经验闭环的 Agent Skills。三个 Skill 分别负责整理资料、维护可复用认知和只读调用历史信息；知识数据默认保存在 `~/.agent-knowledge/`，与 Skill 代码分离。

## 包含的 Skills

| Skill | 用途 | 典型触发 |
| --- | --- | --- |
| `distill-self-improving` | 将用户明确指定的文件、目录或项目建立索引并逐份蒸馏 | “把这个项目加入知识库”“整理这批文档” |
| `evolve-self-improving` | 从纠正、能力期望、知识缺口和已收敛错误中维护长期知识与经验 | “记住这条规则”“把这次踩坑沉淀下来” |
| `use-self-improving` | 在工作可能受历史决定、稳定规则或相似经验影响时只读检索 | “之前为什么这么做？”“类似故障怎么处理？” |

## 安装

需要 Node.js 和 npm。以下命令使用 [skills CLI](https://skills.sh/docs/cli) 从 GitHub 安装。

全局安装三个 Skill，供 Codex 的所有项目使用：

```powershell
npx skills@latest add zzusp/agent-self-improving --skill '*' --agent codex --global --yes
```

只安装一个 Skill：

```powershell
npx skills@latest add zzusp/agent-self-improving --skill use-self-improving --agent codex --global --yes
```

如需安装到其他受支持的 Agent，将 `codex` 替换为对应 Agent 名称；也可以省略 `--agent`，由 CLI 交互选择。省略 `--global` 时安装到当前项目。

查看仓库中可安装的 Skill：

```powershell
npx skills@latest add zzusp/agent-self-improving --list
```

## 使用

安装后重新打开 Agent 会话，使 Skill 目录被重新发现。之后直接用自然语言提出任务即可，不必手动指定 Skill：

```text
把 D:\project\example 加入知识库，并整理其中的重要文档。
```

```text
刚才这个错误的根因已经确认，把可复用的处理方法沉淀下来。
```

```text
这个项目以前为什么选择这种部署方式？
```

需要明确指定时，也可以在支持显式调用的 Agent 中使用 `$distill-self-improving`、`$evolve-self-improving` 或 `$use-self-improving`。

三个 Skill 的协作关系是：

1. `distill-self-improving` 整理用户明确指定的原始资料，但不自动生成知识或经验条目。
2. `evolve-self-improving` 只保存已经验证、跨会话仍有价值且边界清楚的知识与经验。
3. `use-self-improving` 只读检索，并在结论易变时回到原文件或当前现场复核。

## 数据与安全边界

- 原始文件保持不变；蒸馏产物、知识和经验写入本机 `~/.agent-knowledge/`。
- 自动发现学习信号不等于自动保存；猜测、临时状态、原始报错和未定位事件不会入库。
- 查询 Skill 全程只读，不会新增、修改或删除知识库内容。
- 凭据、隐私、客户原文和长篇原文不应写入知识库。

## 更新与卸载

```powershell
npx skills@latest update --global
npx skills@latest remove distill-self-improving evolve-self-improving use-self-improving --global --yes
```

更多安装信息与收录状态见 [skills.sh/zzusp/agent-self-improving](https://skills.sh/zzusp/agent-self-improving)。
