from __future__ import annotations

from pathlib import Path


OUT = Path("/Users/asus/ultralytics/docs/paper_assets")


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def header(width: int, height: int, title: str, subtitle: str = "") -> list[str]:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">',
        '<path d="M0,0 L10,5 L0,10 Z" fill="#111827"/>',
        "</marker>",
        "<style>",
        ".title{font:700 28px Arial,Helvetica,sans-serif;fill:#111827}",
        ".subtitle{font:15px Arial,Helvetica,sans-serif;fill:#4B5563}",
        ".section{font:700 18px Arial,Helvetica,sans-serif;fill:#111827}",
        ".label{font:700 14px Arial,Helvetica,sans-serif;fill:#111827}",
        ".small{font:12px Arial,Helvetica,sans-serif;fill:#374151}",
        ".tiny{font:11px Arial,Helvetica,sans-serif;fill:#4B5563}",
        ".box{stroke:#111827;stroke-width:1.4;rx:8;ry:8}",
        ".lane{stroke:#CBD5E1;stroke-width:1;stroke-dasharray:6 5}",
        ".arrow{stroke:#111827;stroke-width:2.0;fill:none;marker-end:url(#arrow)}",
        ".thin{stroke:#6B7280;stroke-width:1.6;fill:none;marker-end:url(#arrow)}",
        ".dash{stroke:#9F1239;stroke-width:1.8;stroke-dasharray:7 5;fill:none;marker-end:url(#arrow)}",
        "</style>",
        "</defs>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
        f'<text x="{width/2}" y="42" text-anchor="middle" class="title">{esc(title)}</text>',
    ]
    if subtitle:
        lines.append(f'<text x="{width/2}" y="68" text-anchor="middle" class="subtitle">{esc(subtitle)}</text>')
    return lines


def rect(lines: list[str], x: int, y: int, w: int, h: int, fill: str, text: str, sub: str = "", stroke: str = "#111827", sw: float = 1.4) -> None:
    lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="box" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    lines.append(f'<text x="{x+w/2}" y="{y+h/2-4}" text-anchor="middle" class="label">{esc(text)}</text>')
    if sub:
        lines.append(f'<text x="{x+w/2}" y="{y+h/2+16}" text-anchor="middle" class="small">{esc(sub)}</text>')


def text(lines: list[str], x: int, y: int, s: str, cls: str = "small", anchor: str = "middle") -> None:
    lines.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{esc(s)}</text>')


def arrow(lines: list[str], x1: int, y1: int, x2: int, y2: int, cls: str = "arrow") -> None:
    if x1 == x2 or y1 == y2:
        lines.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="{cls}"/>')
    else:
        mid = (x1 + x2) // 2
        lines.append(f'<path d="M{x1},{y1} L{mid},{y1} L{mid},{y2} L{x2},{y2}" class="{cls}"/>')


def poly_arrow(lines: list[str], points: list[tuple[int, int]], cls: str = "arrow") -> None:
    d = " ".join(("M" if i == 0 else "L") + f"{x},{y}" for i, (x, y) in enumerate(points))
    lines.append(f'<path d="{d}" class="{cls}"/>')


def save(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines + ["</svg>"]), encoding="utf-8")


