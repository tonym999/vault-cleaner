# Issue #206 evidence: Svelte 5 + TypeScript + Vite review frontend

Verbatim transcripts for the experiments behind
[docs/frontend-framework-decision.md](../../frontend-framework-decision.md).
Each `bash` fence is one command, run from the repository root, and the
`text` fence under it is that command's complete output, with terminal colour
codes removed. The emission order for each capture generation is stated below.
One fence has one further edit, stated above it; nothing else was edited.

S1 to S14 use the synthetic fixtures under `tests/fixtures/`. S15 uses only
the tracked sanitised armor fixture
`tests/fixtures/real/2026-09-01T-current/armor.csv`, without an overlay.
No unsanitised export or file under `data/` was read. The proof code is in
[spikes/issue-206/](../../../spikes/issue-206/README.md).

Captured 2026-10-04 on the implementation branch for #206, and captured
again in full after fix round 1 changed the slice and the proofs. After the
capture every proof fence was rerun and compared with the text recorded
here; only the S10 timings differed. Two kinds of line are not repeatable
and are named where they occur: durations and timestamps printed by npm,
Vite, vitest and svelte-check; and the timings in S10. Amendment 4 reran every proof. S1 to S8 and S11
were unchanged; S9 (CSS bytes), S10 (sizes/timings/check summary), S12
(line counts), S13 (settled contrast), and S14 (prose check output omits its
informational machine ERROR lines) are recaptured below. S14 still verifies
the incomplete changes fail their checks; its script is unchanged. S15 and
the frontend fence are new captures. These new and recaptured fences merge
stderr into stdout in process emission order. The earlier unchanged captures keep their original
stdout-then-stderr order. S15 timing numbers vary between runs;
counts and pass results must remain. Fix round 3 recaptured frontend, source,
S9, S10, S12, S13 and S15 after correcting the focus floor, in merged process
emission order; all other proof transcripts were unchanged. The proof captures print no runtime port,
absolute checkout or temporary path, or session token; repository-relative
fixture, screenshot and source-citation paths are included.

Ids such as `6032` and `8201` in the transcripts are the fake instance ids in
the committed fixtures. `18446744073709551615`, `007` and `9"<'> x` are the
hostile ids experiment S2 substitutes. `Spirit of the Fixture`, `Spirit of
the Proof`, `Spirit of the Twin` and `Fake Seasonal Mod` are the values
experiment S1 overlays.

## Screenshots

Written by `proof_s6_layout.py --screenshots`, from the synthetic fixtures,
each with one veto recorded. All six were regenerated after S15 changed
two contrast colours. The sanitised screenshots are written by
`proof_s15_scale.py --screenshots`, with an approval on the final group.
Each of those four is only the **top 2,400 px** of the page (the first
groups), not the whole report: a full-page capture of all 74 groups was about
7 MB per image (page heights about 61,000 px at desktop and 101,000 px at
390 px) and was removed for size. The checks S15 runs still cover every
group; the approved final group is not in the image. Every displayed fixture
id carries the sanitised `1000` prefix.

| File | Fixture | Width | Scheme |
| --- | --- | --- | --- |
| [both-kinds-desktop-light.png](both-kinds-desktop-light.png) | `armor_close.csv` | 1440 px | light |
| [both-kinds-desktop-dark.png](both-kinds-desktop-dark.png) | `armor_close.csv` | 1440 px | dark |
| [both-kinds-narrow-light.png](both-kinds-narrow-light.png) | `armor_close.csv` | 390 px | light |
| [both-kinds-narrow-dark.png](both-kinds-narrow-dark.png) | `armor_close.csv` | 390 px | dark |
| [four-members-desktop-light.png](four-members-desktop-light.png) | `armor_same_stat_four_ui.csv` | 1440 px | light |
| [four-members-narrow-light.png](four-members-narrow-light.png) | `armor_same_stat_four_ui.csv` | 390 px | light |
| [real-desktop-light.png](real-desktop-light.png) | sanitised armor, top 2,400 px | 1440 px | light |
| [real-desktop-dark.png](real-desktop-dark.png) | sanitised armor, top 2,400 px | 1440 px | dark |
| [real-narrow-light.png](real-narrow-light.png) | sanitised armor, top 2,400 px | 390 px | light |
| [real-narrow-dark.png](real-narrow-dark.png) | sanitised armor, top 2,400 px | 390 px | dark |

## Environment

The interpreter, libraries, Node toolchain and browser every transcript below was produced with.

```bash
.venv/bin/python - <<'EOF'
import importlib.metadata as metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

print(platform.system(), "Python", sys.version.split()[0])
for name in ("flask", "werkzeug", "playwright"):
    print(name, metadata.version(name))
print("node", subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip())
print("npm", subprocess.run(["npm", "--version"], capture_output=True, text=True).stdout.strip())
modules = Path("spikes/issue-206/frontend/node_modules")
for name in ("svelte", "vite", "typescript", "@sveltejs/vite-plugin-svelte", "svelte-check",
             "vitest", "tailwindcss", "@tailwindcss/vite", "daisyui", "axe-core"):
    print(name, json.loads((modules / name / "package.json").read_text())["version"])
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    print("chromium", browser.version, "(headless)")
    browser.close()
EOF
```

Output:

```text
Linux Python 3.14.4
flask 3.1.3
werkzeug 3.1.8
playwright 1.62.0
node v24.20.0
npm 12.0.2
svelte 5.57.1
vite 8.3.2
typescript 6.0.3
@sveltejs/vite-plugin-svelte 7.3.1
svelte-check 4.7.6
vitest 5.0.3
tailwindcss 4.3.3
@tailwindcss/vite 4.3.3
daisyui 5.7.47
axe-core 4.13.0
chromium 151.0.7922.34 (headless)
```

## Frontend: install, type check, unit tests, build

From a clean `npm ci`. The timestamps, durations and the `npm notice` lines vary from run to run; the counts and sizes do not (`dist/modules.json` holds paths relative to the frontend directory, so its size does not depend on where the checkout is). This capture is edited in one respect, so it is not strictly verbatim: svelte-check and vitest print the checkout's absolute directory, and that prefix is replaced with `<repo>` in two lines.

```bash
(cd spikes/issue-206/frontend && npm ci && npm run check && npm test && npm run build)
```

Output:

```text

added 76 packages, and audited 77 packages in 1s

18 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
npm notice run vault-cleaner-spike-206-frontend@0.0.0 check
npm notice run svelte-check --tsconfig ./tsconfig.json --fail-on-warnings
Loading svelte-check in workspace: <repo>/spikes/issue-206/frontend
Getting Svelte diagnostics...

svelte-check found 0 errors and 0 warnings
npm notice run vault-cleaner-spike-206-frontend@0.0.0 test
npm notice run vitest run

 RUN  v5.0.3 <repo>/spikes/issue-206/frontend


 Test Files  3 passed (3)
      Tests  32 passed (32)
   Start at  17:02:00
   Duration  567ms (transform 78%, import 16%, tests 5%, worker 1%)

npm notice run vault-cleaner-spike-206-frontend@0.0.0 build
npm notice run vite build
vite v8.3.2 building client environment for production...
transforming...
/*! 🌼 daisyUI 5.7.47 */
✓ 121 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html       0.43 kB │ gzip:  0.28 kB
dist/modules.json     3.59 kB │ gzip:  0.57 kB
dist/assets/app.css  57.02 kB │ gzip:  9.90 kB
dist/assets/app.js   63.44 kB │ gzip: 23.09 kB

✓ built in 352ms
```

