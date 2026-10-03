// Experiment E9 only (#137): the whole-page shape.  A verdict is posted as
// JSON, because the CSP's `form-action 'none'` rules out a form post, and the
// document is requested again once the server acknowledges it.
(function () {
  "use strict";
  var body = document.body;
  var status = document.getElementById("vc-status");
  document.getElementById("vc-duplicate-list").addEventListener("click", function (event) {
    var button = event.target.closest("button[data-vc-verdict-value]");
    if (!button) return;
    var cell = button.closest("[data-vc-verdict-id]");
    var value = button.getAttribute("data-vc-verdict-value");
    fetch("/api/verdicts", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({
        report_revision: Number(body.getAttribute("data-report-revision")),
        verdict_revision: Number(body.getAttribute("data-verdict-revision")),
        fingerprint: body.getAttribute("data-fingerprint"),
        decisions: [{ id: cell.getAttribute("data-vc-verdict-id"), verdict: value === "" ? null : value }]
      })
    }).then(function (response) {
      if (!response.ok) { status.textContent = "Verdict was not applied."; return; }
      status.textContent = "Verdict acknowledged for 1 item(s).";
      window.location.reload();
    });
  });
})();
