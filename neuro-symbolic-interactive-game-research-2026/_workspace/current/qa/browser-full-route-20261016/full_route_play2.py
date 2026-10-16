"""Real-browser full-route playability check v2 (local build only)."""
import http.server, functools, threading, re, json, time
from playwright.sync_api import sync_playwright

WEB = "/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/game-track/web"
PORT = 8904
SITES = {"spawn": (0.0, 2.0), "mira": (3.0, 11.0), "lens_pickup": (-11.0, 1.0),
         "lamp_mount": (7.0, 13.5), "tide_marks": (-8.5, 15.5)}

def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WEB)
    s = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def txt(pg, sel):
    try:
        return pg.text_content(sel) or ""
    except Exception:
        return ""

def log_has(pg, *needles):
    t = txt(pg, "#log")
    return all(n in t for n in needles)

def player_pos(pg):
    try:
        p = pg.evaluate("({x: window.__traceDashboard.player.x, z: window.__traceDashboard.player.z})")
        return (float(p["x"]), float(p["z"]))
    except Exception:
        return None

def focus(pg):
    m = re.search(r"Focused site:\s*(\S+)", txt(pg, "#map-focus"))
    return m.group(1).strip() if m else ""

VIA = {"lens_pickup": [(-5.0, 4.2), (-8.8, 4.0), (-10.3, 2.5)]}

def walk_to(pg, cv, target, timeout_s=200):
    legs = [(tx, tz) for (tx, tz) in VIA.get(target, [])] + [SITES[target]]
    for (tx, tz) in legs:
        if not _walk_leg(pg, cv, target, tx, tz, timeout_s if len(legs) == 1 else 90):
            return False
    return True

def _walk_leg(pg, cv, target, tx, tz, timeout_s):
    t0 = time.time()
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if focus(pg) == target:
            return True
        p = player_pos(pg)
        if p is None:
            time.sleep(1.0)
            continue
        dx, dz = tx - p[0], tz - p[1]
        if abs(dx) + abs(dz) < 1.6:
            time.sleep(0.8)
            return True
        cv.click()
        time.sleep(0.12)
        if int(time.time() - t0) % 15 == 0:
            print(f"  {target} {tx},{tz}: pos=({p[0]:.1f},{p[1]:.1f}) focus={focus(pg)}", flush=True)
        keys = []
        if dz > 0.5: keys.append("s")
        elif dz < -0.5: keys.append("w")
        if dx > 0.5: keys.append("d")
        elif dx < -0.5: keys.append("a")
        for k in keys or ["s"]:
            pg.keyboard.down(k)
        time.sleep(0.45)
        for k in ("w", "a", "s", "d"):
            pg.keyboard.up(k)
    return focus(pg) == target




def focus_scene(pg, box):
    """Click the 3D view (upper canvas area), never ledger fields, so keys reach the game."""
    pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.22)
    time.sleep(0.3)

def card_open(pg):
    t = txt(pg, "#log")
    shown = len(re.findall(r'coach_card\s+\{"card_id":"[^"]+","phase":"shown"\}', t))
    dism = len(re.findall(r'coach_card\s+\{"card_id":"[^"]+","phase":"dismissed"\}', t))
    return shown > dism

def dismiss_cards(pg, cv, rounds=5):
    """Dismiss coach cards via focused [OK] (Enter). Focus stays on OK while a card is open."""
    for _ in range(rounds):
        if not card_open(pg):
            return
        cv.press("Enter")
        time.sleep(1.2)