## Probes: install and build

The S7 probe pages. Durations vary.

```bash
(cd spikes/issue-206/probes && rm -rf node_modules dist && npm ci && npm run build)
```

Output:

```text

added 132 packages, and audited 133 packages in 8s

17 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
vite v8.3.2 building client environment for production...
transforming...
/*! 🌼 daisyUI 5.7.47 */
✓ 1531 modules transformed.
rendering chunks...
computing gzip size...
dist/daisy.html                          0.45 kB │ gzip:  0.27 kB
dist/plain.html                          0.45 kB │ gzip:  0.27 kB
dist/shadcn.html                         0.45 kB │ gzip:  0.27 kB
dist/skeleton.html                       0.48 kB │ gzip:  0.29 kB
dist/assets/plain.css                    0.11 kB │ gzip:  0.12 kB
dist/assets/shadcn.css                  31.69 kB │ gzip:  6.42 kB
dist/assets/daisy.css                   61.37 kB │ gzip: 10.52 kB
dist/assets/skeleton.css               143.24 kB │ gzip: 15.27 kB
dist/assets/daisy.js                     1.07 kB │ gzip:  0.60 kB
dist/assets/plain.js                     2.50 kB │ gzip:  1.22 kB
dist/assets/chunk-disclose-version.js   53.52 kB │ gzip: 20.58 kB
dist/assets/skeleton.js                 65.69 kB │ gzip: 20.75 kB
dist/assets/shadcn.js                  203.15 kB │ gzip: 61.03 kB

✓ built in 1.86s
npm notice run vault-cleaner-spike-206-probes@0.0.0 build
npm notice run vite build
```

## Source rules (gates H2, H8)

The plan's source rules, the list of every direct DOM access in the shipped source with its reason, and what the build output references.

```bash
.venv/bin/python spikes/issue-206/check_source.py
```

Output:

```text
shipped source files scanned: 15; test and contract files: 4
raw HTML: 0
code from strings: 0
numeric conversion: 0
hand-written inline style: 0
remote URL: 0
id and hash fields declared in envelope.ts: 9, all string: True
-- direct DOM access and effects in shipped source --
App.svelte:28 $effect: focus policy on a report change (the slice's only effects: one before, one after the DOM change)
App.svelte:30 document.activeElement: focus policy: has focus fallen to <body>?
App.svelte:32 $effect: focus policy on a report change (the slice's only effects: one before, one after the DOM change)
App.svelte:34 document.activeElement: focus policy: has focus fallen to <body>?
App.svelte:34 document.body: focus policy: has focus fallen to <body>?
App.svelte:34 .focus(: focus policy: move focus to the list heading
App.svelte:78 bind:this: focus policy: the list, and its heading to focus
App.svelte:81 bind:this: focus policy: the list, and its heading to focus
main.ts:8 document.getElementById: the mount point, once at start-up
-- ordering computed in the browser --
lib/filters.ts:60 .sort(([left], [right]) => left.localeCompare(right, 'en', { sensitivity: 'base' }))
-- build output --
assets/app.css: 57022 bytes; URL strings 2 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: ['--fx-noise:url("data:image/svg+xml']; @import/@font-face/remote url(): []
  the one data: URI is daisyUI's --fx-noise definition; the same file overrides it with --fx-noise:none: True
assets/app.js: 63440 bytes; URL strings 15 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
index.html: 439 bytes; URL strings 0 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
index.html inline scripts, style elements, style or event attributes: []
RESULT: PASS
```

## Contract samples are current (gate H9)

The committed envelope samples equal what the server returns today.

```bash
.venv/bin/python spikes/issue-206/contract.py --check
```

Output:

```text
RESULT: PASS
```

## S1: information parity (gate H1)

Every item under the plan's *Required information*, for four fixtures, without and with verdicts, at 1440 and 390 px; three group values no fixture carries, overlaid in memory on the server's answer; the filter sequences of #137's E10 beside the production page; a negative control.

```bash
.venv/bin/python spikes/issue-206/proof_s1_parity.py
```

Output:

```text
-- every required value, for four fixtures, without and with verdicts --
armor_close.csv unreviewed at 1440px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv unreviewed at 390px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 1440px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 390px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 1440px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 390px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 1440px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 390px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
-- group values no fixture has, overlaid in memory on the server's answer --
exact:6031 shows: {'spirit_signature': 'Spirit of the Fixture · Spirit of the Proof', 'seasonal_mod': 'Fake Seasonal Mod', 'holofoil': 'true'}
same_stat:6081 shows: {'spirit_signature': 'Spirit of the Twin'}
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 1440px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 390px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
-- filters: the slice beside the production page, same session --
no filter: equal to production=True; groups=['exact_duplicate:6031', 'same_stat:6081']
  scope: 2 groups · 4 pieces
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected=''
kind=exact: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected=''
kind=same_stat: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected=''
class=Titan: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to class Titan
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected='Titan'
kind=exact, then class=Titan: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates, class Titan
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected='Titan'
class=Hunter: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to class Hunter
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected='Hunter'
kind=same_stat, then class=Hunter: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups, class Hunter
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected='Hunter'
class=Titan, then kind=same_stat: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected=''
class=Hunter, then kind=exact: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected=''
after the dropped class, the slice says: 'Filter no longer applies and was cleared: class Hunter.'
after the dropped class, production says: 'Local view state dropped: duplicate filter guardianClass Hunter.'
-- negative control: remove one required value from the rendered page --
differences before removal: 0; after removal: ['exact:6031 member 6032 masterwork_tier: not shown']
after a verdict text was changed in the page: ["same_stat:6081 member 6081 verdict: shows ('Approved', False), server says ('Unreviewed', False)"]
RESULT: PASS
```

## S2: hostile content (gate H2)

Every string in the envelope replaced, at two widths. The first pass also replaces the values that decide who has verdict buttons, and the page must then show none; the second keeps those three so a verdict can be pressed on a hostile id.

```bash
.venv/bin/python spikes/issue-206/proof_s2_hostile.py
```

Output:

