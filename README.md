# Liepin JobHelper

一个面向个人求职场景的 **Human-in-the-loop 求职分析与投递 Agent 模板**。

它使用主提示词定义 Agent 角色、流程和安全边界，使用 `preferences.md` 作为动态规则源，并通过分层 Markdown 文件管理岗位状态、评估详情、搜索归档和投递日志。当前示例基于 Trae IDE + 猎聘 MCP 使用，但提示词、规则文件和数据结构可迁移到其他支持 MCP / Tool Calling 的 Agent 环境。

> 本项目不是自动海投机器人。所有投递和在线简历修改都必须经过用户最终确认。

## 核心能力

- 岗位搜索：按动态偏好读取规则并调用招聘平台 MCP 搜索
- 岗位评分：按 `preferences.md` 中的评分模型、权重和等级规则评估
- 岗位记录分层：主索引、详情、搜索归档、投递日志分离
- `/投递` 工作流：筛选候选、确认简历策略、最终确认后投递
- `/捞回` 工作流：复盘暂不投/pass/遗漏候选，按新偏好重新判断
- 偏好学习：根据“投 / 暂不投 / pass”持续更新动态规则
- 安全边界：禁止自动投递、禁止伪造投递状态、禁止未经确认修改简历

## 项目结构

```text
liepin-JobHelper/
├─ README.md
├─ .env.example
├─ .gitignore
├─ prompts/
│  └─ main-agent-prompt.md
├─ templates/
│  ├─ preferences.template.md
│  ├─ job.template.md
│  ├─ job_detail.template.md
│  ├─ job_search_archive.template.md
│  └─ job_apply_log.template.md
├─ examples/
│  ├─ preferences.example.md
│  ├─ job.example.md
│  ├─ job_detail.example.md
│  ├─ job_search_archive.example.md
│  └─ job_apply_log.example.md
├─ docs/
│  ├─ setup.md
│  ├─ workflow.md
│  └─ safety.md
└─ src/
   └─ job_agent/
      └─ cli.py
```

## 快速开始

### 1. 克隆项目

```bash
git clone git@github.com:cnbao/liepin-JobHelper.git
cd liepin-JobHelper
```

### 2. 复制模板文件

PowerShell：

```powershell
Copy-Item templates/preferences.template.md preferences.md
Copy-Item templates/job.template.md job.md
Copy-Item templates/job_detail.template.md job_detail.md
Copy-Item templates/job_search_archive.template.md job_search_archive.md
Copy-Item templates/job_apply_log.template.md job_apply_log.md
Copy-Item .env.example .env
```

### 3. 配置猎聘 MCP

打开猎聘 MCP 配置页：

```text
https://www.liepin.com/mcp/server#config
```

将 MCP server 信息配置到你的 Agent IDE / MCP 客户端中。

### 4. 配置主提示词

复制 [prompts/main-agent-prompt.md](./prompts/main-agent-prompt.md) 到你的 Agent 的 System Prompt / Agent Prompt 中。

### 5. 开始使用

常用指令：

```text
开始搜索
/投递
/捞回
```

## Docker CLI 示例

本项目包含一个最小 Python CLI 示例，用于读取 `job.md` 并输出统计信息。

```powershell
docker compose run --rm job-agent
```

或：

```powershell
docker compose run --rm job-agent python -m job_agent.cli stats
docker compose run --rm job-agent python -m job_agent.cli candidates
docker compose run --rm job-agent python -m job_agent.cli paused
```

## 核心文件说明

| 文件 | 作用 |
|---|---|
| `preferences.md` | 动态规则源，保存目标职位、偏好、评分模型、搜索规则、投递规则和偏好学习规则 |
| `job.md` | 岗位最新状态主索引，不作为全文数据库 |
| `job_detail.md` | 岗位详细评估、A-G 模块、面试准备和风险核查 |
| `job_search_archive.md` | 原始搜索结果、搜索批次和去重记录 |
| `job_apply_log.md` | 投递记录、投递结果、打招呼语和 PDF 路径 |

## 安全边界

- 未经用户最终确认，不得调用投递 MCP
- 不得投递已 pass、暂不投或已投递岗位
- 不得伪造已投递状态
- 不得伪造 PDF 已发送状态
- 不得未经确认修改招聘平台在线简历
- 修改在线简历前必须展示修改内容并获得确认
- 如果 MCP/招聘平台不支持指定 PDF 附件投递，不得假装已发送 PDF

更多说明见 [docs/safety.md](./docs/safety.md)。


## License

MIT
