# Jury interface delivery — 4 October 2026

Objective: make Next Experiment understandable and reviewable against the Databricks brief, repair the three verified Fable UI failures, and preserve the measured scientific evidence.

Acceptance: saved-result status and timestamp visible; invalid/missing data cannot leave working controls or loading text; condition switching retains the selected gene; plain-language product explanation; clear links from the panel to the executed Omnigent loop, measured result, sources, limitations and review package; readable desktop and narrow-screen layout; original calculations, evidence and TP53 warning preserved; source package rebuilt and verified.

This work does not generate new scientific results, run paid models, conduct biological experiments, publish, deploy or submit. Follow-up source reconciliation and multi-case decision-quality evaluation remain scientific development tasks.

| Task | Owner | Files | Acceptance | Status |
|---|---|---|---|---|
| U1 jury interface | coordinator | panel.html, panel.css, serve-demo.py | plain explanation, traceable loop, readable layout | complete |
| U2 reliable controls | panel_logic | panel.js, panel_render_check.js | three Fable fixes, meaningful regressions | complete |
| U3 review path | jury_trace | README, SUBMISSION, BRIEF-COMPLIANCE, index.html, JURY-REVIEW-MAP | current artifact map and honest claims | complete |
| U4 review audit | audit_fixes | verify_fable_review.py, identity tests, old report banner | API-error events rejected, old attribution corrected | complete |
| U5 integrate and verify | coordinator + independent review | release package, delivery record | combined tests, actual browser, package audit | complete |

Rollback snapshot: runs/pre-jury-ui-20261004T115044Z.tar.gz.

Verification:
- Main suite: 75 passed, 10 subtests passed.
- Final interface regression: six demo tests and 10 subtests passed after keyboard-focus and recorded-example gating fixes. All 24 gene/priority/condition combinations, missing/invalid JSON, pending fetch, optional fields and event handling are covered.
- Review identity: 13 targeted tests passed; API-error assistant messages fail closed.
- Real browser: desktop and 390px layout, condition preservation, native keyboard selection and replacement-button focus checked. Isolated missing-data page showed disabled controls, hidden workspace/recorded results, no loading text and no console errors. Temporary viewport override and fixture were removed.
- Independent review approved the combined change after focus and archive-script repairs.
- Final package: 90 manifest files; canonical README, all jury-map links, packaging script, current interface and every SHA256 checked. Extracted package passed 62 tests and 10 subtests with the pinned installed dependencies and a verified copy of the separately distributed public matrix. ZIP integrity and executable launcher mode passed. No paid model run.

The preview is local at http://127.0.0.1:6769/panel. A current desktop screenshot is `reviews/jury-ui-desktop.jpg`. The 119.8-second video shows the earlier interface and requires re-recording. The source discrepancy and multi-case scientific evaluation remain explicitly open; no new biological or agent-selection claims were introduced.