```text
-- 1440px: every string in the envelope replaced --
string values replaced: 602; distinct ids: 32; distinct hashes: 15
differences from the hostile envelope, value by value: 0
ids in the DOM (attribute and text, untrimmed) byte-identical: True: ['18446744073709551615', '007', '9"<\'> x']
hashes in the DOM identical: True: ['005<script>alert(4)</script>', '0014<script>alert(4)</script>']
names shown as exact text, internal double spaces kept: True; length 404
elements created from values (img, script, i, b, u): 0; script elements in the document: 1 (the bundle)
page scrolls sideways with 300-character unbroken values: False
verdict buttons with every disposition and action hostile: 0 (no member's disposition and action agree, so none is a proposal member)
second pass, disposition and action values kept: strings replaced 574; verdict buttons 9; differences from the envelope 0
verdict request body: {"report_revision":1,"verdict_revision":0,"fingerprint":"b212ae6e8f2fc0a7ee7977227f78d32f431149e14af3d81c60698ffec47b9397","decisions":[{"id":"007","verdict":"vetoed"}]}
id in the request equals the envelope's id: True; is a JSON string: True
status after the acknowledgement names the id as text: True
dialogs: []; CSP violations: []; console errors: []; page errors: []
-- 390px: every string in the envelope replaced --
string values replaced: 602; distinct ids: 32; distinct hashes: 15
differences from the hostile envelope, value by value: 0
ids in the DOM (attribute and text, untrimmed) byte-identical: True: ['18446744073709551615', '007', '9"<\'> x']
hashes in the DOM identical: True: ['005<script>alert(4)</script>', '0014<script>alert(4)</script>']
names shown as exact text, internal double spaces kept: True; length 404
elements created from values (img, script, i, b, u): 0; script elements in the document: 1 (the bundle)
page scrolls sideways with 300-character unbroken values: False
verdict buttons with every disposition and action hostile: 0 (no member's disposition and action agree, so none is a proposal member)
second pass, disposition and action values kept: strings replaced 574; verdict buttons 9; differences from the envelope 0
verdict request body: {"report_revision":1,"verdict_revision":0,"fingerprint":"b212ae6e8f2fc0a7ee7977227f78d32f431149e14af3d81c60698ffec47b9397","decisions":[{"id":"9\"<'> x","verdict":"vetoed"}]}
id in the request equals the envelope's id: True; is a JSON string: True
status after the acknowledgement names the id as text: True
dialogs: []; CSP violations: []; console errors: []; page errors: []
RESULT: PASS
```

## S3: acknowledged state only (gate H3)

A held response, then `stale_verdicts` and `stale_report`.

```bash
.venv/bin/python spikes/issue-206/proof_s3_acknowledged.py
```

Output:

```text
-- the response is held after the server has committed --
before: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [False, False, False]}
server while held: verdict_revision=1, verdicts=[{'id': '6032', 'verdict': 'approved'}]
page while held:   {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [True, True, True]}
status unchanged while held: True
after release:     {'verdict': 'Approved', 'persisted_veto': False, 'pressed': ['Approve'], 'disabled': [False, False, False]}; status='The server recorded your approval for item 6032.'
after Veto: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
after Unset: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [False, False, False]}; server verdicts=[]
-- stale_verdicts: another client changes a verdict --
status: 'Your veto was not applied because the review changed. Repeat it if you still want it.'
the page's own action is not shown: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [False, False, False]}
the other client's verdict is shown:  {'verdict': 'Approved', 'persisted_veto': False, 'pressed': ['Approve'], 'disabled': [False, False, False]}
verdict POSTs sent by the page: ['verdicts']; server verdict_revision before=4 after=4; verdicts=[{'id': '6081', 'verdict': 'approved'}]
-- stale_report: a new export is uploaded elsewhere --
status: 'Your approval was not applied because the review changed. Repeat it if you still want it.'
groups now shown: ['exact:8201']; scope: 1 group · 3 pieces
verdict POSTs sent by the page: ['verdicts']; server verdict_revision before=5 after=5; verdicts=[]
differences from the server's new report: 0
RESULT: PASS
```

## S4: finalise, reset, disconnect (gate H3)

Finalise from the open page and from outside it, with the revision pair unchanged; reset; the server stopped.

```bash
.venv/bin/python spikes/issue-206/proof_s4_lifecycle.py
```

Output:

```text
-- finalise from the open page, with a veto in place --
before: state=reviewing, revisions=(1, 1), override_status=[]
page before: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}
after:  state=finalized, revisions=(1, 1), active persisted vetoes=['6032']
revision pair and fingerprint unchanged by the finalise: True
requests the page made: ['POST api/finalize', 'GET api/report']; page navigations or reloads: 0
open page now: {'session': 'Finalised. The reviewed CSV has been produced and this review is frozen.', '6032': {'verdict': 'Vetoed', 'persisted_veto': True, 'pressed': ['Veto'], 'disabled': [True, True, True]}, 'all verdict controls disabled': True, 'download link': 1}
differences between the open page and the finalised envelope: 0
production, loaded fresh: {'verdict': 'Vetoed this session · active persisted veto still suppresses this item', 'disabled': [True, True, True], 'note': 'Finalisation succeeded. The reviewed CSV was produced; this session is now frozen.'}
same meaning as production (vetoed, a persisted veto still suppresses it, controls off, frozen): True
-- reset, then a new upload --
after reset: server state=idle, report_revision=2; page groups=0, empty state=['no-report'], session note='No report is loaded. Upload a DIM armor export on the main review page, then reload here.'
after a new upload and Reload: state=exports-loaded, {'verdict': 'Unreviewed', 'persisted_veto': True, 'pressed': ['Unset'], 'disabled': [False, False, False]}
the veto saved by the finalise is still reported and shown: True; differences from the envelope: 0
-- finalise from outside the already-open page --
finalise posted outside the page: HTTP 200; revisions unchanged=True
open page, before it makes any request: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}
status: 'Your approval was not applied: this review is finalised.'
POSTs sent by the page: ['verdicts']; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
open page now: {'session': 'Finalised. The reviewed CSV has been produced and this review is frozen.', '6032': {'verdict': 'Vetoed', 'persisted_veto': True, 'pressed': ['Veto'], 'disabled': [True, True, True]}, 'all verdict controls disabled': True, 'download link': 1}
a fresh load shows the same: True
-- the server stops --
filter with the server stopped: groups=['same_stat:6081']; scope='1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups'
a verdict with the server stopped: status='Your approval was not applied. The review server did not answer. Filters still work; use Reload to reconnect.'
nothing shown as applied, controls off: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [True, True, True]}; connection=disconnected
filter again while disconnected: groups=['exact:6031']; scope='1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates'
RESULT: PASS
```

## S5: focus and live regions (gate H4)

Node identity across an acknowledgement, writes to the live regions, and the focus policy on a report change.

```bash
.venv/bin/python spikes/issue-206/proof_s5_focus.py
```

Output:

```text
-- static semantics (contract section 7) --
{'skipLink': 'Skip to review content', 'h1Focusable': True, 'regions': ['vc-status: role=status, aria-live=polite', 'vc-reconciliation: role=status, aria-live=polite', 'vc-scope: role=status, aria-live=polite'], 'toggles': 12, 'tabRoles': 0, 'unnamed': 0, 'labelledSelects': True}
first Tab stop: 'Skip to review content'; activating it moves focus to: #vc-title
-- why the slice uses aria-disabled: what native `disabled` does to focus here --
a focused button set to disabled: focus is then on <BODY>
-- a verdict by keyboard --
while the request is in flight: {'focus': 'Approve item 6032', 'ariaDisabled': 'true'}
Unset (Enter): focused control is the same node=True (Unset item 6032); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 0}; controls rebuilt=0; tab stops=18; natively disabled buttons=0
Veto (Space): focused control is the same node=True (Veto item 6032); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 0}; controls rebuilt=0; tab stops=18; natively disabled buttons=0
-- a filter change --
kind filter: focused control is the same node=True; writes={'vc-status': 0, 'vc-reconciliation': 0, 'vc-scope': 1}; live regions are the same nodes=True
-- report change, the focused member is still in the new report --
stale_report, member 6032 still present: focused control is the same node=True (Approve item 6032); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 0}; controls rebuilt=0; tab stops=18; natively disabled buttons=0
-- report change, the focused member is gone --
stale_report, member 6032 gone: focused control is the same node=False (vc-list-title); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 1}; controls rebuilt=3; tab stops=9; natively disabled buttons=0
RESULT: PASS
```

