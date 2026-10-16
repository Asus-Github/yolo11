#!/usr/bin/env python3
"""AutoDL serial experiment queue for TDW next experiments.

Runs, in order:
  1. TDW-CO-P3 WIoU rerun
  2. TDW-CO-D3
  3. DWCA-P2

For each experiment this script:
  - checks out the target branch on AutoDL
  - validates YAML/key structure
  - runs a WIoU smoke test in tmux
  - runs the full training in tmux after smoke success
  - parses best metrics
  - syncs all artifacts to local Mac including weights
  - updates the local Excel workbook
  - commits/pushes non-weight artifacts on the AutoDL branch

It intentionally uses a remote Python helper that sets
BboxLoss.iou_type = "wiou" before model.train(...). Do not replace it with
plain `yolo train` for WIoU experiments.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

LOCAL_ROOT = Path("/Users/asus/ultralytics")
EXCEL_PATH = LOCAL_ROOT / "刘华硕-飞书导入实验记录表.xlsx"
REMOTE = "autodl"
REMOTE_ROOT = Path("/root/autodl-tmp/ultralytics")
REMOTE_HELPER = Path("/root/autodl-tmp/ducc_wiou_train.py")
REMOTE_SUMMARY = Path("/root/autodl-tmp/ducc_collect_result.py")


@dataclass(frozen=True)
class Experiment:
    name: str
    branch: str
    yaml: str
    changelog: str
    tmux: str
    triplet: str
    dyhead: str
    wiou: str
    excel_remark_pending: str
    structure_kind: str


EXPERIMENTS = [
    Experiment(
        name="TDW-CO-P3",
        branch="feat/tdw-co-p3",
        yaml="ultralytics/cfg/models/11/yolo11-tdw-co-p3.yaml",
        changelog="CHANGELOG-TDW-CO-P3.md",
        tmux="t_train_tdw_co_p3_wiou",
        triplet="✅",
        dyhead="✅",
        wiou="✅",
        excel_remark_pending="WIoU 正式重跑；正式训练完成后填表。",
        structure_kind="tdw_co_p3",
    ),
    Experiment(
        name="TDW-CO-D3",
        branch="feat/tdw-co-d3",
        yaml="ultralytics/cfg/models/11/yolo11-tdw-co-d3.yaml",
        changelog="CHANGELOG-TDW-CO-D3.md",
        tmux="t_train_tdw_co_d3",
        triplet="✅",
        dyhead="✅",
        wiou="✅",
        excel_remark_pending="DyHeadDetect 2→3 blocks；等待训练完成填表。",
        structure_kind="tdw_co_d3",
    ),
    Experiment(
        name="DWCA-P2",
        branch="feat/dwca-p2",
        yaml="ultralytics/cfg/models/11/yolo11-dwca-p2.yaml",
        changelog="CHANGELOG-DWCA-P2.md",
        tmux="t_train_dwca_p2",
        triplet="❌",
        dyhead="✅",
        wiou="✅",
        excel_remark_pending="CoordAttention + P2 检测头；等待训练完成填表。",
        structure_kind="dwca_p2",
    ),
]

HELPER_CODE = r'''
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# This helper lives outside the repo, so put the checked-out repo on sys.path
# before importing the local ultralytics package.
sys.path.insert(0, str(Path.cwd()))
from ultralytics import YOLO
from ultralytics.utils.loss import BboxLoss


def patch_dataset_yaml(repo_root: Path) -> Path:
    src = repo_root / "datasets/dair_v2x_i/dair_v2x_i.yaml"
    cfg = yaml.safe_load(src.read_text())
    cfg["path"] = str(repo_root / "datasets/dair_v2x_i")
    out = repo_root / "datasets/dair_v2x_i/_runtime.yaml"
    out.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--epochs", type=int, required=True)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="0")
    ap.add_argument("--project", default="runs/ablation")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--patience", type=int, default=50)
    ap.add_argument("--nbs", type=int, default=64)
    ap.add_argument("--pretrained", choices=["true", "false"], default="true")
    ap.add_argument("--cos-lr", action="store_true")
    ap.add_argument("--plots", action="store_true")
    ap.add_argument("--exist-ok", action="store_true")
    args = ap.parse_args()

    repo_root = Path.cwd()
    data_yaml = patch_dataset_yaml(repo_root)

    BboxLoss.iou_type = "wiou"
    print(f"[ducc_wiou_train] BboxLoss.iou_type = {BboxLoss.iou_type}", flush=True)
    if BboxLoss.iou_type != "wiou":
        raise RuntimeError("WIoU setup failed: BboxLoss.iou_type is not wiou")

    batch = float(args.batch) if "." in str(args.batch) else int(args.batch)

    model = YOLO(args.cfg)
    model.info(detailed=False, verbose=True)
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=batch,
        nbs=args.nbs,
        device=args.device,
        workers=args.workers,
        optimizer="SGD",
        lr0=0.01,
        cos_lr=args.cos_lr,
        weight_decay=0.0005,
        project=args.project,
        name=args.name,
        seed=args.seed,
        pretrained=(args.pretrained == "true"),
        amp=True,
        cache=False,
        patience=args.patience,
        exist_ok=args.exist_ok,
        plots=args.plots,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

SUMMARY_CODE = r'''
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def parse_results(exp: str) -> dict:
    run_dir = Path("runs/detect/runs/ablation") / exp
    csv_path = run_dir / "results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    rows = list(csv.DictReader(csv_path.open()))
    if not rows:
        raise RuntimeError(f"empty results.csv: {csv_path}")

    def get(row, name):
        for k, v in row.items():
            if k.strip() == name:
                return v
        return None

    best = max(rows, key=lambda r: float(get(r, "metrics/mAP50-95(B)") or 0))
    out = {
        "name": exp,
        "epochs_recorded": len(rows),
        "best_epoch": int(float(get(best, "epoch"))),
        "precision": float(get(best, "metrics/precision(B)")),
        "recall": float(get(best, "metrics/recall(B)")),
        "map50": float(get(best, "metrics/mAP50(B)")),
        "map50_95": float(get(best, "metrics/mAP50-95(B)")),
        "run_dir": str(run_dir),
    }

    log_path = Path("runs") / f"{exp}_train.log"
    out["log_path"] = str(log_path)
    if log_path.exists():
        txt = log_path.read_text(errors="replace")
        matches = re.findall(r"summary(?: \(fused\))?: .*?([0-9,]+) parameters.*?([0-9.]+) GFLOPs", txt)
        if matches:
            params_s, gflops_s = matches[-1]
            out["params_m"] = round(int(params_s.replace(",", "")) / 1_000_000, 2)
            out["gflops"] = round(float(gflops_s), 2)
        out["wiou_logged"] = "[ducc_wiou_train] BboxLoss.iou_type = wiou" in txt
    else:
        out["wiou_logged"] = False
    print(json.dumps(out, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    args = ap.parse_args()
    parse_results(args.exp)


if __name__ == "__main__":
    main()
'''

STRUCTURE_CHECK_CODE = r'''
from __future__ import annotations

import argparse
from pathlib import Path
import sys

# This checker lives outside the repo, so put the checked-out repo on sys.path
# before importing the local ultralytics package.
sys.path.insert(0, str(Path.cwd()))
from ultralytics import YOLO
from ultralytics.utils.loss import BboxLoss


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", required=True)
    ap.add_argument("--kind", required=True)
    ap.add_argument("--changelog", required=True)
    args = ap.parse_args()

    y = Path(args.yaml)
    c = Path(args.changelog)
    require(y.exists(), f"YAML missing: {y}")
    require(c.exists(), f"CHANGELOG missing: {c}")
    txt = y.read_text()

    if args.kind == "tdw_co_p3":
        require("TripletAttention" in txt and "True" in txt, "TDW-CO-P3 must include channel-only TripletAttention [True]")
        require("DyHeadDetect" in txt, "TDW-CO-P3 must use DyHeadDetect")
        require("DyHeadDetect3" not in txt, "TDW-CO-P3 should not use DyHeadDetect3")
    elif args.kind == "tdw_co_d3":
        require("DyHeadDetect3" in txt, "TDW-CO-D3 must use DyHeadDetect3")
        head = Path("ultralytics/nn/modules/head.py").read_text()
        init = Path("ultralytics/nn/modules/__init__.py").read_text()
        tasks = Path("ultralytics/nn/tasks.py").read_text()
        require("class DyHeadDetect3" in head, "DyHeadDetect3 class missing in head.py")
        require("DyHeadDetect3" in init, "DyHeadDetect3 export missing")
        require("DyHeadDetect3" in tasks, "DyHeadDetect3 parse_model registration/import missing")
    elif args.kind == "dwca_p2":
        require("CoordAttention" in txt, "DWCA-P2 YAML must include CoordAttention")
        require("DyHeadDetect" in txt, "DWCA-P2 must use DyHeadDetect")
        require(txt.count("Concat") >= 6, "DWCA-P2 should have P2/P3/P4/P5 neck with multiple Concat ops")
        conv = Path("ultralytics/nn/modules/conv.py").read_text()
        init = Path("ultralytics/nn/modules/__init__.py").read_text()
        tasks = Path("ultralytics/nn/tasks.py").read_text()
        require("class CoordAttention" in conv, "CoordAttention class missing in conv.py")
        require("CoordAttention" in init, "CoordAttention export missing")
        require("CoordAttention" in tasks, "CoordAttention parse_model registration/import missing")
    else:
        raise AssertionError(f"unknown kind: {args.kind}")

    BboxLoss.iou_type = "wiou"
    require(BboxLoss.iou_type == "wiou", "BboxLoss.iou_type did not become wiou")
    print(f"[ducc_preflight] BboxLoss.iou_type = {BboxLoss.iou_type}")
    model = YOLO(str(y))
    model.info(detailed=False, verbose=True)
    print(f"[ducc_preflight] structure check passed: {args.kind} {args.yaml}")


if __name__ == "__main__":
    main()
'''


def run(cmd: list[str] | str, *, check: bool = True, capture: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    if isinstance(cmd, str):
        printable = cmd
        shell = True
    else:
        printable = " ".join(shlex.quote(c) for c in cmd)
        shell = False
    print(f"[local] $ {printable}", flush=True)
    return subprocess.run(cmd, shell=shell, text=True, check=check, capture_output=capture, timeout=timeout)


def ssh(command: str, *, check: bool = True, capture: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run(["ssh", REMOTE, command], check=check, capture=capture, timeout=timeout)


def scp_from(remote_path: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    run(["scp", "-r", f"{REMOTE}:{remote_path}", str(local_path)])


def upload_remote_helpers() -> None:
    for path, code in [(REMOTE_HELPER, HELPER_CODE), (REMOTE_SUMMARY, SUMMARY_CODE), (Path("/root/autodl-tmp/ducc_structure_check.py"), STRUCTURE_CHECK_CODE)]:
        quoted = shlex.quote(code)
        ssh(f"cat > {shlex.quote(str(path))} <<'PY'\n{code}\nPY\nchmod +x {shlex.quote(str(path))}")


def ensure_excel_rows() -> None:
    wb = load_workbook(EXCEL_PATH)
    ws = wb["数据表"]
    # Ensure formal TDW-CO-P3 WIoU row exists.
    formal_exists = any(ws.cell(r, 3).value == "TDW-CO-P3" and ws.cell(r, 5).value == "WIoU" for r in range(2, ws.max_row + 1))
    if not formal_exists:
        ws.insert_rows(21)
        values = [20, "下一阶段消融实验", "TDW-CO-P3", "yolo11-tdw-co-p3.yaml", "WIoU", "✅", "✅", "✅", None, None, None, None, None, None, None, "WIoU 正式重跑；正式训练完成后填表。"]
        for c, v in enumerate(values, 1):
            ws.cell(21, c).value = v
    # Ensure rows for all experiments exist and have pending remarks.
    for exp in EXPERIMENTS:
        row = find_excel_row(ws, exp)
        if row is None:
            ws.append([None, "下一阶段消融实验", exp.name, Path(exp.yaml).name, "WIoU", exp.triplet, exp.dyhead, exp.wiou, None, None, None, None, None, None, None, exp.excel_remark_pending])
    # Renumber logical sequence from row 21 onward if needed.
    seq = 20
    for r in range(21, ws.max_row + 1):
        ws.cell(r, 1).value = seq
        seq += 1
    wb.save(EXCEL_PATH)


def find_excel_row(ws, exp: Experiment) -> int | None:
    # Prefer an unfinished WIoU row for this experiment.
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 3).value == exp.name and ws.cell(r, 5).value == "WIoU":
            return r
    return None


def update_excel(exp: Experiment, summary: dict[str, Any]) -> None:
    wb = load_workbook(EXCEL_PATH)
    ws = wb["数据表"]
    row = find_excel_row(ws, exp)
    if row is None:
        ws.append([None, "下一阶段消融实验", exp.name, Path(exp.yaml).name, "WIoU", exp.triplet, exp.dyhead, exp.wiou, None, None, None, None, None, None, None, exp.excel_remark_pending])
        row = ws.max_row
    ws.cell(row, 2).value = "下一阶段消融实验"
    ws.cell(row, 3).value = exp.name
    ws.cell(row, 4).value = Path(exp.yaml).name
    ws.cell(row, 5).value = "WIoU"
    ws.cell(row, 6).value = exp.triplet
    ws.cell(row, 7).value = exp.dyhead
    ws.cell(row, 8).value = exp.wiou
    ws.cell(row, 9).value = round(summary["precision"] * 100, 1)
    ws.cell(row, 10).value = round(summary["recall"] * 100, 1)
    ws.cell(row, 11).value = round(summary["map50"] * 100, 1)
    ws.cell(row, 12).value = round(summary["map50_95"] * 100, 1)
    if "gflops" in summary:
        ws.cell(row, 14).value = summary["gflops"]
    if "params_m" in summary:
        ws.cell(row, 15).value = summary["params_m"]
    wiou_note = "WIoU已确认" if summary.get("wiou_logged") else "WIoU日志未确认"
    ws.cell(row, 16).value = f"best epoch={summary['best_epoch']}；{wiou_note}；AutoDL串行自动训练完成。"
    seq = 20
    for r in range(21, ws.max_row + 1):
        ws.cell(r, 1).value = seq
        seq += 1
    wb.save(EXCEL_PATH)
    print(f"[excel] updated row {row} for {exp.name}")


def checkout_and_preflight(exp: Experiment) -> None:
    print(f"\n=== Preflight {exp.name} ===", flush=True)
    cmd = f"""
