"""Static mockups for #210: three directions on the 74-group sanitised envelope.

Reads envelope.json (the unmodified server's /api/report for the tracked
sanitised armor fixture) and writes a.html, b.html, c.html.  No inline style
attributes are used, as the server CSP would drop them.
"""
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
env = json.loads((HERE / "envelope.json").read_text())
section = next(s for s in env["snapshot"]["sections"] if s.get("armor"))
decisions = {d["id"]: d for d in section["decisions"]}
EXACT = section["armor"]["exact_duplicate_groups"]
SAME = section["armor"]["same_stat_groups"]

# Mock-only verdict overlay so pressed states are visible (the envelope has none).
VERDICTS = {
    EXACT[0]["members"][1]["id"]: "approved",
    SAME[1]["members"][0]["id"]: "vetoed",
    SAME[2]["members"][1]["id"]: "approved",
}

e = html.escape
ROLE = {30: "primary", 25: "secondary", 20: "tertiary"}
DISP = {
    "preferred_survivor": "Preferred survivor",
    "retained_protected": "Retained, protected",
    "proposed_junk": "Proposed junk",
    "proposed_review": "Proposed review",
}
VLABEL = {"": "Unreviewed", "approved": "Approved", "vetoed": "Vetoed"}


def val(text, unknown=False):
    return f'<span class="unk">{e(text)}</span>' if unknown else e(text)


def cat(v):
    return ("none", True) if v == "" else (v, False)


def yes(v):
    return ("Yes" if v else "No", False)


def num(v):
    return ("unknown", True) if v is None else (str(v), False)


def prot(m):
    if not m["protection_level"]:
        return ("none", True)
    r = m["protection_reason"]
    return (f'{m["protection_level"]} — {r}' if r else m["protection_level"], False)


def slot(v):
    return (v, True) if v == "none/unknown" else cat(v)


COMMON = [
    ("protection", "Protection", prot),
    ("in_loadout", "In loadout", lambda m: yes(m["in_loadout"])),
    ("equipped", "Equipped", lambda m: yes(m["equipped"])),
    ("locked", "Locked", lambda m: yes(m["locked"])),
    ("masterwork_tier", "Masterwork tier", lambda m: num(m["masterwork_tier"])),
    ("power", "Power", lambda m: num(m["power"])),
]
SAME_FIELDS = [
    ("tuning_mod_slot", "Tuning Mod Slot", lambda m: slot(m["tuning_mod_slot"])),
    ("tuning_stat", "Tuning Stat", lambda m: cat(m["tuning_stat"])),
    ("seasonal_mod", "Seasonal Mod", lambda m: cat(m["seasonal_mod"])),
    ("holofoil", "Holofoil", lambda m: cat(m["holofoil"])),
] + COMMON


def view(group, kind):
    fields = COMMON if kind == "exact" else SAME_FIELDS
    members = []
    for i, m in enumerate(group["members"], 1):
        d = decisions.get(m["id"])
        if kind == "exact":
            status = DISP.get(m["disposition"], m["disposition"])
            controls = bool(d) and m["proposal_action"] == d["action"] and m["disposition"] == f'proposed_{d["action"]}'
            keep = m["disposition"] == "preferred_survivor"
        else:
            status = f'Existing proposal: {d["action"]}' if d else "Comparison only"
            controls = bool(d) and d["action"] in ("junk", "review")
            keep = False
        members.append({
            "n": i, "id": m["id"], "loc": m["location"] or "unknown", "status": status,
            "cells": {k: f(m) for k, _, f in fields}, "d": d, "controls": controls,
            "keep": keep, "verdict": VERDICTS.get(m["id"], ""),
        })
    shared, differing = [], []
    for k, label, _ in fields:
        texts = {m["cells"][k][0] for m in members}
        if len(texts) > 1 or k == "tuning_mod_slot":
            differing.append((k, label))
        else:
            shared.append((label, members[0]["cells"][k]))
    if kind == "exact":
        extra = [("Tuning Mod Slot", slot(group["tuning_mod_slot"]))]
        if group["spirit_signature"]:
            extra.append(("Spirit signature", (" · ".join(group["spirit_signature"]), False)))
        shared = extra + shared
    stats = sorted(group["stats"].items(), key=lambda kv: -kv[1])
    return {
        "kind": kind, "name": group["name"], "arch": group["item_archetype"], "type": group["type"],
        "cls": group["guardian_class"], "tier": group["tier"], "hash": group["hash"],
        "spike": [(n.capitalize(), v) for n, v in stats if v], "zero": [n.capitalize() for n, v in stats if not v],
        "stats": group["stats"], "members": members, "shared": shared, "differing": differing, "gid": group["group_id"],
    }