## S6: layouts (gate H5)

Three widths, two colour schemes, two fixtures. Run with `--screenshots` it also writes the PNG files beside this file.

```bash
.venv/bin/python spikes/issue-206/proof_s6_layout.py
```

Output:

```text
-- armor_close.csv --
1440px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1440px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
tab order at 390px: ['Skip to review content', 'Reload report', 'Finalise review', 'Reset session', 'All (2)', 'Exact (1)', 'Same stats (1)', 'any classTitan (2 groups)', 'Reset filters', 'Approve item 6032', 'Veto item 6032', 'Unset item 6032', 'Approve item 6081', 'Veto item 6081', 'Unset item 6081', 'Approve item 6082', 'Veto item 6082', 'Unset item 6082']
-- armor_same_stat_four_ui.csv --
1440px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1440px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
RESULT: PASS
```

## S7: Content-Security-Policy (gate H7)

The whole slice under the unchanged policy, then one probe per shortlisted library.

```bash
.venv/bin/python spikes/issue-206/proof_s7_csp.py
```

Output:

```text
production policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
additions the slice is served with: []
-- part 1: the whole slice under the unchanged policy --
exercised: ['class facet', 'kind filter, dropping the class (reconciliation notice)', 'verdict buttons (approve, veto, unset)', 'focus ring', 'finalise (frozen controls, persisted-veto notice, download link)', 'reset (the no-report empty state)', 'reload']
requests: {'document GET spike/': 1, 'script GET spike/assets/app.js': 1, 'stylesheet GET spike/assets/app.css': 1, 'fetch GET api/report': 3, 'fetch POST api/verdicts': 4, 'fetch POST api/finalize': 1, 'fetch POST api/reset': 1}
policy on every response equals production's: True
violations: []; console errors: []; page errors: []
stylesheet applied: True; <style> elements: 0; style attributes: 0; images: 0; web fonts: 0
-- part 2: library probes under the unchanged policy --
plain Svelte 5, no library: violations=none; button styled=True; overlay visible=True; custom (non-native) select=False; style attributes in the DOM=4; <style> elements=0
  build: css 117 bytes, js 2509 bytes (shared chunks excluded); data: URIs in css 0; @font-face 0; remote url() 0
shadcn-svelte 1.7.0 on Bits UI 2.19.5: violations=none; button styled=True; overlay visible=True; custom (non-native) select=True; style attributes in the DOM=3; <style> elements=0
  build: css 31692 bytes, js 203155 bytes (shared chunks excluded); data: URIs in css 0; @font-face 0; remote url() 0
Skeleton 5.0.1 (Zag.js): violations=none; button styled=True; overlay visible=True; custom (non-native) select=False; style attributes in the DOM=6; <style> elements=0
  build: css 143240 bytes, js 65692 bytes (shared chunks excluded); data: URIs in css 0; @font-face 0; remote url() 0
daisyUI 5.7.47 (CSS only): violations={'img-src blocked data': 31}; button styled=True; overlay visible=True; custom (non-native) select=False; style attributes in the DOM=0; <style> elements=0
  build: css 61373 bytes, js 1071 bytes (shared chunks excluded); data: URIs in css 1; @font-face 0; remote url() 0
plain Svelte: style: directive applied (width 1068px of 1424px); style attribute applied (width 854.391px); spread style applied (outline dotted)
probes with violations under the unchanged policy: ['daisy']
daisy with ['img']: violations=none
daisy with ['font']: violations={'img-src blocked data': 31}
daisy with ['style-inline']: violations={'img-src blocked data': 31}
daisy: fewest additions that clear it: ['img'] -> default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'; img-src 'self' data:
the slice uses daisyUI and overrides the texture that needs img-src (`--fx-noise: none` in app.css), which is why part 1 has no violation
RESULT: PASS
```

## S8: installed wheel, in a browser (gate H6)

A wheel built from a temporary copy, installed into a fresh environment, served with Node absent from the server's `PATH`, and driven by Chromium.

```bash
.venv/bin/python spikes/issue-206/proof_s8_wheel.py
```

Output:

```text
package-data in the copy is today's, unedited: True
wheel files under vault_cleaner/ui/: ['vault_cleaner/ui/__init__.py', 'vault_cleaner/ui/review.css', 'vault_cleaner/ui/review_app.css', 'vault_cleaner/ui/review_app.html', 'vault_cleaner/ui/review_app.js', 'vault_cleaner/ui/review_server.html', 'vault_cleaner/ui/review_server.js', 'vault_cleaner/ui/review_ui.js']
the three frontend files in the wheel are byte-identical to the build: True; node_modules or .svelte files in the wheel: 0
installed into a fresh environment; editable install: False
server process: vault_cleaner imported from the fresh environment=True, from the repository=False; node on its PATH=None; npm on its PATH=None; frontend files found as package resources=['review_app.css', 'review_app.html', 'review_app.js']
node on the proof's own PATH (so the absence above is real): True; PATH given to the server has 1 entry
bootstrap exchanged in the browser; fake fixture uploaded: HTTP 200
groups rendered by the installed JavaScript and CSS: ['exact:6031', 'same_stat:6081']
  response: /api/report 200 application/json
  response: /spike/ 200 text/html; charset=utf-8
  response: /spike/assets/app.css 200 text/css; charset=utf-8
  response: /spike/assets/app.js 200 text/javascript; charset=utf-8
verdict acknowledged: status='The server recorded your veto for item 6032.'; Veto pressed=true; server verdict_revision 0 -> 1; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
stylesheet applied: True; console errors: []; CSP violations: []
RESULT: PASS
```

## S9: request envelope (gate H7)

Headers and refusals on every spike route, and the policy on production routes.

```bash
.venv/bin/python spikes/issue-206/proof_s9_envelope.py
```

Output:

```text
-- served as the slice is: additions [] --
production asset headers: {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"}
/spike/: HTTP 200, text/html; charset=utf-8, 439 bytes; security headers equal production's=True; refusals={'no cookie': 401, 'wrong Host': 400, 'wrong Origin': 403, 'POST': 404}
/spike/assets/app.js: HTTP 200, text/javascript; charset=utf-8, 63440 bytes; security headers equal production's=True; refusals={'no cookie': 401, 'wrong Host': 400, 'wrong Origin': 403, 'POST': 404}
/spike/assets/app.css: HTTP 200, text/css; charset=utf-8, 57022 bytes; security headers equal production's=True; refusals={'no cookie': 401, 'wrong Host': 400, 'wrong Origin': 403, 'POST': 404}
production route /: HTTP 200; policy byte-identical to SERVER_CSP=True
production route /assets/review.css: HTTP 200; policy byte-identical to SERVER_CSP=True
production route /assets/review_ui.js: HTTP 200; policy byte-identical to SERVER_CSP=True
production route /assets/review_server.js: HTTP 200; policy byte-identical to SERVER_CSP=True
production route /api/report: HTTP 200; policy byte-identical to SERVER_CSP=True
/spike/assets/other.js: HTTP 404
/spike/assets/../../pyproject.toml: HTTP 404
/spike/assets/%2e%2e/app.js: HTTP 404
/spike/modules.json: HTTP 404
/spike/index.html: HTTP 404
/spike/ with a file-like query string: HTTP 200; the body is the same index.html=True
/spike (no trailing slash): HTTP 308 -> /spike/
-- the mechanism, with all three pre-approved additions switched on --
/spike/: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'; img-src 'self' data:; font-src 'self'
directives that differ from production: ["font-src 'self'", "img-src 'self' data:", "style-src 'self' 'unsafe-inline'"]
production route /: policy byte-identical to SERVER_CSP=True
production route /assets/review.css: policy byte-identical to SERVER_CSP=True
production route /assets/review_ui.js: policy byte-identical to SERVER_CSP=True
production route /assets/review_server.js: policy byte-identical to SERVER_CSP=True
production route /api/report: policy byte-identical to SERVER_CSP=True
/spike/ without a cookie: HTTP 401, policy on the refusal is the spike's=True
RESULT: PASS
```

