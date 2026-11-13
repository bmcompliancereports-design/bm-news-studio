#!/usr/bin/env python3
"""
BM NEWS × Inquirer.net Editorial Card Engine
Improved Hybrid Edition for Batong Malake
Face-preserving only — GrabCut + alpha. No generative face edits.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

NAVY = "#012444"
DEEP_NAVY = "#011930"
PRIMARY = "#013567"
INQ_RIBBON_BLUE = "#024E8A"
INQ_SUBHEAD_GRAY = "#353538"
CYAN = "#1CB7D1"
PAPER = "#F4F5F6"
WHITE = "#FFFFFF"

ASPECTS = {
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "5:4": (1350, 1080),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
}

def parse_hex(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

def load_font(role: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = {
        "serif_italic": [
            "PlayfairDisplay-BoldItalic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
        ],
        "medium": [
            "Inter-Medium.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "bold": [
            "Inter-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "heavy": [
            "BarlowCondensed-Black.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        ],
        "semibold": [
            "Inter-SemiBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
    }
    for path in candidates.get(role, candidates["medium"]):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()

def extract_subject_cutout(photo_path: str | Path, monochrome: bool = False) -> Image.Image:
    """GrabCut + morphological refinement. Original pixels only. Upscale-friendly."""
    img = cv2.imread(str(photo_path))
    if img is None:
        raise FileNotFoundError(photo_path)
    h, w = img.shape[:2]
    # Upscale small images for better cutout quality
    if max(h, w) < 1200:
        scale = 1200 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        h, w = img.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    rect = (int(w * 0.03), int(h * 0.03), int(w * 0.94), int(h * 0.94))
    cv2.grabCut(img, mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel, iterations=1)
    alpha = (mask2 * 255).astype(np.uint8)
    if monochrome:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        b, g, r = cv2.split(gray)
    else:
        b, g, r = cv2.split(img)
    rgba = cv2.merge((r, g, b, alpha))
    return Image.fromarray(rgba)

class EditorialCanvas:
    def __init__(self, aspect: str = "1:1", scale: int = 2):
        self.aspect = aspect
        self.w, self.h = ASPECTS.get(aspect, (1080, 1080))
        self.scale = scale
        self.image = Image.new("RGBA", (self.w * scale, self.h * scale), (*parse_hex(DEEP_NAVY), 255))
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = {}

    def p(self, v: float) -> int:
        return round(v * self.scale)

    def font(self, role: str, size: float):
        px = max(1, self.p(size))
        key = (role, px)
        if key not in self.fonts:
            self.fonts[key] = load_font(role, px)
        return self.fonts[key]

    def measure(self, text: str, role: str, size: float) -> float:
        return self.draw.textlength(text, font=self.font(role, size)) / self.scale

    def text(self, x, y, text, size, color=WHITE, role="medium", anchor="lt"):
        if text:
            self.draw.text((self.p(x), self.p(y)), text, fill=color, font=self.font(role, size), anchor=anchor)

    def rect(self, x, y, w, h, fill=None, radius=0):
        xy = (self.p(x), self.p(y), self.p(x + w), self.p(y + h))
        if radius > 0:
            self.draw.rounded_rectangle(xy, radius=self.p(radius), fill=fill)
        else:
            self.draw.rectangle(xy, fill=fill)

    def line(self, x0, y0, x1, y1, color, width=0.8):
        self.draw.line(
            (self.p(x0), self.p(y0), self.p(x1), self.p(y1)),
            fill=color,
            width=max(1, round(width * self.scale)),
        )

    def vertical_scrim(self, x, y, w, h, a_top, a_bot, color):
        overlay = Image.new("RGBA", (self.p(w), self.p(h)), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        r, g, b = parse_hex(color)
        for i in range(self.p(h)):
            t = i / max(1, self.p(h) - 1)
            a = int(255 * (a_top + (a_bot - a_top) * t))
            od.line([(0, i), (self.p(w), i)], fill=(r, g, b, a))
        self.image.alpha_composite(overlay, (self.p(x), self.p(y)))
        self.draw = ImageDraw.Draw(self.image)

    def duotone_bg(self, bg_path, dark="#011A36", mid="#053A68", light="#4A90C2",
                   top_scrim=0.80, bot_scrim=0.88, corner_folds=True):
        with Image.open(bg_path) as raw:
            im = ImageOps.exif_transpose(raw).convert("RGB")
        fitted = ImageOps.fit(
            im,
            (self.image.width, self.image.height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.38),
        )
        gray = ImageOps.autocontrast(ImageOps.grayscale(fitted), cutoff=1)
        duo = ImageOps.colorize(gray, black=dark, mid=mid, white=light).convert("RGBA")
        self.image = duo
        self.draw = ImageDraw.Draw(self.image)
        if top_scrim > 0:
            self.vertical_scrim(0, 0, self.w, self.h * 0.52, top_scrim, 0.08, "#011F3E")
        if bot_scrim > 0:
            self.vertical_scrim(0, self.h * 0.58, self.w, self.h * 0.42, 0.04, bot_scrim, "#011830")
        if corner_folds:
            overlay = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.polygon([(0, 0), (self.p(250), 0), (0, self.p(310))], fill=(*parse_hex("#014E9E"), 145))
            od.polygon(
                [(self.p(self.w - 210), 0), (self.p(self.w), 0), (self.p(self.w), self.p(270))],
                fill=(*parse_hex("#014E9E"), 120),
            )
            od.polygon(
                [(self.p(self.w), self.p(self.h)), (self.p(self.w - 290), self.p(self.h)),
                 (self.p(self.w), self.p(self.h - 230))],
                fill=(*parse_hex("#013567"), 150),
            )
            self.image.alpha_composite(overlay)
            self.draw = ImageDraw.Draw(self.image)

    def draw_ribbons(self, x, y, lines, subheadline, headline_size=46, sub_size=13.5, align="left", max_w=900):
        cur_y = y
        pad_x, pad_y, gap = 15, 4, 4
        line_h = math.ceil(headline_size * 1.10) + pad_y * 2
        for line in lines:
            tw = self.measure(line, "serif_italic", headline_size)
            bw = tw + pad_x * 2
            bx = x if align == "left" else x + (max_w - bw) / 2
            self.rect(bx, cur_y, bw, line_h, fill=INQ_RIBBON_BLUE, radius=1)
            self.text(bx + pad_x, cur_y + pad_y - headline_size * 0.04, line, headline_size, WHITE, "serif_italic")
            cur_y += line_h + gap
        if subheadline:
            stxt = subheadline.upper()
            stw = self.measure(stxt, "semibold", sub_size)
            sbw = stw + 26
            sbh = 26
            sbx = x if align == "left" else x + (max_w - sbw) / 2
            cur_y += 5
            self.line(sbx, cur_y, sbx + sbw, cur_y, "#C8D6E2", 0.8)
            self.rect(sbx, cur_y + 2.5, sbw, sbh, fill=INQ_SUBHEAD_GRAY)
            self.text(sbx + sbw / 2, cur_y + 2.5 + sbh / 2, stxt, sub_size, WHITE, "semibold", "mm")
            self.line(sbx, cur_y + 2.5 + sbh + 2.5, sbx + sbw, cur_y + 2.5 + sbh + 2.5, "#C8D6E2", 0.8)
            cur_y += sbh + 10
        return cur_y

    def draw_body(self, x, y, text, max_w, size=18.5, align="left"):
        cur_y = y
        self.line(x, cur_y, x + max_w, cur_y, "#6EA2CC", 0.8)
        cx = x + max_w / 2 if align == "center" else x + 34
        self.rect(cx - 16, cur_y - 1.5, 32, 3.5, fill=WHITE)
        cur_y += 14
        words = text.split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if self.measure(test, "medium", size) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        lh = round(size * 1.32)
        for line in lines:
            if align == "center":
                self.text(x + max_w / 2, cur_y, line, size, "#F0F6FC", "medium", "mt")
            else:
                self.text(x, cur_y, line, size, "#F0F6FC", "medium")
            cur_y += lh
        return cur_y

    def paste_cutout(self, cutout: Image.Image, x, y, w, h, drop_shadow=True):
        fitted = ImageOps.fit(cutout, (self.p(w), self.p(h)), method=Image.Resampling.LANCZOS, centering=(0.5, 0.08))
        if drop_shadow:
            shadow = fitted.copy()
            shadow.putalpha(ImageEnhance.Brightness(shadow.getchannel("A")).enhance(0.48))
            shadow = shadow.filter(ImageFilter.GaussianBlur(self.p(14)))
            self.image.alpha_composite(shadow, (self.p(x) + self.p(5), self.p(y) + self.p(11)))
        self.image.alpha_composite(fitted, (self.p(x), self.p(y)))
        self.draw = ImageDraw.Draw(self.image)

    def top_bar(self, kicker, num, total):
        y = 34
        self.rect(50, y, 5, 20, fill=CYAN)
        self.text(64, y + 10, kicker.upper(), 13.5, WHITE, "bold", "lm")
        kw = self.measure(kicker.upper(), "bold", 13.5)
        self.line(64 + kw + 14, y + 10, self.w - 130, y + 10, "#79A9CF", 0.8)
        self.text(self.w - 50, y + 10, f"{num:02d} / {total:02d}", 13.5, CYAN, "heavy", "rm")
        return y + 32

    def footer(self, num, total, source="BM NEWS"):
        y_top = self.h - 68
        self.vertical_scrim(0, self.h - 115, self.w, 115, 0, 0.92, DEEP_NAVY)
        self.line(50, y_top, self.w - 50, y_top, "#5588B0", 0.8)
        self.rect(50, y_top + 10, 4, 32, fill=CYAN)
        self.text(64, y_top + 10, "BM NEWS · BATONG MALAKE", 17, WHITE, "heavy")
        self.text(64, y_top + 32, f"CARD {num:02d} OF {total:02d}", 10.5, "#9BC4DF", "medium")
        self.text(self.w - 50, y_top + 12, source.upper(), 11.5, WHITE, "semibold", "rt")
        self.text(self.w - 50, y_top + 30, "SANGGUNIANG BARANGAY NG BATONG MALAKE", 9.5, "#8AB4D0", "medium", "rt")

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        final = self.image.convert("RGB").resize((self.w, self.h), Image.Resampling.LANCZOS)
        final.save(path, "PNG", compress_level=6)
        return path

def render_card(
    photo_path: str,
    kicker: str,
    headlines: list[str],
    subheadline: str,
    body: str,
    aspect: str = "1:1",
    style: str = "hybrid_cover",
    monochrome: bool = False,
    slide_num: int = 1,
    slide_total: int = 1,
    source: str = "BM NEWS",
    output_path: str = "card.png",
) -> str:
    cutout = extract_subject_cutout(photo_path, monochrome=monochrome)
    c = EditorialCanvas(aspect=aspect, scale=2)
    c.duotone_bg(
        photo_path,
        dark="#011A36",
        mid="#053A68",
        light="#4A90C2",
        top_scrim=0.82,
        bot_scrim=0.90,
        corner_folds=(style == "hybrid_cover"),
    )
    y = c.top_bar(kicker, slide_num, slide_total)

    if style == "hybrid_cover":
        hsize = 50 if aspect in ("1:1", "4:5") else 42
        y = c.draw_ribbons(52, y + 6, headlines, subheadline, headline_size=hsize, sub_size=13.5, max_w=c.w - 104)
        y = c.draw_body(52, y + 4, body, c.w - 104, size=18.5)
        cut_y = max(y + 8, c.h * 0.42)
        c.line(52, cut_y + 36, c.w - 52, cut_y + 36, "#4A82B0", 0.8)
        c.paste_cutout(cutout, 40, cut_y, c.w - 80, c.h - cut_y - 62, drop_shadow=True)
    elif style == "quotation":
        y = c.draw_ribbons(52, y + 10, headlines, subheadline, headline_size=40, max_w=c.w - 104)
        c.paste_cutout(cutout, 70, y + 16, c.w - 140, c.h - y - 85)
    elif style == "formal_statement":
        impact = headlines[0] if headlines else "WE DESERVE BETTER"
        c.text(52, y + 16, impact, 62, WHITE, "heavy")
        y = y + 92
        c.draw_body(52, y, body, c.w - 104, size=20)
    else:
        y = c.draw_ribbons(52, y + 6, headlines, subheadline, headline_size=28, sub_size=12, max_w=c.w - 104)
        y = c.draw_body(52, y + 4, body, c.w - 104, size=17.5)
        cut_y = max(y + 8, c.h * 0.40)
        c.paste_cutout(cutout, 50, cut_y, c.w - 100, c.h - cut_y - 60)

    c.footer(slide_num, slide_total, source)
    return str(c.save(Path(output_path)))
