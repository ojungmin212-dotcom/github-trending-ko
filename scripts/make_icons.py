# -*- coding: utf-8 -*-
"""홈 화면·공유 미리보기용 PNG 아이콘 생성 (한 번 실행해 icons/ 에 커밋).

외부 패키지 없이 별 다각형을 스캔라인으로 칠하고(4×4 서브샘플 안티앨리어싱) PNG로 직접 인코딩한다.
디자인: 사이트 히어로의 별(--green #76b900)을 어두운 바탕(#0c0c0c) 위에.

실행: python scripts/make_icons.py
"""

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "icons"
BG = (12, 12, 12)          # --bg #0c0c0c
STAR = (118, 185, 0)       # --green #76b900
SS = 4                     # 픽셀당 서브샘플 (가로·세로)


def star_points(cx, cy, r_out, r_in):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def coverage_star(size, pts):
    """픽셀별 별 덮임 비율(0~1). 서브샘플 행마다 다각형과의 교차 구간을 구해 누적."""
    cov = [[0.0] * size for _ in range(size)]
    edges = list(zip(pts, pts[1:] + pts[:1]))
    step = 1.0 / SS
    for sy in range(size * SS):
        y = (sy + 0.5) * step
        xs = []
        for (x1, y1), (x2, y2) in edges:
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        row = cov[int(y)]
        for a, b in zip(xs[::2], xs[1::2]):
            # [a, b) 구간에 걸친 서브샘플 열을 센다
            for sx in range(max(0, math.ceil(a * SS - 0.5)), min(size * SS, math.ceil(b * SS - 0.5))):
                row[sx // SS] += 1.0 / (SS * SS)
    return cov


def coverage_round_rect(size, radius):
    cov = [[0.0] * size for _ in range(size)]
    for y in range(size):
        for x in range(size):
            hit = 0
            for sy in range(SS):
                for sx in range(SS):
                    px, py = x + (sx + 0.5) / SS, y + (sy + 0.5) / SS
                    dx = max(radius - px, 0, px - (size - radius))
                    dy = max(radius - py, 0, py - (size - radius))
                    hit += dx * dx + dy * dy <= radius * radius
            cov[y][x] = hit / (SS * SS)
    return cov


def png(size, pixels):
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in pixels)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render(size, star_scale, rounded):
    """star_scale: 별 바깥 반지름 / 아이콘 크기. rounded: 둥근 사각형 바탕(투명 모서리) 여부."""
    c = size / 2
    star = coverage_star(size, star_points(c, c * 1.04, size * star_scale, size * star_scale * 0.45))
    bg = coverage_round_rect(size, size * 0.22) if rounded else [[1.0] * size for _ in range(size)]
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            s = min(star[y][x], 1.0)
            col = tuple(round(BG[i] * (1 - s) + STAR[i] * s) for i in range(3))
            row.append(col + (round(255 * bg[y][x]),))
        pixels.append(row)
    return png(size, pixels)


def main():
    OUT.mkdir(exist_ok=True)
    targets = [
        ("icon-192.png", 192, 0.36, True),            # manifest "any"
        ("icon-512.png", 512, 0.36, True),            # manifest "any" · 공유 미리보기
        ("icon-maskable-512.png", 512, 0.28, False),  # manifest "maskable" (안전 영역 안쪽 80%에 별)
        ("apple-touch-icon.png", 180, 0.33, False),   # iOS 홈 화면 (iOS가 모서리를 직접 둥글게 함)
    ]
    for name, size, scale, rounded in targets:
        (OUT / name).write_bytes(render(size, scale, rounded))
        print(f"icons/{name} {size}px {(OUT / name).stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
