import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).parent
OUT = HERE / "shots"; OUT.mkdir(exist_ok=True)
only = sys.argv[1:] or ["a", "b", "c", "d"]
with sync_playwright() as p:
    br = p.chromium.launch()
    for d in only:
        for name, w, h, dpr, clip_h in (("desktop", 1440, 1000, 1, 1900), ("390", 390, 844, 2, 2300)):
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr, color_scheme="dark")
            pg = ctx.new_page()
            pg.goto(f"file://{HERE}/{d}.html")
            total = pg.evaluate("document.documentElement.scrollHeight")
            sw = pg.evaluate("document.documentElement.scrollWidth")
            print(d, name, "page height", total, "scrollWidth", sw)
            if d == "c":
                pg.screenshot(path=OUT / f"{d}-{name}-top.png", clip={"x": 0, "y": 0, "width": w, "height": h if name == "desktop" else clip_h}, full_page=name != "desktop")
                idx = pg.evaluate("[...document.querySelectorAll('.it')].findIndex(x => x.querySelector('.n4'))")
                pg.goto(f"file://{HERE}/{d}.html?pick={idx}")
                pg.add_style_tag(content=".sech{position:static}")
                pg.evaluate("document.querySelector('.it.open').scrollIntoView({block: 'start'}); window.scrollBy(0, -160)")
                pg.screenshot(path=OUT / f"{d}-{name}-four.png")
                if name == "390":
                    y = pg.evaluate("document.querySelector('.it.open').getBoundingClientRect().top + scrollY")
                    pg.screenshot(path=OUT / f"{d}-{name}-four.png", full_page=True, clip={"x": 0, "y": y - 120, "width": w, "height": 1700})
            else:
                pg.screenshot(path=OUT / f"{d}-{name}-top.png", full_page=True, clip={"x": 0, "y": 0, "width": w, "height": clip_h})
                y = pg.evaluate("document.querySelector('.sec-same').getBoundingClientRect().top + scrollY")
                pg.screenshot(path=OUT / f"{d}-{name}-boundary.png", full_page=True, clip={"x": 0, "y": max(0, y - clip_h * 0.3), "width": w, "height": clip_h})
                pg.add_style_tag(content=".sech{position:static}")
                sel = ".grp:has(.row:nth-child(4))" if d == "a" else ".grp:has(.n4)"
                pg.locator(sel).first.screenshot(path=OUT / f"{d}-{name}-four.png")
                sel3 = ".grp:has(.row:nth-child(3)):not(:has(.row:nth-child(4)))" if d == "a" else ".grp:has(.n3)"
                pg.locator(sel3).first.screenshot(path=OUT / f"{d}-{name}-three.png")
            ctx.close()
    br.close()
