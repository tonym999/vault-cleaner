# Issue #137 evidence: Jinja server-rendered review seam

Verbatim transcripts for the experiments behind
[docs/review-rendering-architecture.md](../../review-rendering-architecture.md).
Each `bash` fence is one command, run from the repository root, and the
`text` fence under it is that command's complete output. Nothing below was
edited after capture.

Everything here uses the fake fixtures under `tests/fixtures/`. No real
export was read. The proof code is in
[spikes/issue-137/](../../../spikes/issue-137/README.md).

Captured 2026-10-03 on the implementation branch for #137, and captured
again in full after fix round 1 changed the proof code. The proofs print
no port, path, timestamp or timing, so a rerun on the same versions prints
the same text; after capture every fence was rerun and compared with the
text recorded here.

Ids such as `6032` and `8201` in the transcripts are the fake instance ids in
the committed fixtures. `18446744073709551615`, `007` and `9"<'> x` are the
hostile ids experiment E2 substitutes.

## Environment

The interpreter, libraries and browser every transcript below was produced with.

```bash
.venv/bin/python - <<'EOF'
import importlib.metadata as metadata
import platform
import sys

from playwright.sync_api import sync_playwright

print(platform.system(), "Python", sys.version.split()[0])
for name in ("flask", "jinja2", "werkzeug", "playwright"):
    print(name, metadata.version(name))
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
jinja2 3.1.6
werkzeug 3.1.8
playwright 1.62.0
chromium 151.0.7922.34 (headless)
```

## Template rules

Scans the template bytes for the constructs the plan forbids. The scanner first proves each rule fires on a snippet that breaks it.

```bash
.venv/bin/python spikes/issue-137/check_templates.py
```

Output:

```text
self-test rejects filter safe: <p>{{ name|safe }}</p> -> rejected
self-test rejects filter safe: <p>{{ name | safe }}</p> -> rejected
self-test rejects filter tojson: <td data-x="{{ value|tojson }}"></td> -> rejected
self-test rejects filter urlize: <p>{{ note|urlize }}</p> -> rejected
self-test rejects filter xmlattr: <td{{ attributes|xmlattr }}></td> -> rejected
self-test rejects filter filesizeformat: <td>{{ id|filesizeformat }}</td> -> rejected
self-test rejects filter round: <td>{{ id|round }}</td> -> rejected
self-test rejects filter safe: {% set text = name|safe %} -> rejected
self-test rejects filter block: {% filter upper %}{{ name }}{% endfilter %} -> rejected
self-test rejects interpolated URL attribute: <a href="{{ link }}">x</a> -> rejected
self-test rejects interpolated URL attribute: <a href="/item/{{ id }}">x</a> -> rejected
self-test rejects interpolated URL attribute: <img src='{{ link }}'> -> rejected
self-test rejects interpolated URL attribute: <form action="{{ target }}"></form> -> rejected
self-test rejects Markup: {{ Markup(name) }} -> rejected
self-test rejects autoescape block: {% autoescape false %}{{ name }}{% endautoescape %} -> rejected
self-test rejects filter int: <td data-id="{{ id|int }}"></td> -> rejected
self-test rejects filter float: <td>{{ id | float }}</td> -> rejected
self-test rejects style attribute: <span style="width: {{ w }}%"></span> -> rejected
self-test rejects event handler attribute: <button onclick="go()">x</button> -> rejected
self-test rejects inline script: <script>go()</script> -> rejected
self-test rejects non-literal template name: {% include name %} -> rejected
self-test rejects non-literal template name: {% extends "base-" ~ kind ~ ".html" %} -> rejected
self-test rejects non-literal template name: {% from source import macro %} -> rejected
self-test rejects unquoted attribute interpolation: <td data-id={{ id }}></td> -> rejected
self-test rejects unquoted attribute interpolation: <td {{ attributes }}></td> -> rejected
self-test accepts: <td class="a" data-id="{{ id }}">{{ name }}</td> -> accepted
self-test accepts: <script src="/assets/x.js" defer></script> -> accepted
self-test accepts: <link rel="stylesheet" href="/assets/review.css"> -> accepted
self-test accepts: <td data-member-id="{{ kind }}:{{ id }}" data-count="{{ count }}"></td> -> accepted
self-test accepts: {% from "_verdict.html" import verdict_cell %} -> accepted
self-test accepts: <button type="button"{% if frozen %} disabled{% endif %}>Approve</button> -> accepted
self-test accepts: {#- a comment may mention |safe and style= -#}<p>{{ text }}</p> -> accepted
templates on disk: ['_armor_group.html', '_verdict.html', 'armor_duplicates.html', 'shell.html', 'whole_page.html']
environment allow-list: ['_armor_group.html', '_verdict.html', 'armor_duplicates.html', 'shell.html', 'whole_page.html']
_armor_group.html: 4995 bytes, 40 interpolations, findings=[]
_verdict.html: 2578 bytes, 30 interpolations, findings=[]
armor_duplicates.html: 1298 bytes, 13 interpolations, findings=[]
shell.html: 2613 bytes, 0 interpolations, findings=[]
whole_page.html: 2186 bytes, 8 interpolations, findings=[]
RESULT: PASS
```

