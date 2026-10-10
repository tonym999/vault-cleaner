import json, sys, urllib.request
sys.path.insert(0, ".")
import harness
from dev import preload
out = sys.argv[1]
with harness.live_spike() as live:
    preload(live, "real")
    req = urllib.request.Request(f"{live.origin}/api/report", headers={"Cookie": f"vault_cleaner_session={live.session.session_token}"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
json.dump(data, open(out, "w"))
arm = [s for s in data["snapshot"]["sections"] if s.get("armor")][0]
ex, ss = arm["armor"]["exact_duplicate_groups"], arm["armor"]["same_stat_groups"]
print(len(ex), len(ss), len(arm["decisions"]))
print(json.dumps(ex[0], indent=1)[:2500])
print(json.dumps(ss[0], indent=1)[:2500])
