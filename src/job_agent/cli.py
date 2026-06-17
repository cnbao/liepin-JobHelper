from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="求职历史库辅助工具")
console = Console()

WORKSPACE = Path("/workspace")
JOB_FILE = WORKSPACE / "job.md"


def iter_job_rows():
    if not JOB_FILE.exists():
        console.print(f"未找到文件：{JOB_FILE}", style="red")
        raise typer.Exit(code=1)

    content = JOB_FILE.read_text(encoding="utf-8")
    for line in content.splitlines():
        if not line.startswith("| "):
            continue
        if "Job ID" in line or "---:" in line:
            continue

        columns = [col.strip() for col in line.strip("|").split("|")]
        if len(columns) < 11:
            continue
        if not columns[0].isdigit():
            continue

        yield {
            "job_id": columns[0],
            "job_type": columns[1],
            "title": columns[2],
            "company": columns[3],
            "score": columns[4],
            "grade": columns[5],
            "choice": columns[6],
            "applied": columns[7],
            "apply_time": columns[8],
            "pdf_path": columns[9],
        }


@app.command()
def stats():
    """统计岗位库概况。"""
    rows = list(iter_job_rows())
    applied = sum(1 for row in rows if row["applied"] == "是")
    pending = sum(1 for row in rows if row["choice"] == "待定")
    paused = sum(1 for row in rows if row["choice"] in {"暂不投", "pass"})
    ab_unapplied = sum(
        1
        for row in rows
        if row["grade"].startswith(("A", "B"))
        and row["applied"] != "是"
        and row["choice"] not in {"暂不投", "pass"}
    )

    table = Table(title="岗位库统计")
    table.add_column("指标")
    table.add_column("数量", justify="right")
    table.add_row("岗位记录数", str(len(rows)))
    table.add_row("已投递", str(applied))
    table.add_row("待定", str(pending))
    table.add_row("暂不投/pass", str(paused))
    table.add_row("A/B 未投候选", str(ab_unapplied))
    console.print(table)


@app.command()
def candidates():
    """列出 A/B 且未投递、未暂不投/pass 的候选。"""
    table = Table(title="A/B 未投候选")
    table.add_column("Job ID")
    table.add_column("岗位")
    table.add_column("公司")
    table.add_column("评分")
    table.add_column("等级")
    table.add_column("状态")

    count = 0
    for row in iter_job_rows():
        if not row["grade"].startswith(("A", "B")):
            continue
        if row["applied"] == "是":
            continue
        if row["choice"] in {"暂不投", "pass"}:
            continue
        count += 1
        table.add_row(row["job_id"], row["title"], row["company"], row["score"], row["grade"], row["choice"])

    console.print(table if count else "暂无 A/B 未投候选。")


@app.command()
def paused():
    """列出暂不投/pass 且未投递岗位。"""
    table = Table(title="暂不投/pass 未投岗位")
    table.add_column("Job ID")
    table.add_column("岗位")
    table.add_column("公司")
    table.add_column("评分")
    table.add_column("等级")
    table.add_column("状态")

    count = 0
    for row in iter_job_rows():
        if row["applied"] == "是":
            continue
        if row["choice"] not in {"暂不投", "pass"}:
            continue
        count += 1
        table.add_row(row["job_id"], row["title"], row["company"], row["score"], row["grade"], row["choice"])

    console.print(table if count else "暂无暂不投/pass 未投岗位。")


if __name__ == "__main__":
    app()