set -euo pipefail
source /etc/network_turbo
cd {shlex.quote(str(REMOTE_ROOT))}
git fetch origin
git checkout {shlex.quote(exp.branch)}
git pull --ff-only origin {shlex.quote(exp.branch)}
/root/miniconda3/bin/python /root/autodl-tmp/ducc_structure_check.py --yaml {shlex.quote(exp.yaml)} --kind {shlex.quote(exp.structure_kind)} --changelog {shlex.quote(exp.changelog)}
"""
    ssh(cmd, timeout=600)


def tmux_run_and_wait(session: str, command: str, timeout_seconds: int) -> None:
    # tmux remain-on-exit keeps panes alive and successful commands return to shell,
    # so pane_dead is not a reliable completion signal. Use explicit marker files.
    marker = f"/root/autodl-tmp/{session}.done"
    status = f"/root/autodl-tmp/{session}.status"
    wrapped = f"rm -f {shlex.quote(marker)} {shlex.quote(status)}; ( {command} ); rc=$?; echo $rc > {shlex.quote(status)}; touch {shlex.quote(marker)}; exit $rc"
    escaped = wrapped.replace("'", "'\\''")
    setup = f"""
set -euo pipefail
(tmux has-session -t {shlex.quote(session)} 2>/dev/null && tmux kill-session -t {shlex.quote(session)}) || true
rm -f {shlex.quote(marker)} {shlex.quote(status)}
tmux new-session -d -s {shlex.quote(session)}
tmux set-option -t {shlex.quote(session)} remain-on-exit on
tmux set-option -g mouse on
tmux set-window-option -g history-limit 100000
tmux send-keys -t {shlex.quote(session)} '{escaped}' Enter
"""
    ssh(setup, timeout=120)
    start = time.time()
    while True:
        done = ssh(f"test -f {shlex.quote(marker)} && cat {shlex.quote(status)} || true", capture=True, check=False, timeout=60)
        out = (done.stdout or "").strip()
        if out:
            if out != "0":
                pane = ssh(f"tmux capture-pane -t {shlex.quote(session)} -p -S -80", capture=True, check=False, timeout=60)
                print(pane.stdout or "", flush=True)
                raise RuntimeError(f"tmux session failed: {session} rc={out}")
            break
        pane = ssh(f"tmux list-panes -t {shlex.quote(session)} -F '#{{pane_dead}} #{{pane_current_command}}'", capture=True, check=False, timeout=60)
        pane_out = (pane.stdout or "").strip()
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"tmux session timed out: {session}")
        print(f"[wait] {session}: {pane_out or 'running'}", flush=True)
        time.sleep(120)


def archive_tdw_co_p3_ref() -> None:
    cmd = f"""
