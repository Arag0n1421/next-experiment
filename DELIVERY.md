# Verified local delivery — 4 October 2026

## Outcome

The scientific lab has a matched computational benchmark, enforced Omnigent policies, a redesigned six-gene evidence panel and saved agent-run replay, a narrated 119.8-second walkthrough and a portable source package. The current interface explains the product, measurements, research roles and changed decision in plain language, with a review map for all five judging criteria. The existing video predates this interface update. These are local artifacts. No public repository, hosted deployment or HackOS submission is claimed.

## Verification

| Requirement | Evidence |
| --- | --- |
| Real bounded multi-agent run | Session `17559c08df9048fe8fb1e3fc4abe4ecd` completed and is idle. All three specialist child sessions exist and finished. |
| Enforced budget and provenance | Run `ede05eb6d8b549ddba04a08e7f684b49` used three of four attempts: candidate, triage and guide-check. All completed. Decision `b15ad66286d040f7a540af55f126d0f0` closes the run; an additional analysis was actually rejected as `Run is closed`. |
| Structured scientific choice | Two possible tests, explicit learning/feasibility/cost and selection reason, an executed test, evidence UUIDs and updated action are saved. |
| Matched improvement | 36,862 binary checklist decisions; zero disagreements with eager computation or existing scientific reference. LOO recomputations 111,274 to 11,739 (89.45% reduction). Five timing pairs: median 2.6311 to 0.6468 seconds, 4.068x checking-kernel speedup. |
| Policy tests | Atomic cross-process attempt caps, source/gene/run matching, successful evidence requirement, role capabilities, startup lifecycle, actual Omnigent ASK/DENY interface and closed-run rejection. No human approval was fabricated. |
| Full suite | Main project: 75 tests and 10 subtests passed. Final focus and recorded-example changes also passed the panel regression and targeted demo tests (six tests and 10 subtests); identity checks passed separately (13 tests). |
| Browser | Desktop and 390px mobile layout checked. Condition switching preserves the selected gene; keyboard selection retains focus; saved status and UTC timestamp are visible. Missing evidence disables controls, clears loading text, and hides recommendations and recorded figures, with no console errors. Failed benchmark validation suppresses improvement claims. Private routes return 404. |
| Video | Existing H264/AAC, 1600x1000, 119.796-second walkthrough passed full decode and visual review in the earlier delivery. It depicts the previous saved-run interface and must be re-recorded to show the current UI. |
| Source package | Rebuilt with 90 manifest files; ZIP integrity and every SHA256 checked; current interface/docs match; jury-map links resolve; launcher is executable. Extracted package passed 62 tests and 10 subtests using the existing pinned dependencies and a verified copy of the separately downloaded public matrix. Explicit allowlist excludes caches, credentials and raw account-linked sessions. |
| Independent review | Original runtime fixes retained. Current review verified saved-state labeling, failure handling, selection preservation, source attribution and review routes. It also found and resolved keyboard-focus loss and an omitted packaging script. |

The current interface delivery and rollback snapshot are recorded in `reviews/JURY-UI-DELIVERY.md`. The Fable review verifier now rejects API-error assistant messages even when they carry the expected model name. The old mixed-model report has a visible UNVERIFIED attribution banner; historical model output was preserved.

Machine-readable receipt: `runs/BOUNDED-VERIFICATION.json`. Full fresh run: `runs/verified/17559c08df9048fe8fb1e3fc4abe4ecd/`. Historical run used by the demo remains in `runs/verified-workflow/`; those are separate executions.

## Important scope

The benchmark measures deterministic early-stop execution of the same heuristic checklist. It establishes computational savings with the same binary decisions, not better biology or LLM reasoning. Early-stopped failures do not produce every later diagnostic. Shared setup (5.131 seconds), model inference and orchestration are outside kernel timings; no end-to-end agent speedup is claimed. Initial timing snapshot is retained separately, and the latest report is not selected for fastest timing.

The new scientific run still requests additional evidence for UBA3. Its proposed next measurement checks guide-specific UBA3 protein depletion and whether target engagement tracks count enrichment. The historical demo proposes guide-resolved perturbations in both IL6 conditions. Both remain proposed experiments; neither has been performed.

Model-dollar/token cost remains unknown and uncapped. The deadline rejects new admissions but does not interrupt computation already running. Permissions constrain the agents; this is not an OS sandbox against an owner who edits source or the ledger.

## Remaining external and research steps

Review the actual HackOS fields and source/data licensing, publish the intended repository/artifacts and submit. A future scientific evaluation should test decision quality or information gained under a matched budget, then seek independent biological validation. Literature APIs remain optional, unconnected extensions.