Every rule rejects its bad snippet and accepts the clean ones. That includes any filter at all (`tojson`, `urlize`, `xmlattr`, `filesizeformat` and `round` among them) and any interpolation inside a URL-bearing attribute. The five templates on disk are exactly the environment's allow-list and have no finding. `shell.html` has no interpolation at all.

## Template environment, and the shell-only shape

Compares Flask's own `render_template` with the spike's explicit environment, then renders the production shell through Jinja.

```bash
.venv/bin/python spikes/issue-137/proof_environment.py
```

Output:

```text
-- autoescape, by template name --
flask render_template probe.html: escaped=True
flask render_template probe.html.j2: escaped=False
flask render_template probe.j2: escaped=False
flask render_template probe.txt: escaped=False
flask render_template with a misspelt key: '<p></p>'
flask loader: FileSystemLoader over 1 directory
explicit environment (autoescape is not chosen by name): escaped=True
-- undefined --
explicit environment with a misspelt key: UndefinedError: 'misspelt' is undefined
-- loader --
allow-list: ['_armor_group.html', '_verdict.html', 'armor_duplicates.html', 'shell.html', 'whole_page.html']
explicit get_template('../render_env.py'): TemplateNotFound: ../render_env.py
explicit get_template('/etc/hostname'): TemplateNotFound: /etc/hostname
explicit get_template('templates/shell.html'): TemplateNotFound: templates/shell.html
explicit get_template('missing.html'): TemplateNotFound: missing.html
explicit get_template('shell.html'): 'shell.html'
-- filters and globals that would break the opaque-id or escaping rule --
stock jinja2 {{ id|int }}: '18446744073709551615'
explicit environment {{ id|int }}: TemplateAssertionError: No filter named 'int'.
stock jinja2 {{ id|float }}: '1.8446744073709552e+19'
explicit environment {{ id|float }}: TemplateAssertionError: No filter named 'float'.
stock jinja2 {{ id|filesizeformat }}: '18.4 EB'
explicit environment {{ id|filesizeformat }}: TemplateAssertionError: No filter named 'filesizeformat'.
stock jinja2 {{ name|safe }}: '<b>x</b>'
explicit environment {{ name|safe }}: TemplateAssertionError: No filter named 'safe'.
stock jinja2 {{ name|tojson }}: '"\\u003cb\\u003ex\\u003c/b\\u003e"'
explicit environment {{ name|tojson }}: TemplateAssertionError: No filter named 'tojson'.
stock jinja2 {{ name|urlize }}: '&lt;b&gt;x&lt;/b&gt;'
explicit environment {{ name|urlize }}: TemplateAssertionError: No filter named 'urlize'.
stock jinja2 {{ {'onclick': name}|xmlattr }}: ' onclick="&lt;b&gt;x&lt;/b&gt;"'
explicit environment {{ {'onclick': name}|xmlattr }}: TemplateAssertionError: No filter named 'xmlattr'.
explicit {{ id }}: '18446744073709551615'
stock jinja2: 54 filters, 6 globals; explicit environment: 0 filters, 0 globals
stock jinja2 <td data-x="{{ name|tojson }}"></td>: <td data-x=""\" onmouseover=\"alert(1)""></td>
explicit environment {{ lipsum(1) }}: UndefinedError: 'lipsum' is undefined
-- shell-only shape --
production shell: 3881 bytes, 0 template tags; rendered through Jinja equals its own source: True
RESULT: PASS
```

Flask escapes by file extension and renders a misspelt key as nothing. The explicit environment escapes whatever the name, raises on a misspelt key, refuses any name outside its allow-list, and has no filter and no global at all, so `|int`, `|float`, `|filesizeformat`, `|safe`, `|tojson`, `|urlize`, `|xmlattr` and `lipsum()` cannot be used. The stock `tojson` line shows why removing three named filters was not enough: its output closes a double-quoted attribute. The production shell contains no template tag, so rendering it through Jinja returns its own bytes: the shell-only shape changes nothing by itself.

## E1: rendered parity (gate G1)