def overview() -> None:
    w, h = 1700, 980
    lines = header(
        w,
        h,
        "YOLOv11n-DWCA-P2 Architecture",
        "Verified topology: CA at layer 5; P2 branch at layer 20; DyHeadDetect inputs [20, 23, 26, 29]",
    )

    for y, name in [(250, "P2 / 4"), (390, "P3 / 8"), (530, "P4 / 16"), (670, "P5 / 32")]:
        lines.append(f'<line x1="70" y1="{y+33}" x2="1615" y2="{y+33}" class="lane"/>')
        text(lines, 42, y + 38, name, "section", "start")

    text(lines, 210, 118, "Backbone", "section")
    text(lines, 595, 118, "Top-down FPN", "section")
    text(lines, 920, 118, "Bottom-up PAN", "section")
    text(lines, 1195, 118, "Detect inputs", "section")
    text(lines, 1445, 118, "Head and loss", "section")

    rect(lines, 115, 132, 190, 56, "#EEF2FF", "Input", "640 x 640 x 3")
    rect(lines, 115, 230, 190, 72, "#DBEAFE", "Layer 2", "P2 source: C3k2")
    rect(lines, 115, 370, 190, 72, "#BBF7D0", "Layer 5", "P3 source + CoordAttention", "#047857", 2.6)
    rect(lines, 115, 510, 190, 72, "#DBEAFE", "Layer 7", "P4 source: C3k2")
    rect(lines, 115, 650, 190, 72, "#BFDBFE", "Layer 11", "P5 source: SPPF+C2PSA")
    arrow(lines, 210, 188, 210, 230, "thin")
    arrow(lines, 210, 302, 210, 370, "thin")
    arrow(lines, 210, 442, 210, 510, "thin")
    arrow(lines, 210, 582, 210, 650, "thin")

    rect(lines, 520, 510, 190, 72, "#DCFCE7", "Layer 14", "P5 up + P4 concat")
    rect(lines, 520, 370, 190, 72, "#DCFCE7", "Layer 17", "N4 up + P3 concat")
    rect(lines, 520, 230, 190, 72, "#DBEAFE", "Layer 20", "P3 up + P2 concat", "#2563EB", 2.8)
    poly_arrow(lines, [(305, 686), (430, 686), (430, 546), (520, 546)], "thin")
    arrow(lines, 305, 546, 520, 546, "thin")
    arrow(lines, 615, 510, 615, 442, "arrow")
    arrow(lines, 305, 406, 520, 406, "thin")
    arrow(lines, 615, 370, 615, 302, "arrow")
    arrow(lines, 305, 266, 520, 266, "thin")

    rect(lines, 840, 370, 190, 72, "#DCFCE7", "Layer 23", "P2 down + P3 concat")
    rect(lines, 840, 510, 190, 72, "#DCFCE7", "Layer 26", "P3 down + P4 concat")
    rect(lines, 840, 650, 190, 72, "#DCFCE7", "Layer 29", "P4 down + P5 concat")
    poly_arrow(lines, [(710, 266), (770, 266), (770, 406), (840, 406)], "arrow")
    arrow(lines, 710, 406, 840, 406, "thin")
    arrow(lines, 935, 442, 935, 510, "arrow")
    arrow(lines, 710, 546, 840, 546, "thin")
    arrow(lines, 935, 582, 935, 650, "arrow")
    arrow(lines, 305, 686, 840, 686, "thin")

    lines.append('<rect x="1100" y="205" width="150" height="520" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.4" rx="12"/>')
    text(lines, 1175, 238, "feature set", "label")
    for y, scale, layer in [(266, "P2", "20"), (406, "P3", "23"), (546, "P4", "26"), (686, "P5", "29")]:
        rect(lines, 1120, y - 23, 110, 46, "#FFFFFF", f"{scale}", f"layer {layer}", "#CBD5E1", 1.2)
    arrow(lines, 710, 266, 1120, 266, "arrow")
    arrow(lines, 1030, 406, 1120, 406, "arrow")
    arrow(lines, 1030, 546, 1120, 546, "arrow")
    arrow(lines, 1030, 686, 1120, 686, "arrow")

    rect(lines, 1305, 315, 220, 250, "#FECACA", "DyHeadDetect", "2 DyHeadBlocks / scale", "#BE123C", 2.8)
    arrow(lines, 1250, 466, 1305, 440, "arrow")
    rect(lines, 1540, 300, 130, 78, "#FFF1F2", "Inference", "box + cls")
    rect(lines, 1540, 500, 130, 78, "#FFE4E6", "WIoU v3", "training loss", "#BE123C", 2.2)
    rect(lines, 1308, 635, 150, 58, "#F3F4F6", "GT labels", "train only")
    arrow(lines, 1525, 440, 1540, 339, "arrow")
    poly_arrow(lines, [(1425, 565), (1425, 539), (1540, 539)], "dash")
    poly_arrow(lines, [(1383, 635), (1383, 539), (1540, 539)], "dash")
    text(lines, 1475, 522, "loss path", "tiny")

    lines.append('<rect x="92" y="790" width="1515" height="115" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.4" rx="12"/>')
    rect(lines, 125, 805, 28, 22, "#DBEAFE", "", "", "#2563EB", 2.4)
    text(lines, 165, 821, "P2/4 branch: high-resolution tiny-object scale", "tiny", "start")
    rect(lines, 580, 805, 28, 22, "#BBF7D0", "", "", "#047857", 2.4)
    text(lines, 620, 821, "CoordAttention: layer 5 after P3", "tiny", "start")
    rect(lines, 925, 805, 28, 22, "#FECACA", "", "", "#BE123C", 2.4)
    text(lines, 965, 821, "DyHeadDetect: inputs P2-P5", "tiny", "start")
    rect(lines, 125, 845, 28, 22, "#FFE4E6", "", "", "#BE123C", 2.0)
    text(lines, 165, 861, "WIoU v3: training loss only", "tiny", "start")
    text(lines, 580, 861, "Triplet attention is removed in this variant", "tiny", "start")

    save(OUT / "dwca_p2_overview_optimized.svg", lines)