GROUPS = [view(g, "exact") for g in EXACT] + [view(g, "same") for g in SAME]
PIECES = sum(len(g["members"]) for g in GROUPS)

# ---------------------------------------------------------------- shared parts


def spike(g, compact=False):
    cells = "".join(
        f'<li class="sp s{v}"><span class="sv">{v}</span><span class="sn">{e(n)}</span>'
        f'<span class="sr">{ROLE[v]}</span></li>' for n, v in g["spike"]
    )
    zero = "" if compact else f'<p class="zero">0 in {e(", ".join(g["zero"]))}</p>'
    return f'<ul class="spike" aria-label="Base stats">{cells}</ul>{zero}'


def verdict(m):
    out = []
    for label, shows in (("Approve", "approved"), ("Veto", "vetoed"), ("Unset", "")):
        pressed = m["verdict"] == shows
        out.append(
            f'<button type="button" class="vb v-{label.lower()}" aria-pressed="{str(pressed).lower()}" '
            f'aria-label="{label} item {m["id"]}">{label}</button>'
        )
    return f'<div class="verdict" role="group" aria-label="Verdict for item {m["id"]}">{"".join(out)}</div>'


def status_pill(m):
    cls = "keep" if m["keep"] else ("prop" if m["d"] else "plain")
    return f'<span class="pill {cls}">{e(m["status"])}</span>'


def proposal(m):
    if not m["d"]:
        return ""
    reason = val(*cat(m["d"]["reason"]))
    return (f'<p class="why"><span class="k">Proposed</span> <b>{e(m["d"]["action"])}</b> '
            f'<span class="k">because</span> {reason}</p>')


def decision_cell(m):
    if not m["d"]:
        return '<p class="ro">No proposal. Nothing to decide.</p>'
    state = f'<p class="vs v-{m["verdict"] or "none"}">{VLABEL[m["verdict"]]}</p>'
    if m["controls"]:
        return verdict(m) + state
    return state + '<p class="ro">Read-only here. Decided on the Proposals page.</p>'


def shared_line(g):
    n = len(g["members"])
    if not g["shared"]:
        return ""
    items = "".join(f'<span class="sh"><span class="k">{e(l)}</span> {val(*c)}</span>' for l, c in g["shared"])
    lead = "Same on both" if n == 2 else f"Same on all {n}"
    return f'<p class="shared"><span class="lead">{lead}</span>{items}</p>'


def head(g):
    kind = '<span class="pill kind-exact">Exact</span>' if g["kind"] == "exact" else '<span class="pill kind-same">Review only</span>'
    n = len(g["members"])
    return (
        f'<header class="gh"><h4>{e(g["name"])}</h4>'
        f'<p class="meta"><span class="arch">{e(g["arch"])}</span>'
        f'<span>{e(g["type"])}</span><span>{e(g["cls"])}</span><span>Tier {g["tier"]}</span>'
        f'<span class="hash">Hash {e(g["hash"])}</span></p>'
        f'<p class="chips">{kind}<span class="count">{n} pieces</span></p></header>'
    )


def shell(title, direction, body, script="", rev=""):
    n_exact, n_same = len(EXACT), len(SAME)
    css = (HERE / "mock.css").read_text()
    return f"""<!doctype html>
<html lang="en" data-dir="{direction}"{rev}>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
<a class="skip" href="#vc-title">Skip to review content</a>
<main>
<header class="top">
  <div><h1 id="vc-title" tabindex="-1">Armor duplicates</h1>
  <p class="status" role="status">Connected. {len(GROUPS)} groups loaded from the armor export.</p></div>
  <div class="session" role="group" aria-label="Session">
    <button type="button" class="btn">Reload report</button>
    <button type="button" class="btn primary">Finalise review</button>
    <button type="button" class="btn">Reset session</button>
  </div>
</header>
<div class="filters">
  <div class="seg" role="group" aria-label="Show">
    <button type="button" aria-pressed="true">All <span>{len(GROUPS)}</span></button>
    <button type="button" aria-pressed="false">Exact <span>{n_exact}</span></button>
    <button type="button" aria-pressed="false">Same stats <span>{n_same}</span></button>
  </div>
  <label class="sel">Class <select><option>any class</option><option>Hunter</option><option>Titan</option><option>Warlock</option></select></label>
  <button type="button" class="btn quiet">Reset filters</button>
  <p class="scope" role="status">{len(GROUPS)} groups, {PIECES} pieces</p>
</div>
{body}
</main>
{script}
</html>
"""