For each of the four slice fixtures, uploaded through the real upload route: a normalised projection of `#vc-duplicate-list` (every element, every attribute, every non-blank text node, each button's `disabled` state) from the production page and from the spike page, on the same session. Repeated after one proposal is approved and one vetoed.

```bash
.venv/bin/python spikes/issue-137/proof_e1_parity.py
```

Output:

```text
armor_close.csv (no verdicts): groups=2 tables=4 buttons=22 nodes=363 equal=True
  declared differences: empty class attributes production=4 jinja=0; data-vc-* attributes production=0 jinja=90
armor_close.csv (one approved, one vetoed): groups=2 tables=4 buttons=22 nodes=363 equal=True
  declared differences: empty class attributes production=4 jinja=0; data-vc-* attributes production=0 jinja=90
armor_duplicates_ui.csv (no verdicts): groups=1 tables=2 buttons=8 nodes=259 equal=True
  declared differences: empty class attributes production=20 jinja=0; data-vc-* attributes production=0 jinja=31
armor_duplicates_ui.csv (one approved, one vetoed): groups=1 tables=2 buttons=8 nodes=259 equal=True
  declared differences: empty class attributes production=20 jinja=0; data-vc-* attributes production=0 jinja=31
armor_same_stat_ui.csv (no verdicts): groups=1 tables=2 buttons=14 nodes=209 equal=True
  declared differences: empty class attributes production=8 jinja=0; data-vc-* attributes production=0 jinja=59
armor_same_stat_ui.csv (one approved, one vetoed): groups=1 tables=2 buttons=14 nodes=209 equal=True
  declared differences: empty class attributes production=8 jinja=0; data-vc-* attributes production=0 jinja=59
armor_same_stat_four_ui.csv (no verdicts): groups=1 tables=2 buttons=26 nodes=374 equal=True
  declared differences: empty class attributes production=30 jinja=0; data-vc-* attributes production=0 jinja=115
armor_same_stat_four_ui.csv (one approved, one vetoed): groups=1 tables=2 buttons=26 nodes=374 equal=True
  declared differences: empty class attributes production=30 jinja=0; data-vc-* attributes production=0 jinja=115
RESULT: PASS
```

Equal for all four fixtures, with and without verdicts. Two differences are declared and counted, and nothing else differs: production writes an empty `class=""` attribute where a cell has no class (`el()` assigns `className`), which Jinja does not; and the Jinja markup carries `data-vc-*` attributes (the stable control key, the verdict id, both sets of verdict texts, and the filter values) that production does not.

## E2: hostile content (gate G2)

Every free-text string, every stat name, every id and every hash of a real envelope is replaced with a hostile value; the fragment route renders it and the browser installs it.

```bash
.venv/bin/python spikes/issue-137/proof_e2_hostile.py
```

Output:

```text
-- overlay --
free-text and stat-name strings replaced: 558
ids replaced: 32; hashes replaced: 15
special ids in use: ['18446744073709551615', '007', '9"<\'> x']
special hashes in use: ['4294967295', '"><img src=x onerror=alert(3)>']
replaced strings the slice prints: 40
fields the slice prints: ['fingerprint', 'guardian_class', 'holofoil', 'item_archetype', 'location', 'name', 'protection_level', 'protection_reason', 'reason', 'seasonal_mod', 'spirit_signature', 'stats (stat name)', 'tuning_mod_slot', 'tuning_stat', 'type']
fields replaced but never printed by this slice: ['archetype', 'best_archetype', 'candidate_tuning_mod_slot', 'equippable', 'note', 'original_notes', 'original_tag', 'path', 'proposal_reason', 'selected_tuning_mod_slot', 'sha256', 'slot', 'tag']
-- spike page: Jinja fragment installed with DOMParser + importNode --
elements created from hostile text inside the list: script=0 img=0 b=0
script elements in the document: 1 (the page's own)
replaced strings found verbatim in the DOM: 40 of 40
literal '{{7*7}}' present, never evaluated: True
data-member-id values byte-identical to the envelope: True
printed member ids byte-identical to the envelope: True
data-group-id values byte-identical to the envelope: True
printed hashes byte-identical to the envelope: True
data-vc-verdict-id values are envelope ids byte-identical to the envelope: True
distinct member ids in the DOM: ['007', '18446744073709551615', '6031"<\'> 3', '9"<\'> x']
-- verdict request for each special id (intercepted, never sent) --
id '18446744073709551615': sent as str, equal=True, quoted in the request body=True
id '007': sent as str, equal=True, quoted in the request body=True
id '9"<\'> x': sent as str, equal=True, quoted in the request body=True
-- parity with production's createElement/textContent DOM --
hostile envelope: Jinja projection equals production projection: True
dialogs: []
CSP violation events: []; CSP console messages: []
-- code-path fields refuse hostile values --
hostile group_kind: ContextError: be exact_duplicate
hostile disposition: ContextError: an unsupported disposition
numeric member id: ContextError: sections[0].armor.exact_duplicate_groups[0].members[0].id must be a string
-- control: the same context with escaping switched off --
control elements inside the list: script>0=True img>0=True b>0=True
control dialogs: []
control CSP violation directives: ['img-src', 'script-src-attr']
-- the fragment route when the builder refuses an envelope --
GET fragment with a hostile disposition in the envelope: HTTP 500 application/json
body: {"error":{"code":"internal_error","message":"internal server error"}}
Cache-Control: no-store; CSP present: True
body names the field, the payload, a file or a traceback: False
GET /api/report on the same session afterwards: HTTP 200
RESULT: PASS
```

No element was created from hostile text, no dialog opened and no CSP violation was reported. Every replaced string the slice prints is in the DOM verbatim, including the literal `{{7*7}}`. Ids and hashes are byte-identical in attributes, in text and in the verdict request body, where `18446744073709551615` and `007` stay quoted strings. The projection equals production's `createElement`/`textContent` DOM for the same hostile envelope. A hostile `group_kind` or `disposition` and a numeric id are refused by the context builder. The control shows the detectors are live: with escaping off, elements are created, and the insertion step and the CSP still stop script (`img-src` and `script-src-attr` violations, no dialog). Fields this slice never prints (`note`, `original_notes`, `tag`, and the rest listed in the transcript) were replaced but had nothing to prove here. The last block shows what a client gets when the builder refuses an envelope: the production handler's bare `internal_error` 500, with the security headers, naming neither the field nor the payload, and the session still answers afterwards.

## E3 and E4: acknowledged state only, and no stale fragment (gate G3)

E3 lets the unmodified `POST /api/verdicts` commit, holds its response, and compares the rendered verdict state before and during. E4 forces `stale_verdicts` and `stale_report` from a second tab and a re-upload, then serves fragments and envelopes whose revisions disagree.

```bash
.venv/bin/python spikes/issue-137/proof_e3_e4_mutation.py
```

Output:

```text
-- E3, repaint=r1 --
before: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
response held; server verdict_revision=1, server verdicts=[{'id': '6032', 'verdict': 'approved'}]
while held: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
while held: verdict state unchanged=True; every verdict button disabled=True; status text=''
after release: 2 cells, approve,veto,unset pressed=true,false,false text='approved'; status='Approve acknowledged for 1 item(s).'
after Veto: 2 cells, approve,veto,unset pressed=false,true,false text='vetoed'; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
after Clear: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'; server verdicts=[]
fragment log: ['fragment accepted: report 1 verdict 0']
-- E3, repaint=r2 --
before: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
response held; server verdict_revision=1, server verdicts=[{'id': '6032', 'verdict': 'approved'}]
while held: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
while held: verdict state unchanged=True; every verdict button disabled=True; status text=''
after release: 2 cells, approve,veto,unset pressed=true,false,false text='approved'; status='Approve acknowledged for 1 item(s).'
after Veto: 2 cells, approve,veto,unset pressed=false,true,false text='vetoed'; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
after Clear: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'; server verdicts=[]
fragment log: ['fragment accepted: report 1 verdict 0', 'fragment accepted: report 1 verdict 1', 'fragment accepted: report 1 verdict 2', 'fragment accepted: report 1 verdict 3']
-- E3, repaint=r3 --
before: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
response held; server verdict_revision=1, server verdicts=[{'id': '6032', 'verdict': 'approved'}]
while held: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
while held: verdict state unchanged=True; every verdict button disabled=True; status text=''
after release: 2 cells, approve,veto,unset pressed=true,false,false text='approved'; status='Approve acknowledged for 1 item(s).'
after Veto: 2 cells, approve,veto,unset pressed=false,true,false text='vetoed'; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
after Clear: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'; server verdicts=[]
fragment log: ['fragment accepted: report 1 verdict 0', 'fragment accepted: report 1 verdict 1', 'fragment accepted: report 1 verdict 2', 'fragment accepted: report 1 verdict 3']
-- E4 stale responses, repaint=r1 --
stale_verdicts: tab A status='Your veto was not applied because this review is stale. Repeat the action.'
stale_verdicts: tab A shows tab B's verdict: 2 cells, approve,veto,unset pressed=true,false,false text='approved'
stale_verdicts: tab A's own action not shown: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
stale_verdicts: server verdict_revision before=1 after=1; server verdicts=[{'id': '6081', 'verdict': 'approved'}]
stale_verdicts: fragment log: []
stale_report: tab A status='Your approve was not applied because this review is stale. Repeat the action.'
stale_report: groups now rendered=['exact_duplicate:8201']; cells left for the old member=0
stale_report: server verdicts=[]
stale_report: fragment log: ['fragment accepted: report 2 verdict 2']
-- E4 stale responses, repaint=r2 --
stale_verdicts: tab A status='Your veto was not applied because this review is stale. Repeat the action.'
stale_verdicts: tab A shows tab B's verdict: 2 cells, approve,veto,unset pressed=true,false,false text='approved'
stale_verdicts: tab A's own action not shown: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
stale_verdicts: server verdict_revision before=1 after=1; server verdicts=[{'id': '6081', 'verdict': 'approved'}]
stale_verdicts: fragment log: ['fragment accepted: report 1 verdict 1']
stale_report: tab A status='Your approve was not applied because this review is stale. Repeat the action.'
stale_report: groups now rendered=['exact_duplicate:8201']; cells left for the old member=0
stale_report: server verdicts=[]
stale_report: fragment log: ['fragment accepted: report 2 verdict 2']
-- E4 stale responses, repaint=r3 --
stale_verdicts: tab A status='Your veto was not applied because this review is stale. Repeat the action.'
stale_verdicts: tab A shows tab B's verdict: 2 cells, approve,veto,unset pressed=true,false,false text='approved'
stale_verdicts: tab A's own action not shown: 2 cells, approve,veto,unset pressed=false,false,true text='Unreviewed'
stale_verdicts: server verdict_revision before=1 after=1; server verdicts=[{'id': '6081', 'verdict': 'approved'}]
stale_verdicts: fragment log: ['fragment accepted: report 1 verdict 1']
stale_report: tab A status='Your approve was not applied because this review is stale. Repeat the action.'
stale_report: groups now rendered=['exact_duplicate:8201']; cells left for the old member=0
stale_report: server verdicts=[]
stale_report: fragment log: ['fragment accepted: report 2 verdict 2']
-- E4 fragment and envelope revisions disagree --
captured fragment headers={'Vault-Cleaner-Report-Revision': '1', 'Vault-Cleaner-Verdict-Revision': '0'}; server now at report 1 verdict 1
trailing fragment: log=['fragment discarded: rendered for report 1 verdict 0; adopted report 1 verdict 1', 'fragment accepted: report 1 verdict 1']
trailing fragment: stale markers installed=0; 2 cells, approve,veto,unset pressed=true,false,false text='approved'
leading fragment: log=['fragment discarded: rendered for report 1 verdict 1; adopted report 1 verdict 0', 'fragment accepted: report 1 verdict 1']
leading fragment: 2 cells, approve,veto,unset pressed=true,false,false text='approved'
never-matching fragment: outcome='refused: fragment and envelope did not converge'; discards=3; stale markers installed=0; groups still rendered=2
RESULT: PASS
```

While the response is held the server already has the verdict (`verdict_revision=1`) and the page still shows `Unreviewed`; only the in-flight gate (every verdict button disabled) has changed. The state moves when the response arrives, for all three mechanisms. A stale action is announced as not applied, is not replayed (the server's verdict revision is unchanged), and the page shows the other client's verdict or the new report. A fragment whose headers trail or lead the adopted envelope is discarded and the page re-synchronises; one that never matches is refused after three attempts and the list is left as it was.

## E5: repaint mechanisms (gate G4)

For each mechanism at 1440 px and 390 px: focus a verdict button, press Enter, wait for the acknowledgement, then measure focus, node identity, the three persistent live regions and tab order.

```bash
.venv/bin/python spikes/issue-137/proof_e5_repaint.py
```

Output:

```text
r1 at 1440px (columns table active):
  focused control is the same node after the ack: True; old node still in the document: True
  focus is on the equivalent control: True (active element: button, aria-pressed=true)
  list elements still in the document: 225 of 225
  list mutation records during the ack: child nodes added=0 removed=0 attribute changes=40 text changes=2
  live regions: #vc-status same node=True writes=1; #vc-reconciliation same node=True writes=0; #vc-duplicate-scope same node=True writes=0
  tab order unchanged: True (17 stops); Tab from the control reaches the next stop: True
r1 at 390px (rows table active):
  focused control is the same node after the ack: True; old node still in the document: True
  focus is on the equivalent control: True (active element: button, aria-pressed=true)
  list elements still in the document: 225 of 225
  list mutation records during the ack: child nodes added=0 removed=0 attribute changes=40 text changes=2
  live regions: #vc-status same node=True writes=1; #vc-reconciliation same node=True writes=0; #vc-duplicate-scope same node=True writes=0
  tab order unchanged: True (17 stops); Tab from the control reaches the next stop: True
r2 at 1440px (columns table active):
  focused control is the same node after the ack: False; old node still in the document: False
  focus is on the equivalent control: True (active element: button, aria-pressed=true)
  list elements still in the document: 0 of 225
  list mutation records during the ack: child nodes added=9 removed=9 attribute changes=54 text changes=0
  live regions: #vc-status same node=True writes=1; #vc-reconciliation same node=True writes=0; #vc-duplicate-scope same node=True writes=0
  tab order unchanged: True (17 stops); Tab from the control reaches the next stop: True
r2 at 390px (rows table active):
  focused control is the same node after the ack: False; old node still in the document: False
  focus is on the equivalent control: True (active element: button, aria-pressed=true)
  list elements still in the document: 0 of 225
  list mutation records during the ack: child nodes added=9 removed=9 attribute changes=54 text changes=0
  live regions: #vc-status same node=True writes=1; #vc-reconciliation same node=True writes=0; #vc-duplicate-scope same node=True writes=0
  tab order unchanged: True (17 stops); Tab from the control reaches the next stop: True
r3 at 1440px (columns table active):
  focused control is the same node after the ack: True; old node still in the document: True
  focus is on the equivalent control: True (active element: button, aria-pressed=true)
  list elements still in the document: 225 of 225
  list mutation records during the ack: child nodes added=0 removed=0 attribute changes=76 text changes=2
  live regions: #vc-status same node=True writes=1; #vc-reconciliation same node=True writes=0; #vc-duplicate-scope same node=True writes=0
  tab order unchanged: True (17 stops); Tab from the control reaches the next stop: True
r3 at 390px (rows table active):
  focused control is the same node after the ack: True; old node still in the document: True
  focus is on the equivalent control: True (active element: button, aria-pressed=true)
  list elements still in the document: 225 of 225
  list mutation records during the ack: child nodes added=0 removed=0 attribute changes=76 text changes=2
  live regions: #vc-status same node=True writes=1; #vc-reconciliation same node=True writes=0; #vc-duplicate-scope same node=True writes=0
  tab order unchanged: True (17 stops); Tab from the control reaches the next stop: True
RESULT: PASS
```

R1 and R3 keep the focused control (the same node) and every list element. R2 destroys all 225 list elements, including the focused button, and then puts focus on the equivalent new button by its key. All three leave `#vc-status`, `#vc-reconciliation` and `#vc-duplicate-scope` as the same nodes, write the status region once, and leave tab order unchanged.

## E6: orientation switch on Jinja markup (gate G5)

Repeats the production orientation, keyboard-reachability and no-sideways-scroll checks against the spike page at 1440, 1024 and 390 px, for two, three and four members, beside the production page for the same session.

```bash
.venv/bin/python spikes/issue-137/proof_e6_orientation.py
```

Output:

```text
review.css container thresholds (rem): {2: 38.5, 3: 51.0, 4: 63.5, 5: 76.0, 6: 88.5}
-- armor_same_stat_ui.csv: 2 members, threshold 38.5rem --
1440px: container content box jinja=1156px production=1156px; threshold=616.0px; active table jinja=columns production=columns
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=12, in the accessibility tree=6
  document scrollWidth=1440 (viewport 1440); matrix scroller overflow-x=auto
1024px: container content box jinja=932px production=932px; threshold=616.0px; active table jinja=columns production=columns
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=12, in the accessibility tree=6
  document scrollWidth=1024 (viewport 1024); matrix scroller overflow-x=auto
390px: container content box jinja=315.61px production=315.61px; threshold=616.0px; active table jinja=rows production=rows
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=12, in the accessibility tree=6
  document scrollWidth=390 (viewport 390); matrix scroller overflow-x=auto
flip search: columns first shown at viewport jinja=708px production=708px; container just below=615px (rows=True), at the flip=616px (columns=True); narrowing again shows rows=True
-- armor_duplicates_ui.csv: 3 members, threshold 51.0rem --
1440px: container content box jinja=1156px production=1156px; threshold=816.0px; active table jinja=columns production=columns
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=6, in the accessibility tree=3
  document scrollWidth=1440 (viewport 1440); matrix scroller overflow-x=auto
1024px: container content box jinja=932px production=932px; threshold=816.0px; active table jinja=columns production=columns
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=6, in the accessibility tree=3
  document scrollWidth=1024 (viewport 1024); matrix scroller overflow-x=auto
390px: container content box jinja=315.61px production=315.61px; threshold=816.0px; active table jinja=rows production=rows
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=6, in the accessibility tree=3
  document scrollWidth=390 (viewport 390); matrix scroller overflow-x=auto
-- armor_same_stat_four_ui.csv: 4 members, threshold 63.5rem --
1440px: container content box jinja=1156px production=1156px; threshold=1016.0px; active table jinja=columns production=columns
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=24, in the accessibility tree=12
  document scrollWidth=1440 (viewport 1440); matrix scroller overflow-x=auto
1024px: container content box jinja=932px production=932px; threshold=1016.0px; active table jinja=rows production=rows
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=24, in the accessibility tree=12
  document scrollWidth=1024 (viewport 1024); matrix scroller overflow-x=auto
390px: container content box jinja=315.61px production=315.61px; threshold=1016.0px; active table jinja=rows production=rows
  inactive table: offsetParent null=True, refuses focus=True; active table accepts focus=True; verdict buttons in DOM=24, in the accessibility tree=12
  document scrollWidth=390 (viewport 390); matrix scroller overflow-x=auto
RESULT: PASS
```

The Jinja markup measures exactly as production at every width. The active table is the one `review.css` selects for the container's content box and the per-count threshold; the two-member flip happens at a 616 px content box (38.5rem) on both pages and reverses. The inactive table has no `offsetParent`, refuses focus, and contributes no button to the accessibility tree (half the DOM's buttons are exposed). The document never scrolls sideways and the matrix keeps its own `overflow-x: auto` scroller.

## E7: templates from an installed wheel (gate G6)

Builds wheels from a temporary copy of the tracked source with the templates overlaid, installs one into a fresh environment, and renders and serves from the installed package.

```bash
.venv/bin/python spikes/issue-137/proof_e7_wheel.py
```

Output:

```text
-- nested ui/templates/, package-data as it is today --
package-data: "vault_cleaner.ui" = ["*.css", "*.html", "*.js"]
wheel files under vault_cleaner/ui/: ['vault_cleaner/ui/__init__.py', 'vault_cleaner/ui/review.css', 'vault_cleaner/ui/review_server.html', 'vault_cleaner/ui/review_server.js', 'vault_cleaner/ui/review_ui.js']
templates in the wheel: 0 of 5
-- nested ui/templates/, proposed package-data --
package-data: "vault_cleaner.ui" = ["*.css", "*.html", "*.js", "templates/*.html"]
templates in the wheel: ['vault_cleaner/ui/templates/_armor_group.html', 'vault_cleaner/ui/templates/_verdict.html', 'vault_cleaner/ui/templates/armor_duplicates.html', 'vault_cleaner/ui/templates/shell.html', 'vault_cleaner/ui/templates/whole_page.html']
installed into a fresh environment; editable install: False
vault_cleaner imported from the fresh environment: True; from the repository: False
allow-listed templates present as package resources: 5 of 5
shell served (HTTP 200, text/html): True
fragment served (HTTP 200, text/html): True
fragment carries the wheel-only marker: True
fragment renders the uploaded report: True
fragment revision header equals the envelope: True
fragment keeps the production CSP: True
-- flat, beside the existing ui/ resources, package-data as it is today --
templates in the wheel: 5 of 5; files now directly under vault_cleaner/ui/: 10
RESULT: PASS
```

With today's `package-data`, a nested `ui/templates/` directory is left out of the wheel (0 of 5). With `"templates/*.html"` added, all five are packaged; the fresh environment imports `vault_cleaner` from itself, not the repository, finds every template as a package resource, and serves the shell and the fragment, the fragment carrying a marker that exists only in the wheel's copy. A flat layout is packaged without a `pyproject.toml` change but puts the templates beside the served assets.

## E8: request envelope and headers (gate G7)

Raw HTTP requests against every spike route, then Chromium over the whole slice.

```bash
.venv/bin/python spikes/issue-137/proof_e8_headers.py
```

Output:

```text
-- production root page --
Cache-Control: no-store
Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
CSP equals vault_cleaner.server.app.SERVER_CSP: True
-- spike routes --
/spike/: 200 text/html; charset=utf-8; security headers equal production: True
  no cookie: 401 authentication_required; wrong Host: 400 invalid_host; wrong Origin: 403 invalid_origin; POST: 404 not_found; POST without Origin: 403 invalid_origin
/spike/assets/spike.js: 200 text/javascript; charset=utf-8; security headers equal production: True
  no cookie: 401 authentication_required; wrong Host: 400 invalid_host; wrong Origin: 403 invalid_origin; POST: 404 not_found; POST without Origin: 403 invalid_origin
/spike/assets/whole.js: 200 text/javascript; charset=utf-8; security headers equal production: True
  no cookie: 401 authentication_required; wrong Host: 400 invalid_host; wrong Origin: 403 invalid_origin; POST: 404 not_found; POST without Origin: 403 invalid_origin
/spike/assets/spike.css: 200 text/css; charset=utf-8; security headers equal production: True
  no cookie: 401 authentication_required; wrong Host: 400 invalid_host; wrong Origin: 403 invalid_origin; POST: 404 not_found; POST without Origin: 403 invalid_origin
/spike/fragments/armor-duplicates: 200 text/html; charset=utf-8; security headers equal production: True
  no cookie: 401 authentication_required; wrong Host: 400 invalid_host; wrong Origin: 403 invalid_origin; POST: 404 not_found; POST without Origin: 403 invalid_origin
/spike/whole: 200 text/html; charset=utf-8; security headers equal production: True
  no cookie: 401 authentication_required; wrong Host: 400 invalid_host; wrong Origin: 403 invalid_origin; POST: 404 not_found; POST without Origin: 403 invalid_origin
-- fragment route parameters --
?kind=exact: 200
?kind=bogus: 400 bad_request
?template=shell.html: 400 bad_request
?kind=all&kind=exact: 400 bad_request
?guardian_class=xxxx...(201 characters): 400 bad_request
/spike/whole?kind=exact: 400 bad_request
revision headers on the fragment: {'Vault-Cleaner-Report-Revision': '1', 'Vault-Cleaner-Verdict-Revision': '0'}
-- Chromium, whole slice --
/spike/: CSP violation events=[]
/spike/?repaint=r2: CSP violation events=[]
/spike/?repaint=r3: CSP violation events=[]
/spike/?filters=server: CSP violation events=[]
/spike/whole: CSP violation events=[]
CSP console messages across the slice: []
control (an inline style attribute set on purpose): events=['style-src-attr'], console messages=1
RESULT: PASS
```

Every spike route returns the same five security headers as the production root page, and the CSP equals `SERVER_CSP`. Every route refuses a missing cookie (401), a wrong Host (400), a wrong Origin (403) and a POST. The fragment route accepts only its two filter parameters. Chromium reports no CSP violation in any mode; the control (an inline style set on purpose) is detected.

## E9: the whole-page shape

A verdict on `/spike/whole`, which requests the document again after the acknowledgement.

```bash
.venv/bin/python spikes/issue-137/proof_e9_whole_page.py
```

Output:

```text
before the verdict: focus on 'columns:exact_duplicate:6032:approve'; scrollY=746; filter text='unsent filter text'; status='Report loaded.'
server verdicts: [{'id': '6032', 'verdict': 'approved'}]; rendered aria-pressed on the new document: true
after the reload: active element=body key=None
after the reload: scrollY=746
after the reload: filter text=''
after the reload: status='Report loaded.'
after the reload: the old document's objects survived=False; #vc-status is the node that was there before=False
after the reload: the next Tab lands on 'vc-dup-search'
-- script-free form post --
submitting <form method=post action=/api/verdicts>: CSP violation events=['form-action']; navigated=False; server verdict_revision before=1 after=1
CSP console messages: 1
-- bytes per acknowledged verdict --
whole document: 17390; fragment: 16267; JSON envelope: 24537
RESULT: PASS
```

After the reload the new document shows the acknowledged verdict, and Chromium restored the scroll position. Focus is on `body` (the next Tab starts from the top of the page), the unsent filter text is gone, the status region is a new node holding its load-time text, so the acknowledgement message was never in it. A script-free form post is blocked by `form-action 'none'` and changes nothing on the server, so this shape still needs script to post.

## E10: filter ownership (gate G8)

The group-kind selector and the Class facet, implemented both ways and compared with production.

```bash
.venv/bin/python spikes/issue-137/proof_e10_filters.py
```

Output:

```text
-- the same filter in production, candidate (a) and candidate (b) --
no filter: all three agree=True; groups=['exact_duplicate:6031', 'same_stat:6081']; headings=['Exact duplicates', 'Same stats, different tuning']
  scope: 2 groups · 4 pieces
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected=''
kind=exact: all three agree=True; groups=['exact_duplicate:6031']; headings=['Exact duplicates']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected=''
kind=same_stat: all three agree=True; groups=['same_stat:6081']; headings=['Same stats, different tuning']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected=''
class=Titan: all three agree=True; groups=['exact_duplicate:6031']; headings=['Exact duplicates']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to class Titan
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected='Titan'
kind=exact, then class=Titan: all three agree=True; groups=['exact_duplicate:6031']; headings=['Exact duplicates']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates, class Titan
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected='Titan'
class=Hunter: all three agree=True; groups=['same_stat:6081']; headings=['Same stats, different tuning']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to class Hunter
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected='Hunter'
kind=same_stat, then class=Hunter: all three agree=True; groups=['same_stat:6081']; headings=['Same stats, different tuning']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups, class Hunter
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected='Hunter'
class=Titan, then kind=same_stat: all three agree=True; groups=['same_stat:6081']; headings=['Same stats, different tuning']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected=''
class=Hunter, then kind=exact: all three agree=True; groups=['exact_duplicate:6031']; headings=['Exact duplicates']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected=''
reconciliation message after the dropped class: all three agree=True; 'Local view state dropped: duplicate filter guardianClass Hunter.'
-- requests per filter change --
(a) browser: 0 request(s)
(b) server: 1 request(s)
-- the same filter after the server has stopped --
production: filter applied=True; groups shown before=2 after=1; status='Connected — report loaded with server-backed verdict controls.'
(a) browser: filter applied=True; groups shown before=2 after=1; status='Connected — report loaded.'
(b) server: filter applied=False; groups shown before=2 after=2; status='Filters need the review server, which could not be reached.'
-- line counts (non-blank lines between the experiment markers) --
candidate (a): JavaScript 62, Python 0
candidate (b): JavaScript 27, Python 63
-- production filter code this would replace --
review_ui.js:747-771 (25 lines) function matchesArmorGroup: found at that line=True
review_ui.js:773-777 (5 lines) function filterArmorGroups: found at that line=True
review_ui.js:779-802 (24 lines) function countArmorGroups: found at that line=True
review_server.js:221-238 (18 lines) function armorGroupValueStillExists: found at that line=True
review_server.js:240-252 (13 lines) function armorGroupsForKind: found at that line=True
review_server.js:254-261 (8 lines) function armorGroupKinds: found at that line=True
review_server.js:263-275 (13 lines) function reconcileArmorQueryForGroups: found at that line=True
review_server.js:277-281 (5 lines) function countGroupPieces: found at that line=True
review_server.js:283-310 (28 lines) function duplicateScopeText: found at that line=True
review_server.js:1284-1296 (13 lines) function duplicateOptions: found at that line=True
total: 152 lines
RESULT: PASS
```

Both candidates show the same groups, headings, scope sentence, Class options and selected class as production for every case, including the last two, where production recounts the Class options for the selected kind and drops a class that kind lacks, and all three report the drop with the same message. Candidate (a) makes no request per filter change and still filters after the server has stopped, as production does. Candidate (b) makes one request per change and cannot filter once the server is gone. Line counts are for the two measured filters only, with recount-and-drop implemented in both candidates.

## E11: finalise and reset (gate G3)

`POST /api/finalize` changes `state` and `override_status` and leaves both revisions and the fingerprint alone. The proof checks that the fragment does not depend on either, and that a page with the fragment already installed reaches the right presentation from the envelope.

```bash
.venv/bin/python spikes/issue-137/proof_e11_finalize.py
```

Output:

```text
-- finalise --
POST /api/finalize: 200
envelope before: state=reviewing report=1 verdict=1 active persisted vetoes=[]
envelope after:  state=finalized report=1 verdict=1 active persisted vetoes=['6032']
fragment revision headers equal before and after: True
fragment bytes equal before and after: True (16263 and 16263 bytes)
page before it learns of the finalise: text='vetoed' pressed=false,true,false all disabled=False
page after adopting the envelope: text='Vetoed this session · active persisted veto still suppresses this item' pressed=false,true,false all disabled=True
fragment requests made to get there: 0 []
finalised: production loaded fresh equals the spike page with its fragment already installed=True; equals the spike page loaded fresh=True
-- reset --
POST /api/reset: 200; state=idle report=2 verdict=2
page after adopting the envelope: groups rendered=0; fragment log=['fragment accepted: report 2 verdict 2']
-- a new report while the saved veto is active --
envelope: state=exports-loaded report=3 active persisted vetoes=['6032']
page after adopting the envelope: text='Active persisted veto still suppresses this item' pressed=false,false,true all disabled=False; fragment log=['fragment accepted: report 3 verdict 2']
active saved veto: production loaded fresh equals the spike page with its fragment already installed=True; equals the spike page loaded fresh=True
RESULT: PASS
```

Across a finalise the fragment's revision headers and its bytes are both unchanged, so equal revision pairs mean equal fragments. The installed page shows the pre-finalise text until it adopts the new envelope; it then shows the persisted-veto wording with every verdict button disabled, having made no fragment request, and equals production loaded fresh. Reset bumps the report revision, so the ordinary report-change path replaces the fragment. A report loaded while the saved veto is active is also equal to production.

## JavaScript keep/remove line ranges (gate G8)

Every range the decision record's keep/remove map cites, checked against the files at this head, and the size of what the spike wrote for the slice.

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

Every anchor is found at its cited line. The slice replaces 908 lines of production JavaScript. In its place the spike has 93 lines of fragment seam and 62 lines of browser-owned filtering in JavaScript, a 474-line Python context builder and 187 lines of templates.