def p2_branch() -> None:
    lines = header(1180, 520, "P2 Branch", "P3/8 is upsampled and fused with layer-2 P2/4; layer 20 enters DyHeadDetect")
    rect(lines, 70, 210, 165, 70, "#DCFCE7", "Layer 17", "P3/8 feature")
    rect(lines, 285, 210, 150, 70, "#E0F2FE", "Upsample", "x2")
    rect(lines, 485, 130, 165, 70, "#DBEAFE", "Layer 2", "P2/4 source")
    rect(lines, 485, 250, 165, 70, "#EFF6FF", "Concat", "P3 up + P2")
    rect(lines, 705, 250, 170, 70, "#DBEAFE", "Layer 20", "C3k2 P2 tiny", "#2563EB", 2.8)
    rect(lines, 940, 185, 170, 70, "#FECACA", "DyHeadDetect", "P2 input")
    rect(lines, 940, 330, 170, 70, "#DCFCE7", "Bottom-up", "Conv s=2 -> P3")
    arrow(lines, 235, 245, 285, 245)
    arrow(lines, 435, 245, 485, 285)
    arrow(lines, 568, 200, 568, 250, "thin")
    arrow(lines, 650, 285, 705, 285)
    arrow(lines, 875, 285, 940, 220)
    arrow(lines, 790, 320, 940, 365, "thin")
    text(lines, 590, 382, "P2 preserves fine spatial detail for tiny roadside objects", "small")
    save(OUT / "module_p2_branch.svg", lines)


def coord_attention() -> None:
    lines = header(1320, 640, "CoordAttention", "pool_h/pool_w -> shared 1x1 bottleneck -> split -> sigmoid gates a_h and a_w")
    rect(lines, 55, 275, 150, 70, "#F3F4F6", "Input X", "B,C,H,W")
    rect(lines, 275, 180, 185, 70, "#DCFCE7", "AvgPool over W", "B,C,H,1")
    rect(lines, 275, 370, 185, 70, "#DCFCE7", "AvgPool over H", "B,C,1,W -> B,C,W,1")
    rect(lines, 535, 275, 185, 70, "#DBEAFE", "Concat", "B,C,H+W,1")
    rect(lines, 790, 275, 185, 70, "#E0F2FE", "1x1 Conv+BN+SiLU", "C -> max(8,C/32)")
    rect(lines, 1035, 180, 190, 70, "#BBF7D0", "Conv_h + sigmoid", "a_h: B,C,H,1")
    rect(lines, 1035, 370, 190, 70, "#BBF7D0", "Conv_w + sigmoid", "a_w: B,C,1,W")
    rect(lines, 575, 515, 210, 70, "#DCFCE7", "Output", "Y = X * a_h * a_w")
    arrow(lines, 205, 310, 275, 215)
    arrow(lines, 205, 310, 275, 405)
    arrow(lines, 460, 215, 535, 310)
    arrow(lines, 460, 405, 535, 310)
    arrow(lines, 720, 310, 790, 310)
    arrow(lines, 975, 310, 1035, 215)
    arrow(lines, 975, 310, 1035, 405)
    arrow(lines, 1130, 250, 680, 515, "thin")
    arrow(lines, 1130, 440, 680, 515, "thin")
    arrow(lines, 130, 345, 575, 550, "thin")
    text(lines, 660, 110, "Placed at backbone layer 5 after P3 feature extraction", "small")
    save(OUT / "module_coord_attention.svg", lines)