def section_head(kind, count):
    if kind == "exact":
        h, rule = "Exact duplicates", "Same item, same stats, same tuning. One copy is kept."
    else:
        h, rule = "Same stats, different tuning", "Review only. No copy is preferred, because the tuning is yours to pick."
    return (f'<div class="sech"><h3>{h}</h3><p>{rule}</p>'
            f'<span class="count">{count} groups</span></div>')


def sections(render):
    out = []
    for kind, label in (("exact", "exact"), ("same", "same")):
        gs = [g for g in GROUPS if g["kind"] == kind]
        out.append(f'<section class="sec sec-{label}">{section_head(kind, len(gs))}'
                   f'<div class="groups">{"".join(render(g) for g in gs)}</div></section>')
    return "".join(out)


# ---------------------------------------------------------------- A: ledger


def a_group(g):
    k = len(g["differing"])
    cols = "".join(f'<span class="fh">{e(l)}</span>' for _, l in g["differing"])
    rows = []
    for m in g["members"]:
        cells = "".join(
            f'<span class="fc{" lead-axis" if key == "tuning_mod_slot" else ""}">'
            f'<span class="cl">{e(l)}</span>{val(*m["cells"][key])}</span>'
            for key, l in g["differing"]
        )
        rows.append(
            f'<li class="row{" kept" if m["keep"] else ""}">'
            f'<div class="who"><span class="pn">Piece {m["n"]}</span>{status_pill(m)}'
            f'<code>{m["id"]}</code><span class="loc">{e(m["loc"])}</span></div>'
            f'<div class="fields">{cells or "<span class=\"nodiff\">No difference between the pieces.</span>"}</div>'
            f'<div class="dec">{proposal(m)}{decision_cell(m)}</div></li>'
        )
    headrow = (f'<div class="row hrow" aria-hidden="true"><div class="who"></div>'
               f'<div class="fields">{cols}</div><div class="dec"></div></div>') if k else ""
    return (
        f'<article class="grp g-{g["kind"]}"><div class="idn">{head(g)}{spike(g)}</div>'
        f'<div class="pcs">{headrow}<ol>{"".join(rows)}</ol>{shared_line(g)}</div></article>'
    )


# ---------------------------------------------------------------- B: side by side


def matrix(g):
    rows = len(g["differing"]) + 3  # header, axes, proposal, verdict
    labels = ['<div class="ml corner"></div>']
    labels += [f'<div class="ml{" lead-axis" if key == "tuning_mod_slot" else ""}">{e(l)}</div>' for key, l in g["differing"]]
    labels += ['<div class="ml">Proposal</div>', '<div class="ml">Verdict</div>']
    cols = [f'<div class="mlab">{"".join(labels)}</div>']
    for m in g["members"]:
        cells = [
            f'<div class="mc mh"><span class="pn">Piece {m["n"]}</span>{status_pill(m)}'
            f'<code>{m["id"]}</code><span class="loc">{e(m["loc"])}</span></div>'
        ]
        for key, l in g["differing"]:
            cells.append(
                f'<div class="mc{" lead-axis" if key == "tuning_mod_slot" else ""}">'
                f'<span class="cl">{e(l)}</span>{val(*m["cells"][key])}</div>'
            )
        cells.append(f'<div class="mc"><span class="cl">Proposal</span>{proposal(m) or "<span class=\"unk\">none</span>"}</div>')
        cells.append(f'<div class="mc mv"><span class="cl">Verdict</span>{decision_cell(m)}</div>')
        cols.append(f'<div class="mem{" kept" if m["keep"] else ""}">{"".join(cells)}</div>')
    return f'<div class="mx r{rows} n{len(g["members"])}">{"".join(cols)}</div>'


def b_group(g):
    return (f'<article class="grp g-{g["kind"]}"><div class="idn">{head(g)}{spike(g)}</div>'
            f'{matrix(g)}{shared_line(g)}</article>')


# ---------------------------------------------------------------- C: index + inspector


def c_body():
    out = []
    for kind in ("exact", "same"):
        gs = [g for g in GROUPS if g["kind"] == kind]
        items = []
        for g in gs:
            todo = [m for m in g["members"] if m["controls"]]
            done = sum(1 for m in todo if m["verdict"])
            prog = f'{done} of {len(todo)} decided' if todo else "nothing to decide"
            sig = " ".join(f'<span class="sg">{e(n)} <b>{v}</b></span>' for n, v in g["spike"])
            items.append(
                f'<li class="it" data-gid="{g["kind"]}-{g["gid"]}">'
                f'<button type="button" class="ib" aria-expanded="false">'
                f'<span class="in">{e(g["name"])}</span>'
                f'<span class="ip">{len(g["members"])} pieces · {prog}</span>'
                f'<span class="im">{e(g["arch"])} · {e(g["type"])} · {e(g["cls"])}</span>'
                f'<span class="is">{sig}</span></button>'
                f'<div class="panel">{b_group(g)}</div></li>'
            )
        out.append(f'<section class="sec sec-{kind}">{section_head(kind, len(gs))}<ol class="index">{"".join(items)}</ol></section>')
    return f'<div class="md"><div class="list">{"".join(out)}</div><aside class="insp" aria-label="Selected group"></aside></div>'


