# YOLO11n-DWCA-P2 Paper Inputs

This folder is the clean paper workspace for branch `codex/paper-yolo11n-dwca-p2-clean`.

## Authoritative Inputs

- `刘华硕-飞书导入实验记录表.xlsx`: authoritative experiment result table.
- `yolo11n-dwca-p2-original-draft.md`: original manuscript draft copied from the working branch.
- `dair_v2x_i.yaml`: dataset split and class configuration.
- `model_yamls/`: model YAML files used for the paper and ablation discussion.

## Current Data Policy

- Use `刘华硕-飞书导入实验记录表.xlsx` as the primary source for experiment metrics.
- Unless a row explicitly marks a different batch setting, interpret experiments as fixed `batch=32`.
- All rows in the Excel table are valid experiments.
- Negative/underperforming ablation rows are still valid evidence and can be used to show why the final route was chosen.
- Re-draw all paper figures from the clean Excel/table inputs; do not reuse the old cluttered chart assets by default.

## Pending Confirmation

- Confirm whether the final named method should be `DWCA-P2-b32` or whether `YOLO11n-TDW` should be discussed as an earlier complete model only.
- Confirm whether all 26 Excel rows should appear in one full ablation/reference table, or whether the paper should split them into main results, ablation, structure comparison, pretrained reference, and FPS tables.
- Confirm whether scale-group AP has already been computed elsewhere; if not found in this clean branch, return to the source branch or ask the user before claiming it.
