# Setup

## 1. 配置 Agent 主提示词

复制 `prompts/main-agent-prompt.md` 到支持 System Prompt / Agent Prompt 的 Agent IDE 中。

## 2. 创建本地数据文件

从模板复制：

```powershell
Copy-Item templates/preferences.template.md preferences.md
Copy-Item templates/job.template.md job.md
Copy-Item templates/job_detail.template.md job_detail.md
Copy-Item templates/job_search_archive.template.md job_search_archive.md
Copy-Item templates/job_apply_log.template.md job_apply_log.md
```

## 3. 配置猎聘 MCP

访问：

```text
https://www.liepin.com/mcp/server#config
```

将 MCP server 信息配置到你的 Agent IDE / MCP 客户端。

## 4. 配置 LLM API

复制 `.env.example` 为 `.env`，填写自己的 API Key。

不要提交 `.env`。