set -euo pipefail
cd {shlex.quote(str(REMOTE_ROOT))}
if [ -d runs/detect/runs/ablation/TDW-CO-P3 ] && [ ! -d runs/detect/runs/ablation/TDW-CO-P3-CIoU-ref ]; then
  mv runs/detect/runs/ablation/TDW-CO-P3 runs/detect/runs/ablation/TDW-CO-P3-CIoU-ref
fi
if [ -f runs/TDW-CO-P3_train.log ] && [ ! -f runs/TDW-CO-P3-CIoU-ref_train.log ]; then
  mv runs/TDW-CO-P3_train.log runs/TDW-CO-P3-CIoU-ref_train.log
fi
"""
    ssh(cmd, timeout=120)


def run_smoke(exp: Experiment) -> None:
    print(f"\n=== Smoke {exp.name} ===", flush=True)
    session = f"{exp.tmux}_smoke"
    smoke_name = f"_smoke_{exp.name}"
    command = (
        f"source /etc/network_turbo && cd {shlex.quote(str(REMOTE_ROOT))} && "
        f"/root/miniconda3/bin/python {shlex.quote(str(REMOTE_HELPER))} "
        f"--cfg {shlex.quote(exp.yaml)} --name {shlex.quote(smoke_name)} --epochs 1 --batch 0.85 --imgsz 640 --seed 42 --project runs/ablation --patience 50 --nbs 64 --pretrained true --cos-lr --exist-ok --plots "
        f"2>&1 | tee runs/{shlex.quote(exp.name)}_smoke.log"
    )
    tmux_run_and_wait(session, command, timeout_seconds=60 * 60)
    verify = f"""
