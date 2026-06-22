"""猎聘 MCP HTTP 客户端封装。

基于 MCP HTTP 传输协议，通过 JSON-RPC 2.0 调用猎聘 MCP 工具。
配置从环境变量读取，支持上下文管理器。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests


class McpConnectionError(Exception):
    """MCP 连接异常"""


class McpTimeoutError(Exception):
    """MCP 请求超时"""


class McpResponseError(Exception):
    """MCP 返回错误"""


# 默认配置
DEFAULT_MCP_URL = "https://open-agent.liepin.com/mcp/user"
DEFAULT_TIMEOUT = 60


def _get_config() -> tuple[str, str, int]:
    """从环境变量获取 MCP 配置。

    Returns:
        (url, token, timeout)
    """
    url = os.environ.get("MCP_URL", DEFAULT_MCP_URL)
    token = os.environ.get(
        "MCP_TOKEN",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI0NDIwOTc4OSIsInVzZXJJZCI6NDQyMDk3ODksImlhdCI6MTc4MjEwNDk3MiwiZXhwIjoxNzg5ODgwOTcyfQ._SmTn3qfDn1lMFt34R5bEn_P118V3swjmenY3gEZAvA",
    )
    timeout = int(os.environ.get("MCP_TIMEOUT", str(DEFAULT_TIMEOUT)))
    return url, token, timeout


class LiepinMCPClient:
    """猎聘 MCP HTTP 客户端。

    基于 MCP HTTP 传输协议，通过 JSON-RPC 2.0 调用猎聘 MCP 工具。
    支持上下文管理器，自动管理会话。

    用法:
        client = LiepinMCPClient()
        jobs = client.search_jobs(jobName="AI 产品经理", address="上海")
        client.close()

    或:
        with LiepinMCPClient() as client:
            jobs = client.search_jobs(jobName="AI 产品经理", address="上海")
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        url, token, timeout = url or _get_config()[0], token or _get_config()[1], timeout or _get_config()[2]
        self._url = url
        self._token = token
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "x-user-token": self._token,
            }
        )
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """调用 MCP 工具。

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果

        Raises:
            McpConnectionError: 连接异常
            McpTimeoutError: 请求超时
            McpResponseError: 返回错误
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
        }

        try:
            resp = self._session.post(self._url, json=payload, timeout=self._timeout)
        except requests.ConnectionError as e:
            raise McpConnectionError(f"无法连接到 MCP 服务器 {self._url}: {e}")
        except requests.Timeout as e:
            raise McpTimeoutError(f"MCP 请求超时 ({self._timeout}s): {e}")
        except requests.RequestException as e:
            raise McpConnectionError(f"MCP 请求失败: {e}")

        if resp.status_code != 200:
            raise McpResponseError(f"MCP 返回 HTTP {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            raise McpResponseError(f"MCP 返回非 JSON 响应: {e}")

        if "error" in data and data["error"] is not None:
            err = data["error"]
            raise McpResponseError(f"MCP 返回错误: [{err.get('code')}] {err.get('message')}")

        result = data.get("result")
        if result is None:
            return None

        # MCP tools/call 返回的 result 中可能包含 content 数组
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if content and isinstance(content, list):
                # 尝试解析第一个 text 类型的内容
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        try:
                            return json.loads(text)
                        except (json.JSONDecodeError, TypeError):
                            return text
            return content

        return result

    # ── 核心工具方法 ──────────────────────────────────────────

    def search_jobs(
        self,
        jobName: Optional[str] = None,
        address: Optional[str] = None,
        salaryFloor: Optional[str] = None,
        salaryCap: Optional[str] = None,
        salaryKind: Optional[str] = None,
        workExperience: Optional[str] = None,
        eduLevel: Optional[str] = None,
        compNature: Optional[str] = None,
        companyName: Optional[str] = None,
        page: Optional[int] = None,
    ) -> list:
        """搜索职位。

        Args:
            jobName: 职位名称关键词
            address: 工作地点
            salaryFloor: 薪资下限
            salaryCap: 薪资上限
            salaryKind: 薪资类型（"月薪"或"年薪"）
            workExperience: 工作经验要求
            eduLevel: 学历要求
            compNature: 公司性质（如：国企、外企、民营）
            companyName: 公司名称
            page: 分页页码（0 表示第 1 页）

        Returns:
            职位列表
        """
        params = {}
        if jobName is not None:
            params["jobName"] = jobName
        if address is not None:
            params["address"] = address
        if salaryFloor is not None:
            params["salaryFloor"] = salaryFloor
        if salaryCap is not None:
            params["salaryCap"] = salaryCap
        if salaryKind is not None:
            params["salaryKind"] = salaryKind
        if workExperience is not None:
            params["workExperience"] = workExperience
        if eduLevel is not None:
            params["eduLevel"] = eduLevel
        if compNature is not None:
            params["compNature"] = compNature
        if companyName is not None:
            params["companyName"] = companyName
        if page is not None:
            params["page"] = page

        return self._call_tool("user-search-job", params)

    def apply_job(self, jobId: int, jobKind: str) -> dict:
        """投递职位。

        Args:
            jobId: 职位 ID
            jobKind: 职位类型

        Returns:
            投递结果
        """
        return self._call_tool("user-apply-job", {"jobId": jobId, "jobKind": jobKind})

    def get_my_resume(self) -> dict:
        """获取我的简历。

        Returns:
            简历原始内容
        """
        return self._call_tool("my-resume")

    def modify_resume_base_info(self, **kwargs) -> dict:
        """修改简历基本信息。

        Args:
            **kwargs: 基本信息字段，支持：
                realName: 真实姓名
                sex: 性别（男/女）
                birthday: 生日（yyyyMMdd）
                cityCode: 当前城市名称
                startJob: 开始工作年份
                startJobMonth: 开始工作月份
                nowWorkStatus: 当前工作状态
                nowSalary: 当前月薪（元）
                nowMonths: 当前月薪月数
                nowSalarySecret: 薪资是否保密（0-显示，1-隐藏）
                jobName: 当前职位名称
                nowComp: 当前公司名称
                nowIndusCode: 当前行业名称
                nowJobTitleCode: 当前职能名称
                nameSecret: 姓名隐私配置
                wechat: 微信号
                politicalStatusCode: 政治面貌

        Returns:
            修改结果
        """
        return self._call_tool("modify-resume-base-info", kwargs)

    def add_work_exp(self, **kwargs) -> dict:
        """添加工作经历。

        Args:
            **kwargs: 工作经历字段，支持：
                compName: 公司名称
                industry: 所属行业名称
                workStart: 在职开始时间（YYYYMM）
                workEnd: 在职结束时间（YYYYMM）
                rwTitle: 职位名称
                jobtitle: 职位类别/职能名称
                dq: 工作地点名称
                dept: 所属部门
                report: 汇报对象职位
                subordinate: 下属人数
                duty: 职责业绩
                months: 薪资月数
                salary: 薪资（元）
                compkind: 公司性质编码
                compscale: 公司规模编码
                shieldComp: 是否对该公司屏蔽简历
                labels: 技能标签（英文逗号分隔）
                workType: 工作经历类型（1-全职，2-实习）

        Returns:
            添加结果
        """
        return self._call_tool("add-work-exp", kwargs)

    def modify_work_exp(self, workId: int, **kwargs) -> dict:
        """修改工作经历。

        Args:
            workId: 工作经历 ID（必填）
            **kwargs: 其他工作经历字段

        Returns:
            修改结果
        """
        return self._call_tool("modify-work-exp", {"workId": workId, **kwargs})

    def add_project_exp(self, name: str, start: str, end: str, **kwargs) -> dict:
        """添加项目经历。

        Args:
            name: 项目名称（必填）
            start: 项目开始时间（YYYYMM，必填）
            end: 项目结束时间（YYYYMM，必填）
            **kwargs: 其他项目经历字段：
                compName: 公司名称
                position: 担任职务
                descr: 项目描述
                duty: 项目职责
                achievement: 项目业绩

        Returns:
            添加结果
        """
        return self._call_tool("add-project-exp", {"name": name, "start": start, "end": end, **kwargs})

    def modify_project_exp(self, id: int, **kwargs) -> dict:
        """修改项目经历。

        Args:
            id: 项目经历 ID（必填）
            **kwargs: 其他项目经历字段

        Returns:
            修改结果
        """
        return self._call_tool("modify-project-exp", {"id": id, **kwargs})

    def add_edu_exp(self, school: str, degree: str, start: str, end: str, **kwargs) -> dict:
        """添加教育经历。

        Args:
            school: 学校名称（必填）
            degree: 学历（必填，如 040-本科）
            start: 开始时间（YYYYMM，必填）
            end: 结束时间（YYYYMM，必填）
            **kwargs: 其他教育经历字段：
                major: 专业名称
                tz: 统招标志（0-否，1-是）
                experience: 在校经历

        Returns:
            添加结果
        """
        return self._call_tool("add-edu-exp", {"school": school, "degree": degree, "start": start, "end": end, **kwargs})

    def modify_edu_exp(self, eduId: int, **kwargs) -> dict:
        """修改教育经历。

        Args:
            eduId: 教育经历 ID（必填）
            **kwargs: 其他教育经历字段

        Returns:
            修改结果
        """
        return self._call_tool("modify-edu-exp", {"eduId": eduId, **kwargs})

    def add_job_want(self, jobtitle: str, dq: str, **kwargs) -> dict:
        """添加求职期望。

        Args:
            jobtitle: 职能/职位类别名称（必填）
            dq: 期望地点名称（必填）
            **kwargs: 其他求职期望字段：
                industries: 行业名称列表
                wantSalaryLow: 期望薪资下限（元）
                wantSalaryHigh: 期望薪资上限（元）
                wantSalaryMonths: 期望薪资月数
                workType: 工作类型
                otherExpectDqs: 其他期望地点列表
                workweek: 每周工作天数
                practiceMonths: 实习月数

        Returns:
            添加结果
        """
        return self._call_tool("add-job-want", {"jobtitle": jobtitle, "dq": dq, **kwargs})

    def modify_job_want(self, id: int, **kwargs) -> dict:
        """修改求职期望。

        Args:
            id: 求职期望 ID（必填）
            **kwargs: 其他求职期望字段

        Returns:
            修改结果
        """
        return self._call_tool("modify-job-want", {"id": id, **kwargs})

    def modify_self_assess(self, selfAssess: str) -> dict:
        """修改自我评价。

        Args:
            selfAssess: 自我评价内容

        Returns:
            修改结果
        """
        return self._call_tool("modify-self-assess", {"selfAssess": selfAssess})

    def close(self) -> None:
        """关闭会话，释放连接。"""
        self._session.close()

    def __enter__(self) -> LiepinMCPClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
