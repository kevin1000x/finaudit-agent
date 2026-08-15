"""执行冻结。**先跑前置门禁，校验不过就拒绝冻结**（EVAL_CASES §2.1）。

为什么冻结要由脚本做而不是人手工打哈希：
POC-01 的 `revenue_growth_yoy.yaml` 冻结于 2026-08-10，
2026-08-15 才被发现它根本不是合法 YAML——能解析它的校验器那天才存在。
冻结是不可逆的，所以「能不能被机器读懂」必须在**跨过那道门之前**验证完。

用法：
    python -m eval.freeze --suite frozen-01 --check     # 只跑门禁，不冻结
    python -m eval.freeze --suite frozen-01             # 门禁通过则冻结
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

REQUIRED_KEYS = ["id", "category", "question", "expected", "required_evidence", "judging"]


def _registry():
    from semantic_layer.resolve import Registry

    return Registry.load(REPO_ROOT / "metrics")


def pregate(suite_dir: Path) -> list[str]:
    """EVAL_CASES §2.1 前置门禁。返回问题清单，空列表表示通过。"""
    from semantic_layer.resolve import Refusal

    problems: list[str] = []
    case_dir = suite_dir / "cases"
    paths = sorted(case_dir.glob("*.yaml"))
    if not paths:
        return [f"没有找到任何题面：{case_dir}"]

    registry = _registry()
    seen_ids: dict[str, str] = {}

    for path in paths:
        # 1. 是合法 YAML —— 这一条正是 POC-01 的教训
        try:
            case = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{path.name}：不是合法 YAML：{exc}")
            continue
        if not isinstance(case, dict):
            problems.append(f"{path.name}：顶层不是映射")
            continue

        # 2. 必填字段齐全
        for key in REQUIRED_KEYS:
            if key not in case:
                problems.append(f"{path.name}：缺必填字段 {key}")

        cid = case.get("id")
        cat = case.get("category")
        if not cid:
            continue

        # 3. id 无重复
        if cid in seen_ids:
            problems.append(f"{path.name}：id {cid!r} 与 {seen_ids[cid]} 重复")
        seen_ids[cid] = path.name

        expected = case.get("expected") or {}

        # 4a. C2 的靶子必须**真的**不存在 —— 靶子是软柿子就等于没考
        if cat == "C2":
            target = expected.get("target_name")
            if not target:
                problems.append(f"{path.name}：C2 题未声明 expected.target_name")
            else:
                outcome = registry.resolve(target)
                if not isinstance(outcome, Refusal):
                    problems.append(
                        f"{path.name}：C2 靶子 {target!r} 在语义层中**存在**，不构成拒答题"
                    )

        # 4b. 其余类别引用的 metric_id 必须真实存在
        else:
            mid = expected.get("metric_id")
            if mid:
                outcome = registry.resolve(mid)
                if isinstance(outcome, Refusal):
                    problems.append(
                        f"{path.name}：expected.metric_id {mid!r} 在 metrics/ 中不存在"
                    )

        # 5. 引用的夹具必须存在
        fixture = expected.get("fixture")
        if fixture and not (suite_dir / "fixtures" / f"{fixture}.yaml").is_file():
            problems.append(f"{path.name}：引用的夹具不存在：fixtures/{fixture}.yaml")

    return problems


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "UNKNOWN"


def freeze(suite_dir: Path) -> tuple[str, list[Path]]:
    """填入同一个 UTC 时间戳，再生成 SHA256SUMS。

    **顺序不能反**：先填 frozen_at 再算哈希，否则清单校验立刻失效。
    """
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if 'frozen_at: ""' not in text:
            raise SystemExit(f"{path.name}：frozen_at 不是空占位，疑似已冻结，拒绝覆盖")
        path.write_text(
            text.replace('frozen_at: ""', f'frozen_at: "{stamp}"', 1),
            encoding="utf-8", newline="\n",
        )

    covered = sorted((suite_dir / "cases").glob("*.yaml")) + sorted(
        (suite_dir / "fixtures").glob("*.yaml")
    )
    lines = []
    for path in covered:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest} *{path.relative_to(suite_dir).as_posix()}")
    (suite_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return stamp, covered


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eval.freeze")
    ap.add_argument("--suite", required=True)
    ap.add_argument("--check", action="store_true", help="只跑前置门禁，不执行冻结")
    args = ap.parse_args(argv)

    suite_dir = EVAL_ROOT / args.suite
    if not suite_dir.is_dir():
        print(f"套件目录不存在：{suite_dir}", file=sys.stderr)
        return 2

    problems = pregate(suite_dir)
    if problems:
        print("冻结前置门禁未通过，**拒绝冻结**（EVAL_CASES §2.1）：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"前置门禁通过：{len(list((suite_dir / 'cases').glob('*.yaml')))} 份题面")

    if args.check:
        print("--check 模式，未执行冻结。")
        return 0

    if (suite_dir / "SHA256SUMS").is_file():
        print("SHA256SUMS 已存在，该套件疑似已冻结。拒绝重复冻结。", file=sys.stderr)
        return 1

    stamp, covered = freeze(suite_dir)
    print(f"已冻结 {len(covered)} 个文件")
    print(f"  UTC 时间戳  {stamp}")
    print(f"  git commit  {_git_commit()}")
    print(f"  清单        {suite_dir / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