set -euo pipefail
cd {shlex.quote(str(REMOTE_ROOT))}
grep -F '[ducc_wiou_train] BboxLoss.iou_type = wiou' runs/{shlex.quote(exp.name)}_smoke.log
grep -F 'Results saved to' runs/{shlex.quote(exp.name)}_smoke.log
[ -f runs/detect/runs/ablation/{shlex.quote(smoke_name)}/results.csv ]
"""
    ssh(verify, timeout=120)
    print(f"[smoke] passed: {exp.name}")


def run_full_train(exp: Experiment) -> None:
    print(f"\n=== Full train {exp.name} ===", flush=True)
    if exp.name == "TDW-CO-P3":
        archive_tdw_co_p3_ref()
    command = (
        f"source /etc/network_turbo && cd {shlex.quote(str(REMOTE_ROOT))} && "
        f"/root/miniconda3/bin/python {shlex.quote(str(REMOTE_HELPER))} "
        f"--cfg {shlex.quote(exp.yaml)} --name {shlex.quote(exp.name)} --epochs 300 --batch 0.85 --imgsz 640 --seed 42 --project runs/ablation --patience 50 --nbs 64 --pretrained true --cos-lr --exist-ok --plots "
        f"2>&1 | tee runs/{shlex.quote(exp.name)}_train.log"
    )
    tmux_run_and_wait(exp.tmux, command, timeout_seconds=12 * 60 * 60)
    verify = f"""