## S10: development loop (gate H9)

Build times, sizes, the type check and unit tests, the edit-and-see loop, what its proxy does to `Origin`, and what stands in for Flask's `Host` check in development. **The timings vary from run to run**; every other line is repeatable.

```bash
.venv/bin/python spikes/issue-206/proof_s10_devloop.py
```

Output:

```text
-- build --
cold build: exit 0, 0.8 s; rebuild after a one-line edit: exit 0, 0.8 s
(each figure includes starting npm and Vite; Vite's own report of the build step was: ✓ built in 334ms)
index.html: 439 bytes, 282 gzip
assets/app.js: 63440 bytes, 22786 gzip
assets/app.css: 57022 bytes, 9786 gzip
-- type check and unit tests --
svelte-check: exit 0, 2.2 s: found 0 errors and 0 warnings
vitest: exit 0, 1.3 s: ['Test Files  3 passed (3)', 'Tests  32 passed (32)']
-- edit and see, against the real server --
one command to first render, through the proxy: 1.3 s; page address is the dev server's: True
a verdict through the proxy: the page sent ['POST /api/verdicts'] to the dev server; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
save to visible: 85 ms; no page reload: True; the server's verdict is still shown: True
-- what the proxy does to Origin --
POST through the proxy with the dev server's own Origin: HTTP 400 (reached the route; 400 is its answer to a malformed body)
POST through the proxy with a foreign Origin: HTTP 403 (forwarded unchanged, refused)
POST straight to Flask with the dev server's Origin: HTTP 403 (Flask itself is not relaxed)
-- what stands in for Flask's exact-Host check --
the proxy always presents the Flask server's own Host, so in development the only Host check is Vite's allow-list (server.allowedHosts, left at its default)
GET /api/report through the proxy, by Host name (dev port): {'127.0.0.1': 200, 'evil.example': 403, 'localhost': 200, 'foo.localhost': 200}
GET /api/report straight to Flask, by Host name (its own port): {'127.0.0.1': 200, 'evil.example': 400, 'localhost': 400, 'foo.localhost': 400}
so Vite refuses a foreign Host, but accepts localhost and any *.localhost name, which Flask itself refuses
-- none of the development path is in the build --
index.html: development-only strings found: []
assets/app.js: development-only strings found: []
assets/app.css: development-only strings found: []
RESULT: PASS
```

## S11: type drift (gate H9)

One envelope field renamed on the Python side, in memory.

```bash
.venv/bin/python spikes/issue-206/proof_s11_typedrift.py
```

Output:

```text
-- before the rename --
committed samples equal what the server returns: True
-- Python renames exact-group member `disposition` to `member_disposition` --
1. contract.py --check, no Node needed: stale samples detected: ['reviewing.json', 'finalized.json']
2. type check after regenerating the samples: exit 1: COMPLETED 295 FILES 2 ERRORS 0 WARNINGS 1 FILES_WITH_PROBLEMS
   src/contract/samples.ts 11:72: ... Property 'disposition' is missing in type '{ equipped: boolean; id: string; in_loa ...
       ... but required in type 'ExactMember'
   src/contract/samples.ts 11:83: ... Property 'disposition' is missing in type '{ equipped: boolean; id: string; in_loa ...
       ... but required in type 'ExactMember'
3. unit tests: exit 1: ['Test Files  1 failed | 2 passed (3)', 'Tests  1 failed | 31 passed (32)']
4. production build: exit 0: ✓ built (Vite does not type-check; the build is not the gate)
so the rename surfaces at step 1 without Node, and at the type check and the unit tests with it; nothing reaches the browser unless all three are skipped
RESULT: PASS
```

## S12: code comparison, npm tree and licences (gate H8)

Line counts by category, the installed tree against the lockfile, `npm audit`, and the licence of everything installed and of everything in the built output. The JavaScript half of the built-output scan reads the bundler's own module list. The stylesheet half is a text match on the `@import` and `@plugin` lines of the CSS entry file, because the bundler lists only that file; a package pulled in by an imported stylesheet would not be seen.

```bash
.venv/bin/python spikes/issue-206/proof_s12_code.py
```

Output:

```text
-- lines (non-blank) --
production JavaScript the slice replaces: 908 lines in 6 ranges (anchors found: True)
Jinja hybrid (#137 evidence, quoted): 93 lines of fragment seam and 62 lines of browser-owned filtering in JavaScript, a 474-line Python context builder and 187 lines of templates: quote found=True
slice, components and markup: 408 lines in 9 files
slice, presentation projection (wording, shared/differing split): 298 lines in 1 files
slice, application logic (requests, revisions, reconciliation, lifecycle): 277 lines in 3 files
slice, filtering: 102 lines in 1 files
slice, types: 110 lines in 1 files
slice, stylesheet: 61 lines in 1 files
slice, Python: serving the build: 164 lines in 1 files
slice, everything that runs or is served: 1420 lines
slice, unit tests and the type-contract module: 347 lines in 4 files
slice, build configuration: 113 lines in 3 files
slice, Python: contract sample generator: 92 lines in 1 files
proof and tooling scripts (not part of any comparison): 3708 lines in 22 files
imperative DOM calls (createElement, el(), appendChild, textContent=, setAttribute): slice 0; the production ranges 87
-- npm tree and audit --
frontend: 76 packages installed; 122 in the lockfile; installed but not as locked: []; locked but not installed here (other platforms' optional binaries): 46, all optional=True, lockfile licences {'MIT': 26, 'MPL-2.0': 20}
  licences in the installed tree: {'Apache-2.0': 5, 'BSD-3-Clause': 1, 'ISC': 2, 'MIT': 63, 'MPL-2.0': 5}
  MPL-2.0 (accepted for build-time-only use): ['axe-core@4.13.0', 'lightningcss-linux-x64-gnu@1.32.0', 'lightningcss-linux-x64-gnu@1.33.0', 'lightningcss@1.32.0', 'lightningcss@1.33.0']
  outside the approved licences: []
  apexcharts or Flowbite installed: []
probes: 132 packages installed; 178 in the lockfile; installed but not as locked: []; locked but not installed here (other platforms' optional binaries): 46, all optional=True, lockfile licences {'MIT': 26, 'MPL-2.0': 20}
  licences in the installed tree: {'0BSD': 1, 'Apache-2.0': 7, 'BSD-3-Clause': 1, 'ISC': 3, 'MIT': 116, 'MPL-2.0': 4}
  MPL-2.0 (accepted for build-time-only use): ['lightningcss-linux-x64-gnu@1.32.0', 'lightningcss-linux-x64-gnu@1.33.0', 'lightningcss@1.32.0', 'lightningcss@1.33.0']
  outside the approved licences: []
  apexcharts or Flowbite installed: []
frontend direct dependencies: runtime 0, development 11; every version exact: True
npm audit: {'info': 0, 'low': 0, 'moderate': 0, 'high': 0, 'critical': 0, 'total': 0}
-- what is in the built output --
dist/modules.json: 3595 bytes; every path relative to frontend/: True
assets/app.js: 61 modules, 14 of them the slice's own source
assets/app.css: built from src/app.css, which pulls in ['tailwindcss', 'daisyui']
  contributes to the output: clsx@2.1.1 (MIT), 1 modules
  contributes to the output: daisyui@5.7.47 (MIT), stylesheet
  contributes to the output: svelte@5.57.1 (MIT), 46 modules
  contributes to the output: tailwindcss@4.3.3 (MIT), stylesheet
MPL-2.0 packages contributing to the output: []; traces of lightningcss or axe-core in the built files: []
RESULT: PASS
```

