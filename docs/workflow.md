# Workflow

## 搜索岗位

```text
开始搜索
```

流程：读取 `preferences.md` → 搜索岗位 → 去重 → 初评 → 写入 `job_search_archive.md`、`job.md`、`job_detail.md`。

## /投递

```text
/投递
```

流程：读取 `preferences.md` 和 `job.md` → 筛选未投递 A/B 候选 → 展示候选 → 用户选择 → 简历策略 → 最终确认 → 调用 MCP → 写入投递日志。

## /捞回

```text
/捞回
```

流程：读取规则和主索引 → 找暂不投/pass/遗漏推荐岗位 → 按新偏好复盘 → 给出建议动作 → 用户确认后恢复候选。

## 偏好学习

当用户选择“投 / 暂不投 / pass”时，Agent 更新岗位状态，并把反馈写入 `preferences.md`。