set -euo pipefail
cd {shlex.quote(str(REMOTE_ROOT))}
grep -F '[ducc_wiou_train] BboxLoss.iou_type = wiou' runs/{shlex.quote(exp.name)}_train.log
[ -f runs/detect/runs/ablation/{shlex.quote(exp.name)}/results.csv ]
[ -f runs/detect/runs/ablation/{shlex.quote(exp.name)}/weights/best.pt ]
"""
    ssh(verify, timeout=120)


def collect_summary(exp: Experiment) -> dict[str, Any]:
    cp = ssh(f"cd {shlex.quote(str(REMOTE_ROOT))} && /root/miniconda3/bin/python {shlex.quote(str(REMOTE_SUMMARY))} --exp {shlex.quote(exp.name)}", capture=True, timeout=120)
    line = (cp.stdout or "").strip().splitlines()[-1]
    summary = json.loads(line)
    print(f"[summary] {summary}")
    return summary


def sync_artifacts(exp: Experiment) -> None:
    local_run_dir = LOCAL_ROOT / "runs/detect/runs/ablation" / exp.name
    local_log = LOCAL_ROOT / "runs" / f"{exp.name}_train.log"
    if local_run_dir.exists():
        backup = local_run_dir.with_name(local_run_dir.name + f".backup-{int(time.time())}")
        local_run_dir.rename(backup)
        print(f"[sync] moved existing local run dir to {backup}")
    scp_from(f"{REMOTE_ROOT}/runs/detect/runs/ablation/{exp.name}", local_run_dir)
    scp_from(f"{REMOTE_ROOT}/runs/{exp.name}_train.log", local_log)


def commit_push_artifacts(exp: Experiment) -> None:
    cmd = f"""