## S13: automated accessibility check (gate H4)

axe-core in both colour schemes at two widths, in seven states, with the
contrast axe could not judge measured directly. An actual Tab lap checks all
links, selects and buttons (including unreviewed, held, approved, vetoed and
frozen verdict controls) for the 3px/2px floor and at least 3:1 contrast against
the adjacent background. The old cascade is restored temporarily through
CSSOM as a failing negative control, then the shipped rule is restored.

```bash
.venv/bin/python spikes/issue-206/proof_s13_axe.py
```

Output:

```text
axe-core 4.13.0 (MPL-2.0), development-only
pre-fix cascade negative control: Skip to review content=2.40:1/2px; Finalise review=2.40:1/2px; All (2)=2.40:1/2px; rejected=True
reviewing, unreviewed, 1440px light: rules passed=39, violations=[]; contrast axe could not judge: 20 nodes, measured here 20, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
approval in flight, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
approval in flight, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
approval in flight, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
approval in flight, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
filtered, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 1440px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
filtered, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 1440px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
filtered, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 390px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
filtered, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 390px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
finalised, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 1440px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Download reviewed CSV', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
finalised, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 1440px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Download reviewed CSV', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
finalised, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 390px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Download reviewed CSV', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
finalised, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 390px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Download reviewed CSV', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
no report, 1440px light: rules passed=32, violations=[]; contrast axe could not judge: 5 nodes, measured here 5, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 1440px light: keyboard focus=5/5; lowest 16.68:1 (main review page); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72)]; outline floor=3px/2px; problems=[]
no report, 1440px dark: rules passed=32, violations=[]; contrast axe could not judge: 5 nodes, measured here 5, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 1440px dark: keyboard focus=5/5; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75)]; outline floor=3px/2px; problems=[]
no report, 390px light: rules passed=31, violations=[]; contrast axe could not judge: 6 nodes, measured here 6, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 390px light: keyboard focus=5/5; lowest 16.68:1 (main review page); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72)]; outline floor=3px/2px; problems=[]
no report, 390px dark: rules passed=32, violations=[]; contrast axe could not judge: 5 nodes, measured here 5, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 390px dark: keyboard focus=5/5; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75)]; outline floor=3px/2px; problems=[]
RESULT: PASS
```

## S14: change exercises (gate H8)

Three changes as patches, each with a deliberately incomplete version, and the places the same change touches in the current page and in #137's Jinja hybrid.

```bash
.venv/bin/python spikes/issue-206/proof_s14_changes.py
```

Output:

```text
-- exercise 1: show one more per-member comparison value (a same-stat member's selected partner) --
  patch applies cleanly to the committed slice: True
  Svelte slice: 1 places in 1 files {'src/lib/view.ts': 1}; tests added or changed: {'src/lib/view.test.ts': 1}
  with the patch: type check exit 0, unit tests exit 0 ['Tests  32 passed (32)'], build exit 0
  deliberately incomplete version: type check exit 1, unit tests exit 1
  current page: 3 places in 1 files
    src/vault_cleaner/ui/review_ui.js:569 already normalised here (3 lines), or it would be added: found at that line=True
    src/vault_cleaner/ui/review_ui.js:592 already carried on the member, or it would be added: found at that line=True
    src/vault_cleaner/ui/review_ui.js:1500 add one comparison spec after Holofoil: found at that line=True
  Jinja hybrid (#137): 1 places in 1 files
    spikes/issue-137/context.py:172 add one axis spec after Holofoil in _axes: found at that line=True
-- exercise 2: add one more filter facet (Slot / type) --
  patch applies cleanly to the committed slice: True
  Svelte slice: 3 places in 2 files {'src/lib/filters.ts': 1, 'src/lib/view.ts': 2}; tests added or changed: {'src/lib/filters.test.ts': 1}
  with the patch: type check exit 0, unit tests exit 0 ['Tests  33 passed (33)'], build exit 0
  deliberately incomplete version: type check exit 1, unit tests exit 0
  current page: 6 places in 2 files
    src/vault_cleaner/ui/review_server.js:106 initial filter state: found at that line=True
    src/vault_cleaner/ui/review_server.js:264 fields reconciled when a report or kind changes: found at that line=True
    src/vault_cleaner/ui/review_server.js:295 scope sentence: found at that line=True
    src/vault_cleaner/ui/review_server.js:369 filter state restored on adoption: found at that line=True
    src/vault_cleaner/ui/review_server.js:1298 the control: found at that line=True
    src/vault_cleaner/ui/review_ui.js:758 the match: found at that line=True
  Jinja hybrid (#137): 9 places in 4 files
    spikes/issue-137/context.py:382 the group's facet value: found at that line=True
    spikes/issue-137/templates/_armor_group.html:128 the data attribute the browser filters on: found at that line=True
    spikes/issue-137/templates/shell.html:37 the control: found at that line=True
    spikes/issue-137/static/spike.js:33 the control's handle: found at that line=True
    spikes/issue-137/static/spike.js:44 filter state: found at that line=True
    spikes/issue-137/static/spike.js:388 scope sentence: found at that line=True
    spikes/issue-137/static/spike.js:408 recount and drop: found at that line=True
    spikes/issue-137/static/spike.js:431 the match: found at that line=True
    spikes/issue-137/static/spike.js:465 the change handler: found at that line=True
-- exercise 3: change the wording of one verdict state (Unreviewed) --
  patch applies cleanly to the committed slice: True
  Svelte slice: 1 places in 1 files {'src/lib/view.ts': 1}; tests added or changed: none
  with the patch: type check exit 0, unit tests exit 0 ['Tests  32 passed (32)'], build exit 0
  deliberately incomplete version: type check exit 1, unit tests exit 0
  current page: 1 places in 1 files
    src/vault_cleaner/ui/review_server.js:425 the wording: found at that line=True
  Jinja hybrid (#137): 1 places in 1 files
    spikes/issue-137/context.py:101 the wording: found at that line=True
the committed slice is byte-identical before and after this proof: True
RESULT: PASS
```