def dyhead() -> None:
    lines = header(1380, 700, "DyHeadDetect", "Inputs [20, 23, 26, 29]; each scale passes two DyHeadBlocks before Detect branches")
    y_positions = [170, 270, 370, 470]
    labels = [("P2", "layer 20"), ("P3", "layer 23"), ("P4", "layer 26"), ("P5", "layer 29")]
    for y, (scale, layer) in zip(y_positions, labels):
        rect(lines, 70, y, 150, 56, "#DBEAFE", f"{scale}", layer)
        arrow(lines, 220, y + 28, 300, y + 28)
    rect(lines, 300, 130, 245, 400, "#FEE2E2", "DyHeadBlock x2", "per scale, not shared", "#BE123C", 2.6)
    rect(lines, 635, 130, 190, 78, "#FFE4E6", "Spatial-aware", "3x3 Conv + GN")
    rect(lines, 635, 270, 190, 78, "#FFE4E6", "Scale-aware", "GAP -> 1x1 -> Hardsigmoid")
    rect(lines, 635, 410, 190, 78, "#FFE4E6", "Task-aware", "DyReLU-B")
    rect(lines, 930, 270, 185, 78, "#FFF1F2", "Detect cv2/cv3", "bbox + cls branches")
    rect(lines, 1210, 270, 130, 78, "#F3F4F6", "Output", "box + cls")
    arrow(lines, 545, 330, 635, 169)
    arrow(lines, 730, 208, 730, 270)
    arrow(lines, 730, 348, 730, 410)
    arrow(lines, 825, 449, 930, 309)
    arrow(lines, 1115, 309, 1210, 309)
    text(lines, 730, 590, "DyReLU-B: y = max(a1*x + b1, a2*x + b2), where a1,b1,a2,b2 are predicted from global pooled features", "small")
    save(OUT / "module_dyhead_detect.svg", lines)


def wiou() -> None:
    lines = header(1380, 640, "Wise-IoU v3 Loss", "Training only; replaces CIoU inside BboxLoss when BboxLoss.iou_type = 'wiou'")
    rect(lines, 70, 230, 170, 70, "#F3F4F6", "Pred boxes", "from Detect")
    rect(lines, 70, 370, 170, 70, "#F3F4F6", "Target boxes", "matched GT")
    rect(lines, 320, 300, 180, 70, "#DBEAFE", "IoU + center dist", "iou, rho^2, c^2")
    rect(lines, 580, 175, 200, 70, "#FFE4E6", "R_WIoU", "exp(rho^2 / c^2_detach)")
    rect(lines, 580, 300, 200, 70, "#FFE4E6", "loss_iou_per", "1 - iou")
    rect(lines, 580, 425, 200, 70, "#FFE4E6", "running mean", "iou_mean update")
    rect(lines, 870, 300, 210, 70, "#FECACA", "dynamic focus", "beta/(delta*alpha^(beta-delta))", "#BE123C", 2.6)
    rect(lines, 1160, 300, 170, 70, "#FFF1F2", "bbox loss", "weighted sum")
    arrow(lines, 240, 265, 320, 335)
    arrow(lines, 240, 405, 320, 335)
    arrow(lines, 500, 335, 580, 210)
    arrow(lines, 500, 335, 580, 335)
    arrow(lines, 680, 370, 680, 425)
    arrow(lines, 780, 210, 870, 335)
    arrow(lines, 780, 335, 870, 335)
    arrow(lines, 780, 460, 870, 335)
    arrow(lines, 1080, 335, 1160, 335)
    text(lines, 685, 555, "Final detection loss also includes classification loss and DFL; WIoU changes the bbox regression term.", "small")
    save(OUT / "module_wiou_loss.svg", lines)


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    overview()
    p2_branch()
    coord_attention()
    dyhead()
    wiou()


if __name__ == "__main__":
    build()