set -euo pipefail
source /etc/network_turbo
cd {shlex.quote(str(REMOTE_ROOT))}
git checkout {shlex.quote(exp.branch)}
git add -f runs/{shlex.quote(exp.name)}_train.log runs/detect/runs/ablation/{shlex.quote(exp.name)}
git reset -q -- runs/detect/runs/ablation/{shlex.quote(exp.name)}/weights || true
git status --short
if git diff --cached --quiet; then
  echo '[git] no non-weight artifacts to commit'
else
  git commit -m 'feat(results): add {exp.name} WIoU training results'
  git push origin {shlex.quote(exp.branch)}
fi
"""
    ssh(cmd, timeout=600)


def run_queue(smoke_only: bool = False, start_full_after_smoke: bool = True) -> None:
    ensure_excel_rows()
    upload_remote_helpers()
    # Preflight + smoke all experiments first.
    for exp in EXPERIMENTS:
        checkout_and_preflight(exp)
        run_smoke(exp)
    if smoke_only:
        print("[queue] smoke-only mode finished successfully")
        return
    if not start_full_after_smoke:
        print("[queue] smoke finished; full training disabled")
        return
    for exp in EXPERIMENTS:
        checkout_and_preflight(exp)
        run_full_train(exp)
        summary = collect_summary(exp)
        sync_artifacts(exp)
        update_excel(exp, summary)
        commit_push_artifacts(exp)
        print(f"[queue] completed {exp.name}")
    print("[queue] all experiments completed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-only", action="store_true", help="run only preflight + smoke for all experiments")
    ap.add_argument("--no-full", action="store_true", help="do not start full training after smoke")
    args = ap.parse_args()
    run_queue(smoke_only=args.smoke_only, start_full_after_smoke=not args.no_full)
    return 0


if __name__ == "__main__":
    sys.exit(main())