C_SCRIPT = """<script>
const wide = matchMedia('(min-width: 900px)');
const insp = document.querySelector('.insp');
function pick(li) {
  document.querySelectorAll('.it').forEach((x) => {
    const on = x === li && !(x.classList.contains('open') && !wide.matches);
    x.classList.toggle('open', on);
    x.querySelector('.ib').setAttribute('aria-expanded', on);
  });
  if (wide.matches) insp.replaceChildren(li.querySelector('.panel > *').cloneNode(true));
}
document.querySelectorAll('.ib').forEach((b) => b.addEventListener('click', () => pick(b.parentElement)));
const want = new URLSearchParams(location.search).get('pick') || 0;
pick(document.querySelectorAll('.it')[+want]);
</script>"""


# ---------------------------------------------------------------- D: revised B

ORDER = ["health", "melee", "grenade", "super", "class", "weapons"]


def strip6(g):
    cells = []
    for name in ORDER:
        v = g["stats"][name]
        role = f'<span class="sr">{ROLE[v]}</span>' if v in ROLE else ""
        cells.append(f'<li class="s6 z{v}"><span class="sn">{name.capitalize()}</span>'
                     f'<span class="sv">{v}</span>{role}</li>')
    return f'<ul class="strip6" aria-label="Base stats">{"".join(cells)}</ul>'


def tuned(cell):
    text, unknown = cell
    marks = "".join(f'<i class="{"on" if n.capitalize() == text else ""}">{n[0].upper()}</i>' for n in ORDER)
    return f'<span class="ts" aria-hidden="true">{marks}</span><b class="tt">{val(text, unknown)}</b>'


def d_group(g):
    same_word = all(m["cells"]["tuning_stat"][0].capitalize() == m["cells"]["tuning_mod_slot"][0]
                    for m in g["members"]) if g["kind"] == "same" else False
    axes = [(k, l) for k, l in g["differing"] if not (same_word and k == "tuning_stat")]
    rows = len(axes) + 3
    labels = ['<div class="ml corner"></div>']
    labels += [f'<div class="ml{" lead-axis" if k == "tuning_mod_slot" else ""}">'
               f'{"Tuned stat" if k == "tuning_mod_slot" else e(l)}</div>' for k, l in axes]
    labels += ['<div class="ml">Proposal</div>', '<div class="ml">Verdict</div>']
    cols = [f'<div class="mlab">{"".join(labels)}</div>']
    for m in g["members"]:
        cells = [f'<div class="mc mh"><span class="pn">Piece {m["n"]}</span>{status_pill(m)}'
                 f'<span class="idloc"><code>{m["id"]}</code> <span class="loc">{e(m["loc"])}</span></span></div>']
        for k, l in axes:
            if k == "tuning_mod_slot":
                cells.append(f'<div class="mc tuned"><span class="cl">Tuned stat</span>{tuned(m["cells"][k])}</div>')
            else:
                cells.append(f'<div class="mc"><span class="cl">{e(l)}</span>{val(*m["cells"][k])}</div>')
        cells.append(f'<div class="mc"><span class="cl">Proposal</span>{proposal(m) or "<span class=\"unk\">none</span>"}</div>')
        cells.append(f'<div class="mc mv"><span class="cl">Verdict</span>{decision_cell(m)}</div>')
        cols.append(f'<div class="mem{" kept" if m["keep"] else ""}">{"".join(cells)}</div>')
    mx = f'<div class="mx r{rows} n{len(g["members"])}">{"".join(cols)}</div>'
    return (f'<article class="grp g-{g["kind"]}"><div class="idn">{head(g)}{strip6(g)}</div>'
            f'{mx}{shared_line(g)}</article>')


(HERE / "d.html").write_text(shell("D: Side by side, revised", "b", sections(d_group), rev=' data-rev="2"'))

(HERE / "a.html").write_text(shell("A: Ledger", "a", sections(a_group)))
(HERE / "b.html").write_text(shell("B: Side by side", "b", sections(b_group)))
(HERE / "c.html").write_text(shell("C: Index and inspector", "c", c_body(), C_SCRIPT))
print(len(GROUPS), "groups", PIECES, "pieces", sum(m["controls"] for g in GROUPS for m in g["members"]) * 3, "verdict buttons")
print("max rows", max(len(g["differing"]) + 3 for g in GROUPS), file=sys.stderr)