## Build reproducibility

Two builds from the same lockfile on the same machine, compared byte for byte. This is what a "committed build equals a fresh build" check in CI would rely on; one machine and one platform were measured.

```bash
(cd spikes/issue-206/frontend && npm run build >/dev/null 2>&1 && sha256sum dist/index.html dist/assets/app.js dist/assets/app.css > /tmp/vc-206-build.sha && npm run build >/dev/null 2>&1 && sha256sum --check /tmp/vc-206-build.sha && rm /tmp/vc-206-build.sha)
```

Output:

```text
dist/index.html: OK
dist/assets/app.js: OK
dist/assets/app.css: OK
```

## Keep/remove line ranges

The decision record's keep/remove map cites the current page by the ranges #137 established. #137's own proof checks every one of them at this head.

```bash
.venv/bin/python spikes/issue-137/proof_js_map.py
```

Output:

```text
review_server.js: 1793 lines; review_ui.js: 1851 lines
1 bootstrap/session: review_server.js:81-120 (40) ok
1 bootstrap/session: review_server.js:128-212 (85) ok
1 bootstrap/session: review_server.js:312-413 (102) ok
1 bootstrap/session: review_server.js:1773-1792 (20) ok
2 uploads: review_server.js:752-754 (3) ok
2 uploads: review_server.js:1483-1508 (26) ok
2 uploads: review_server.js:1760-1767 (8) ok
3 report fetching: review_server.js:443-570 (128) ok
3 report fetching: review_server.js:1509-1525 (17) ok
4 filters/sort/search/navigation: review_ui.js:211-262 (52) ok
4 filters/sort/search/navigation: review_ui.js:264-302 (39) ok
4 filters/sort/search/navigation: review_ui.js:747-802 (56) ok
4 filters/sort/search/navigation: review_ui.js:846-857 (12) ok
4 filters/sort/search/navigation: review_server.js:214-310 (97) ok
4 filters/sort/search/navigation: review_server.js:786-832 (47) ok
4 filters/sort/search/navigation: review_server.js:1212-1218 (7) ok
5 verdict mutation and acknowledgement: review_server.js:572-584 (13) ok
5 verdict mutation and acknowledgement: review_server.js:899-921 (23) ok
5 verdict mutation and acknowledgement: review_server.js:935-943 (9) ok
5 verdict mutation and acknowledgement: review_server.js:1526-1543 (18) ok
5 verdict mutation and acknowledgement: review_server.js:1556-1564 (9) ok
5 verdict mutation and acknowledgement: review_server.js:1737-1759 (23) ok
5 verdict mutation and acknowledgement: review_ui.js:1168-1199 (32) ok
5 verdict mutation and acknowledgement: review_ui.js:1790-1815 (26) ok
6 stale-state reconciliation: review_server.js:760-776 (17) ok
6 stale-state reconciliation: review_server.js:944-1014 (71) ok
6 stale-state reconciliation: review_server.js:1544-1555 (12) ok
7 finalise/download/reset/shutdown: review_server.js:585-601 (17) ok
7 finalise/download/reset/shutdown: review_server.js:777-785 (9) ok
7 finalise/download/reset/shutdown: review_server.js:851-877 (27) ok
7 finalise/download/reset/shutdown: review_server.js:1447-1482 (36) ok
7 finalise/download/reset/shutdown: review_server.js:1565-1736 (172) ok
8 focus and live regions: review_server.js:603-610 (8) ok
8 focus and live regions: review_server.js:755-759 (5) ok
8 focus and live regions: review_server.js:833-850 (18) ok
8 focus and live regions: review_server.js:878-898 (21) ok
9 responsive comparison switching: review_ui.js:1641-1648 (8) ok
10 DOM construction: shell: review_server.js:627-746 (120) ok
10 DOM construction: metrics: review_server.js:1015-1043 (29) ok
10 DOM construction: weapon DIM query: review_server.js:1044-1211 (168) ok
10 DOM construction: filters: review_server.js:1219-1369 (151) ok
10 DOM construction: lists: review_server.js:1370-1446 (77) ok
10 DOM construction: element helpers: review_ui.js:892-981 (90) ok
10 DOM construction: proposals: review_ui.js:87-150 (64) ok
10 DOM construction: proposals: review_ui.js:982-1166 (185) ok
10 DOM construction: duplicate groups: review_ui.js:304-624 (321) ok
10 DOM construction: duplicate groups: review_ui.js:804-844 (41) ok
10 DOM construction: duplicate groups: review_ui.js:1201-1640 (440) ok
10 DOM construction: duplicate groups: review_ui.js:1773-1788 (16) ok
10 DOM construction: armor DIM query: review_ui.js:626-739 (114) ok
10 DOM construction: armor DIM query: review_ui.js:1650-1771 (122) ok
-- lines per responsibility --
1 bootstrap/session: 247
2 uploads: 37
3 report fetching: 145
4 filters/sort/search/navigation: 310
5 verdict mutation and acknowledgement: 153
6 stale-state reconciliation: 100
7 finalise/download/reset/shutdown: 261
8 focus and live regions: 52
9 responsive comparison switching: 8
10 DOM construction: shell: 120
10 DOM construction: metrics: 29
10 DOM construction: weapon DIM query: 168
10 DOM construction: filters: 151
10 DOM construction: lists: 77
10 DOM construction: element helpers: 90
10 DOM construction: proposals: 249
10 DOM construction: duplicate groups: 818
10 DOM construction: armor DIM query: 236
-- the Armor duplicates slice --
production JavaScript the slice replaces: 908 lines in 6 ranges
spike JavaScript, all experiments: 464 non-blank lines
spike JavaScript without the R3 and server-filter experiments: 393 non-blank lines
  of which the fragment seam (fetch, check, install, paint, focus): 93
  of which browser-owned filtering for two filters: 62
  of which session, mutation and reconciliation that production already has: 238
spike context builder (Python): 474 non-blank lines
spike templates for the slice: 187 non-blank lines
RESULT: PASS
```

## Licences the plan's table did not list

The registry's licence field for the packages the decision record discusses.

```bash
for p in lightningcss axe-core @fontsource-variable/inter apexcharts daisyui bits-ui @skeletonlabs/skeleton-svelte; do echo "$p: $(npm view $p license)"; done
```

Output:

```text
lightningcss: MPL-2.0
axe-core: MPL-2.0
@fontsource-variable/inter: OFL-1.1
apexcharts: SEE LICENSE IN LICENSE
daisyui: MIT
bits-ui: MIT
@skeletonlabs/skeleton-svelte: MIT
```


## S15: real scale (gates H1, H4, H5)

The entire sanitised report, no overlay: S1's independent oracle compares all
groups/members/required values at both widths and after a real acknowledgement;
E10's nine filter sequences run on both pages; all spirit-bearing exact groups
are checked. S6's whole-document geometry and keyboard lap cover every group
at all three widths in both schemes; the four screenshots show only the top
2,400 px.
A verdict on the final group checks both node identity and viewport position:
scroll anchoring adjusts scrollY as the status wraps, but the control does not
move in the viewport. Axe and the independent contrast checks cover the whole
report after colour transitions finish. The shared S13 check additionally
measures every one of the 444 actual keyboard-focused controls for the
outline floor and at least 3:1 against the adjacent background.

