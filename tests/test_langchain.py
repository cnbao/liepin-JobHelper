"""测试 LangChain 集成模块（不依赖真实 LLM 调用）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

# 测试 LLMNotAvailableError
from job_agent.langchain import LLMNotAvailableError, _get_llm

print("=" * 60)
print("测试 LLM 不可用异常")
print("=" * 60)

# 确保没有 API key
if "OPENAI_API_KEY" in os.environ:
    del os.environ["OPENAI_API_KEY"]

try:
    _get_llm()
    print("[FAIL] 应抛出 LLMNotAvailableError")
except LLMNotAvailableError as e:
    print(f"[PASS] LLMNotAvailableError: {e}")

print()
print("=" * 60)
print("测试 recommendation 模块")
print("=" * 60)

from job_agent.langchain.recommendation import _format_job_for_prompt, _format_preferences_for_prompt

# 测试格式化函数
job = {
    "title": "解决方案架构师",
    "company": "阿里云",
    "location": "西安",
    "salary_text": "28-55k·16薪",
    "education": "本科",
    "experience": "10年以上",
    "industry": "IT服务",
    "company_stage": "已上市",
    "company_size": "10000人以上",
    "tags": "五险一金、年终奖金",
    "description": "负责公共云解决方案架构设计，客户需求分析...",
}
formatted = _format_job_for_prompt(job)
assert "解决方案架构师" in formatted
assert "阿里云" in formatted
assert "28-55k·16薪" in formatted
print("[PASS] _format_job_for_prompt 格式化正确")

# 测试偏好格式化
prefs = {
    "target_roles": ["解决方案经理", "售前支持"],
    "salary_min": 18000,
    "salary_max": 24000,
    "preferred_cities": ["西安"],
}
formatted_prefs = _format_preferences_for_prompt(prefs)
assert "目标职位" in formatted_prefs
assert "西安" in formatted_prefs
print("[PASS] _format_preferences_for_prompt 格式化正确")

# 测试空偏好
empty_prefs = _format_preferences_for_prompt({})
assert empty_prefs == "无特殊偏好"
print("[PASS] 空偏好处理正确")

# 测试 generate_recommendation 无 API key
from job_agent.langchain.recommendation import generate_recommendation
try:
    generate_recommendation(job)
    print("[FAIL] 应抛出 LLMNotAvailableError")
except LLMNotAvailableError:
    print("[PASS] generate_recommendation 无 API key 抛出异常")

print()
print("=" * 60)
print("测试 matching 模块")
print("=" * 60)

from job_agent.langchain.matching import _format_resume_for_prompt

# 测试简历格式化
resume = {
    "name": "张三",
    "title": "解决方案经理",
    "years_experience": 10,
    "skills": ["云计算", "解决方案设计", "客户沟通"],
    "experience": [
        {"company": "华为云", "role": "解决方案经理", "description": "负责企业数字化转型咨询..."},
    ],
    "education": [
        {"school": "西安电子科技大学", "degree": "本科", "major": "计算机科学与技术"},
    ],
    "projects": [
        {"name": "企业数字化诊断项目", "description": "完成79家企业诊断..."},
    ],
}
formatted_resume = _format_resume_for_prompt(resume)
assert "张三" in formatted_resume
assert "华为云" in formatted_resume
assert "西安电子科技大学" in formatted_resume
print("[PASS] _format_resume_for_prompt 格式化正确")

# 测试空简历
empty_resume = _format_resume_for_prompt({})
assert empty_resume == "无简历信息"
print("[PASS] 空简历处理正确")

# 测试 analyze_match 无 API key
from job_agent.langchain.matching import analyze_match
try:
    analyze_match(resume, job)
    print("[FAIL] 应抛出 LLMNotAvailableError")
except LLMNotAvailableError:
    print("[PASS] analyze_match 无 API key 抛出异常")

print()
print("=" * 60)
print("全部测试通过!")
print("=" * 60)