def main():
    serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.goto(f"http://127.0.0.1:{PORT}/dashboard/", wait_until="domcontentloaded")
        pg.wait_for_function("() => Boolean(window.__traceDashboard)", timeout=30000)
        time.sleep(20)
        frame = pg.frames[1]
        cv = frame.locator("canvas")
        box = pg.locator("#game").bounding_box()
        cx = box["x"] + box["width"] / 2
        begin_y = box["y"] + box["height"] * 0.62
        start_y = box["y"] + box["height"] * 0.78
        end_x = box["x"] + box["width"] * 0.74
        pg.mouse.click(cx, box["y"] + box["height"] / 2)
        time.sleep(5)
        pg.mouse.click(cx, begin_y)  # BEGIN INVESTIGATION
        time.sleep(5)
        # START CASE button bottom-right; Enter also works (focused). Try Enter first.
        cv.press("Escape")
        time.sleep(2)
        pg.mouse.click(end_x, start_y)  # START CASE direct click fallback
        time.sleep(2)
        pg.screenshot(path="/tmp/v2-afterstart.png")
        print("quest:", txt(pg, "#quest-objective")[:100], flush=True)

        def step(name, ok, extra=""):
            print(f"{'PASS' if ok else 'FAIL'} {name} {extra}", flush=True)
            if not ok:
                pg.screenshot(path=f"/tmp/v2-{name}.png")
                raise SystemExit(f"FAILED {name}")

        # verify folio closed by checking movement works
        p0 = player_pos(pg)
        cv.click(); time.sleep(0.2)
        pg.keyboard.down("w"); time.sleep(2); pg.keyboard.up("w"); time.sleep(1)
        p1 = player_pos(pg)
        moved = p0 and p1 and (abs(p1[0]-p0[0]) + abs(p1[1]-p0[1]) > 0.3)
        step("move-unlocked", moved, f"{p0} -> {p1}")

        step("walk-mira", walk_to(pg, cv, "mira"), f"focus={focus(pg)}")
        cv.click(); time.sleep(0.3)
        cv.press("e"); time.sleep(2.5)
        step("mira-dialogue", log_has(pg, "dialogue"), "")
        cv.press("1"); time.sleep(2.0)
        step("numkey-1", log_has(pg, "ask_lighthouse") or "choice" in txt(pg, "#log"), "")
        cv.press("2"); time.sleep(2.0)
        step("choice-2-hold", txt(pg, "#kpi-holds").strip() not in ("", "0", "—"), txt(pg, "#kpi-holds").strip())
        dismiss_cards(pg, cv)
        cv.press("4"); time.sleep(1.5)
        step("walk-lens", walk_to(pg, cv, "lens_pickup"), f"focus={focus(pg)}")
        dismiss_cards(pg, cv)
        focus_scene(pg, box); cv.press("e"); time.sleep(2.5)
        step("commit-lens", txt(pg, "#kpi-commits").strip() == "1", txt(pg, "#kpi-commits").strip())
        step("walk-mount", walk_to(pg, cv, "lamp_mount"), f"focus={focus(pg)}")
        dismiss_cards(pg, cv)
        focus_scene(pg, box); cv.press("e"); time.sleep(2.5)
        step("commit-mount", txt(pg, "#kpi-commits").strip() == "2", txt(pg, "#kpi-commits").strip())
        step("walk-mira2", walk_to(pg, cv, "mira"), f"focus={focus(pg)}")
        dismiss_cards(pg, cv)
        focus_scene(pg, box); cv.press("e"); time.sleep(2.0)
        pg.screenshot(path="/tmp/v2-mira2.png")
        print("mira2 log tail:", (txt(pg, "#log") or "")[-400:], flush=True)
        for _ in range(3):
            dismiss_cards(pg, cv, rounds=2)
            cv.press("3"); time.sleep(3.0)
            if txt(pg, "#kpi-commits").strip() == "3":
                break
        print("post-3 holds:", txt(pg, "#kpi-holds").strip(), flush=True)
        print("post-3 log tail:", (txt(pg, "#log") or "")[-500:], flush=True)
        pg.screenshot(path="/tmp/v2-commit-tide.png")
        step("commit-tide", txt(pg, "#kpi-commits").strip() == "3", txt(pg, "#kpi-commits").strip())
        dismiss_cards(pg, cv)
        cv.press("4"); time.sleep(1.5)
        step("walk-tide", walk_to(pg, cv, "tide_marks"), f"focus={focus(pg)}")
        dismiss_cards(pg, cv)
        focus_scene(pg, box); cv.press("e"); time.sleep(2.5)
        step("deduction-open", log_has(pg, "deduction"), "")
        pg.screenshot(path="/tmp/v2-deduction.png")
        print("FINAL", txt(pg, "#kpi-commits").strip(), txt(pg, "#kpi-episode").strip(), flush=True)
        b.close()
    print("FULL-ROUTE-BROWSER PASS", flush=True)

main()