Five alternating runs per page use one authenticated report/session/machine,
All groups, no Class filter, 1440 px/light. Production activates its ready
surface control in-page before building duplicates; its Proposals DOM and both
matrix orientations are counted. Readiness requires every group to be laid
out. Navigation time starts at performance.timeOrigin; acknowledgement time
starts after decoding the verdict JSON, before returning it to application
code. MutationObserver measures the target aria-pressed change and the next
animation frame. These measure DOM completion/frame opportunity, not physical
display scanout. Timing numbers vary on rerun. An isolated repeat confirmed
the direction: the slice is slower, despite fewer elements. Correctness checks
pass; the recommendation and H5 performance condition are bounded conditional.

S15 exposed two colour defects, fixed narrowly in the slice stylesheet:
approved success text at 4.46:1 and dark outlined tier-5 role text at 2.39:1.
Exact Seasonal Mod and positive Holofoil still rest on S1's overlay; this
fixture supplies the spirit signatures without one.

```bash
.venv/bin/python spikes/issue-206/proof_s15_scale.py --screenshots
```

Output:

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
report: exact=9, same-stat=65; same-stat sizes={2: 57, 3: 6, 4: 2}; members=158; wire bytes=690503
unreviewed 1440px: groups=74, members=158, value/role assertions=3401, differences=0
unreviewed 390px: groups=74, members=158, value/role assertions=3401, differences=0
spirit signatures from unmodified upload: 5/5 exact groups correct
1440px no filter: equal=True; groups=74; scope='74 groups · 158 pieces'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected=''
1440px kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
1440px kind=same_stat: equal=True; groups=65; scope='65 of 74 groups · 140 of 158 pieces — filtered to same-stat groups'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected=''
1440px class=Titan: equal=True; groups=40; scope='40 of 74 groups · 88 of 158 pieces — filtered to class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Titan'
1440px kind=exact, then class=Titan: equal=True; groups=6; scope='6 of 74 groups · 12 of 158 pieces — filtered to exact duplicates, class Titan'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected='Titan'
1440px class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Hunter'
1440px kind=same_stat, then class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to same-stat groups, class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Hunter'
1440px class=Titan, then kind=same_stat: equal=True; groups=34; scope='34 of 74 groups · 76 of 158 pieces — filtered to same-stat groups, class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Titan'
1440px class=Hunter, then kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
  dropped-class notices: slice='Filter no longer applies and was cleared: class Hunter.'; production='Local view state dropped: duplicate filter guardianClass Hunter.'
1440px E10 sequences: executed=9, unsupported=0; real-upload Hunter-to-Exact drops=1
390px no filter: equal=True; groups=74; scope='74 groups · 158 pieces'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected=''
390px kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
390px kind=same_stat: equal=True; groups=65; scope='65 of 74 groups · 140 of 158 pieces — filtered to same-stat groups'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected=''
390px class=Titan: equal=True; groups=40; scope='40 of 74 groups · 88 of 158 pieces — filtered to class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Titan'
390px kind=exact, then class=Titan: equal=True; groups=6; scope='6 of 74 groups · 12 of 158 pieces — filtered to exact duplicates, class Titan'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected='Titan'
390px class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Hunter'
390px kind=same_stat, then class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to same-stat groups, class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Hunter'
390px class=Titan, then kind=same_stat: equal=True; groups=34; scope='34 of 74 groups · 76 of 158 pieces — filtered to same-stat groups, class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Titan'
390px class=Hunter, then kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
  dropped-class notices: slice='Filter no longer applies and was cleared: class Hunter.'; production='Local view state dropped: duplicate filter guardianClass Hunter.'
390px E10 sequences: executed=9, unsupported=0; real-upload Hunter-to-Exact drops=1
far-down acknowledged verdict: group=74/74; scroll before=100533px; same focused node=True; scroll change=20px; control viewport change=0px
acknowledged 1440px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 1440px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
wrote docs/evidence/issue-206/real-desktop-light.png: top 1440x2400 of a 1440x60949 page; all 74 groups checked
acknowledged 1440px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 1440px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
wrote docs/evidence/issue-206/real-desktop-dark.png: top 1440x2400 of a 1440x60949 page; all 74 groups checked
acknowledged 1024px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 1024px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 1024px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 390px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
wrote docs/evidence/issue-206/real-narrow-light.png: top 390x2400 of a 390x101453 page; all 74 groups checked
acknowledged 390px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 390px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
wrote docs/evidence/issue-206/real-narrow-dark.png: top 390x2400 of a 390x101453 page; all 74 groups checked
sanitised report, acknowledged verdict, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
sanitised report, acknowledged verdict, 1440px light: keyboard focus=444/444; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (74)', 17.72)]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
sanitised report, acknowledged verdict, 1440px dark: keyboard focus=444/444; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (74)', 14.75)]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
sanitised report, acknowledged verdict, 390px light: keyboard focus=444/444; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (74)', 17.72)]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
sanitised report, acknowledged verdict, 390px dark: keyboard focus=444/444; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (74)', 14.75)]; outline floor=3px/2px; problems=[]
slice CSP violations: []; console/errors/dialogs: {'dialogs': [], 'console': [], 'errors': []}
timing run 1 slice: all groups=74; navigation=203.5ms, next frame=217.3ms; ack-to-DOM=17.9ms, next frame=24.5ms; DOM elements=13143
timing run 1 production: all groups=74; navigation=150.2ms, next frame=156.3ms; ack-to-DOM=10.5ms, next frame=22.0ms; DOM elements=17138
timing run 2 production: all groups=74; navigation=147.8ms, next frame=153.9ms; ack-to-DOM=12.1ms, next frame=24.0ms; DOM elements=17138
timing run 2 slice: all groups=74; navigation=198.7ms, next frame=210.9ms; ack-to-DOM=17.8ms, next frame=24.8ms; DOM elements=13143
timing run 3 slice: all groups=74; navigation=200.0ms, next frame=212.6ms; ack-to-DOM=16.3ms, next frame=22.8ms; DOM elements=13143
timing run 3 production: all groups=74; navigation=154.0ms, next frame=159.5ms; ack-to-DOM=8.9ms, next frame=13.8ms; DOM elements=17138
timing run 4 production: all groups=74; navigation=141.2ms, next frame=148.2ms; ack-to-DOM=9.9ms, next frame=14.6ms; DOM elements=17138
timing run 4 slice: all groups=74; navigation=201.7ms, next frame=213.8ms; ack-to-DOM=23.8ms, next frame=30.9ms; DOM elements=13143
timing run 5 slice: all groups=74; navigation=198.0ms, next frame=209.7ms; ack-to-DOM=19.2ms, next frame=26.3ms; DOM elements=13143
timing run 5 production: all groups=74; navigation=155.3ms, next frame=161.2ms; ack-to-DOM=10.3ms, next frame=16.7ms; DOM elements=17138
verdict target: group 74/74, chosen from the envelope
slice medians (5 runs): navigation=200.0ms, next frame=212.6ms; ack-to-DOM=17.9ms, next frame=24.8ms; DOM elements=13143
production medians (5 runs): navigation=150.2ms, next frame=156.3ms; ack-to-DOM=10.3ms, next frame=16.7ms; DOM elements=17138
RESULT: PASS
```
