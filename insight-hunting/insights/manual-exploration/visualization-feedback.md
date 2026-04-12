# ManiScope — Visualization Feedback from a Manual Exploration Pass

This is a companion to the ACT and PNUT exploration reports. Everything below is something I hit while trying to do the recommended workflow from `user-manual.en.md` end-to-end on both tokens. Each item lists the symptom, where I encountered it, the impact on investigation, and a suggested fix.

---

## Severity 1 — Things that block the headline workflow

### F1.1 — Token Distribution force layout collapses for some snapshots and for PNUT entirely

**Symptom:** All bubbles render stacked at the same point at the center of the inner ring instead of being spread out by the force-directed layout.

**Where seen:**
- ACT snapshot 2024-10-26 12:00 UTC after Update Snapshot + Run Detection (`act/screenshots/12a_layout_collapse_1026.png`)
- ACT snapshot 2024-10-19 18:00 UTC same recipe
- **PNUT default snapshot 2024-11-09 23:00 UTC, every time** (`pnut/screenshots/01a_td_collapse.png`)

**Impact:** The entire "scan red-vs-blue ratio, click the largest red node, look at the orange dashed clusters" half of the recommended workflow is unusable because all 191 PNUT bubbles overlap. The user effectively has to ignore the Token Distribution View on PNUT.

**Workaround I found:** dragging the Scale slider triggers a re-render. For ACT this was usually enough to settle the layout. For PNUT it just made the central blob slightly larger and never resolved into a real ring (`pnut/screenshots/02a_td_after_scale.png`).

**Suspected root cause (guess only):** the force simulation may be timing out before convergence on large graphs (191 nodes), or the radial-constraint force may be applying too strongly relative to the repulsion force when one bubble is much larger than the rest. Note that PNUT's biggest bubble is w=53 px while most are w<20 px — the size disparity may make collision-resolution fight the radial constraint.

**Suggested fix priorities:**
1. Make the layout deterministic and preview-able. Ship a "Layout: ready / running / stalled" status indicator so the user knows whether to re-trigger.
2. On Run Detection / coin switch / snapshot change, **always re-run the simulation from scratch with a fresh random seed** rather than reusing the prior state.
3. Budget more simulation iterations for large graphs (e.g. iterations ∝ √N).
4. Add a "re-layout" button in the Token Distribution header so users do not have to nudge the Scale slider as a workaround.

---

### F1.2 — Manipulation View cards/bars/bands are empty for PNUT despite per-user data being populated

**Symptom:** After switching to PNUT and re-running detection, the Manipulation View shows the literal empty-state strings **"No Round Trip manipulations"** and **"No Same Direction manipulations"**. The count bars above and below the K-line have zero child elements (verified via DOM inspection). The light blue band overlay has zero inner HTML.

**But:** clicking into any entity in the Token Distribution View loads a Behavior Detail panel with **389 manipulation-box elements** (verified by `document.querySelectorAll(".manipulation-box").length`) for a single entity click. So the per-user manipulation results clearly exist somewhere in the system — they are just not being aggregated into the global view.

**Where seen:** PNUT default snapshot 2024-11-09 23:00 UTC, after both Run Detection buttons clicked, after waiting through the "Detecting..." button transition.

**Impact:** This is the worst bug I found. The Manipulation View is the headline view of the dashboard — if it says "no manipulations" the user will reasonably conclude PNUT is clean. PNUT is **not** clean (see Finding 3 in the PNUT report). The dashboard is silently lying.

**Suggested fix priorities:**
1. **Stop rendering the empty-state text until you are certain detection has finished AND has actually returned zero events.** Right now it cannot distinguish "no events" from "the aggregator never received the per-user results".
2. The cards row, count bars row, and bands overlay clearly read from a different data source than the per-user Behavior Detail. **Unify them.** Either both should derive from the same `manipulation_results` object, or the cards row should aggregate the per-user data on the fly.
3. Until the underlying issue is fixed, please add a developer-visible log when the cards aggregator computes 0 from non-zero per-user data — that asymmetry should never happen silently.

---

### F1.3 — "single" classification in the Token Distribution disagrees with "Part of Entity" in the Behavior Detail (PNUT)

**Symptom:** I clicked a bubble whose DOM class was `bubble single ` (i.e., not classified as an entity member by the Token Distribution view). The Behavior Detail then loaded with **"Part of Entity, Members: 2"** in its header.

**Where seen:** PNUT, the bubble I clicked was `FjmRj8y9xfDaj5Aygq88t5jAFbpxrbZ16JNPPG1sx9FQ` — see `pnut/screenshots/06a_solo_TL.png`.

A related observation: clicking a bubble that *was* a member of a 5-bubble inner-ring `.group` showed "Part of Entity, Members: **13**". Five rendered members vs thirteen reported members.

**Impact:** Users cannot trust either view's entity classification on PNUT. They have to click the wallet to find out if it is "really" in an entity, defeating the purpose of the visual encoding.

**Suspected root cause:** the inner-ring renderer and the Behavior Detail header are reading entity assignments at different cache versions, or one of them filters wallets by some additional criterion (e.g., balance threshold) before showing them as members.

**Suggested fix:** make the entity assignment computation produce a single canonical mapping `wallet_id → entity_id`, store it once, and have both views read from the same source. Document any filtering rules in the UI ("3 of 13 members are above the Top Holders Threshold and shown here").

---

## Severity 2 — Things that significantly hurt usability

### F2.1 — Default Scale slider value (0.4) makes the inner ring uncomfortably small

**Symptom:** The inner ring at the default `Scale = 0.4` occupies only the central ~30% of the panel; ~70% of the Token Distribution panel area is empty light-blue background (`act/screenshots/01a_token_dist_default.png` shows this).

**Impact:** Wallet bubbles are hard to read at default scale. I had to keep adjusting the slider to either zoom in (read individual nodes) or zoom out (see the outer-ring related holders).

**Suggested fix:** default the slider to **0.7 or 0.8**. Or, better, auto-fit on initial render so the inner ring fills ~80% of the panel.

---

### F2.2 — K-line vertical space is too small to read individual candle wicks

**Symptom:** The candle SVG has a CSS height of ~100 px. At default 1H granularity, candles are 1 px wide and ~20 px tall, with thread-thin wicks. Without zooming or switching to 1W you cannot read the OHLC of individual periods.

**Where seen:** every snapshot, both tokens.

**Impact:** Forces a manual granularity switch on every session. The 1W view is the only one where candles become legibly tall.

**Suggested fix:** give the K-line at least 200 px of vertical space. Right now it shares the right column with the cards above and below; consider compressing the cards (smaller mini-timelines) so the K-line gets more height.

---

### F2.3 — Light blue connection bands are nearly invisible

**Symptom:** The "blue connection bands" linking each card to its candle on the K-line are very low-contrast against the also-light-blue manipulation tints on the K-line. I could see *that* there were diagonal bands in the screenshots, but I could not actually trace any single card to a specific candle without scrolling to a card and looking at it in isolation (`act/screenshots/04_kline_full.png`).

**Impact:** The manual itself flags this — "they are nevertheless the only visual element that links a card to a specific time region on the price chart, so it is worth training your eye to follow them." The fact that the manual has to coach users on how to see the bands is a usability red flag.

**Suggested fix:** make the band the same color as the connected card's accent color (e.g., a faint orange for round-trip top cards, faint pink for same-direction bottom cards), or use a thin stroked line at the top and bottom of the band so the trapezoid shape is at least outlined. Increase opacity from whatever-it-is to maybe 0.25–0.30.

---

### F2.4 — Hover tooltips on bubbles are not triggered by JavaScript-dispatched MouseEvents

**Symptom:** I tried to read tooltips programmatically by dispatching `mouseover` / `mouseenter` / `pointerover` events. None triggered the tooltip (tooltip element existed but stayed empty). Only **real CDP mouse moves** would have worked.

**Impact:** This is mostly a problem for me as an automation user — it forced me to click bubbles to see addresses (clicking populates the Behavior Detail header) instead of hovering. But it also means anything that wants to script the dashboard for testing or automation has to use real input events.

**Suggested fix:** if the tooltip uses Naive UI's `n-popover`, register on both `pointerenter` and `mouseenter` and accept synthetic events (set `passive: false` on the listener and check `event.isTrusted` only for security-sensitive actions, not for tooltip display).

---

### F2.5 — Tooltips can get "stuck" and cover other UI

**Symptom:** A tooltip from a previous hover stayed visible and overlapped the inner ring even after I moved the mouse / clicked elsewhere. I had to dispatch `mouseleave` events on every bubble to clear it. See the partial-tooltip overlap in `act/screenshots/01a_token_dist_default.png` early in my session.

**Impact:** Visual confusion when reviewing screenshots. Worse for users because the stuck tooltip blocks clicks on the underlying nodes.

**Suggested fix:** hide tooltips on `mouseleave` of the *parent SVG container*, not just the individual bubble. Add a `setTimeout(hide, 200)` debounce so the tooltip cannot get orphaned during fast mouse movement.

---

### F2.6 — Wallet labels in `simplified_owner_labels.json` are not surfaced anywhere

**Symptom:** The manual itself says: *"The dashboard does not currently surface wallet labels. The underlying data has labels in `simplified_owner_labels.json` that distinguish exchange wallets, contract wallets, and human wallets, but those labels are not yet shown in the UI."*

**Impact:** I spent several minutes investigating the largest ACT holder `6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237` and concluding it was a "passive whale" — but it could just as easily be a centralized exchange deposit address. Without labels, you cannot tell. This single change would significantly improve interpretation of the largest wallets, where false positives are most expensive.

**Suggested fix:** show the label in:
1. The hover tooltip in the Token Distribution View (top line, before the address).
2. The "User: ..." header in the Behavior Detail.
3. The mini-rows in each manipulation card.

Even just labeling exchange wallets as `[CEX]` and contracts as `[contract]` would change the investigative reading of every flagged event.

---

## Severity 3 — Polish

### F3.1 — Wallet labels in the Behavior Detail rows are truncated to 4 characters

**Symptom:** Row labels in the Behavior Detail use the first 4 characters of the address (e.g., `DmJ..`, `5YP..`, `BgB..`). With ~25 rows visible at once, address collisions across investigations are likely (e.g. two `5xx..` wallets in different sessions). And it makes cross-referencing hard between this view and the manipulation cards (which also use 4-char prefixes).

**Suggested fix:** use 6 characters at minimum, or hover-to-expand. Or, paired with F2.6, use the human-readable label when available and fall back to 6-char otherwise.

---

### F3.2 — Manipulation cards do not mark which wallets in the card belong to a clicked entity

**Symptom:** When the DmJ entity is selected in the Token Distribution, the Behavior Detail dims unrelated rows. But the manipulation cards above/below the K-line do not similarly highlight the cards that contain entity members. Cross-referencing "which cards belong to my selected entity" requires reading row labels and comparing them mentally.

**Impact:** Mid-investigation friction. The cards and the entity are decoupled even though they should be the most useful coordination signal.

**Suggested fix:** when an entity is selected, add a colored border or icon to every manipulation card whose participants intersect the entity. Maybe count the overlap: "3/9 wallets in selected entity".

---

### F3.3 — There is no global "summary" of detection counts

**Symptom:** To know "how many round-trip events did detection find?" I had to either count cards on screen or run JS to count `.manipulation-card` elements in the DOM. There is no badge anywhere saying "Detected 5 round-trip / 20 same-direction events."

**Impact:** Users cannot tell at a glance whether the detector found anything, especially in combination with F1.2 (PNUT shows 0 — is that "0 found" or "the aggregator is broken"?).

**Suggested fix:** put a small counter in the Manipulation View header: `Round Trip: 5 events · Same Direction: 20 events · 22 unique wallets flagged · $X.XM total flagged volume`. This single line would make F1.2 immediately diagnosable.

---

### F3.4 — The K-line shows dates outside the snapshot's "active" range without distinguishing them

**Symptom:** With snapshot at 2024-11-09 23:00, the K-line shows candles all the way out to ~2024-11-09. The visible `same-direction` card for the week 11/07 has stats `11/08 17:36 - 11/11 07:05` — i.e. **into 11/11, after the snapshot time**. So either the K-line/cards include events after the snapshot time, or the snapshot time only affects the holder population and not the time series.

**Impact:** Confused me for a while. I assumed the snapshot time was a "cut" but it appears to only be a "compute holder ranks at this point in time" parameter. The K-line's time domain is independent.

**Suggested fix:** add a vertical dashed line at the snapshot time on the K-line. Label it "Snapshot". Ideally also dim post-snapshot candles or mark them as "look-ahead." Or, document this clearly in the manual under "things that are not obvious from the UI."

---

### F3.5 — Manipulation count bar heights have no scale label

**Symptom:** The grey count bars above and below the K-line clearly encode "number of detected events per interval", but there is no y-axis label or tick marks. You can compare bar heights to each other but you cannot read absolute counts.

**Impact:** Hard to tell whether a "moderately tall bar" is 3 events or 30. Cross-token comparisons are impossible.

**Suggested fix:** label the y-max value (e.g. "max 8 events"). Or place a tick on the tallest bar.

---

## Severity 4 — Quirks I didn't fully understand and want to flag

### F4.1 — `Active Users: 51` for ACT default but only 51 visible bubbles → no aggregated "Others"

The manual describes an aggregated "Others" category at the outermost layer of the Token Distribution. I never saw it visually. Either it is rendered transparent/invisible, or it gets suppressed by default thresholds. Worth a sentence in the manual confirming when it appears.

### F4.2 — Earning bars in the Behavior Detail use a small height and are hard to read at default zoom

The red/green realized PnL bars under each user's action row are correctly placed but very thin (3701 of them in one panel render). When you have hundreds in a row they become a green/red speckle that is hard to read as profit/loss. Consider stacking by amount (cumulative) rather than per-event tick marks.

### F4.3 — Switching coins resets the Show Manipulation Boxes toggle silently

Or at least, the toggle's visual state changed between my ACT and PNUT sessions even though I do not remember explicitly toggling it. Worth verifying — if it does reset, mention it in the "things that are not obvious" section of the manual.

---

## Bug-vs-feature triage summary

| ID | Item | Type |
|---|---|---|
| F1.1 | TD layout collapse for PNUT and some snapshots | **Bug** |
| F1.2 | Empty Manipulation cards on PNUT despite per-user data | **Bug** (highest priority) |
| F1.3 | "single" vs "entity" disagreement on PNUT | **Bug** |
| F2.1 | Default Scale slider too small | UX |
| F2.2 | K-line vertical space too small | UX |
| F2.3 | Connection bands invisible | UX |
| F2.4 | JS-dispatched hover doesn't show tooltip | Automation/testing concern |
| F2.5 | Stuck tooltips | UX |
| F2.6 | No wallet labels in UI | Feature gap (already noted by manual) |
| F3.1 | 4-char label truncation | UX |
| F3.2 | Cards don't highlight selected entity | UX |
| F3.3 | No global detection summary | UX |
| F3.4 | K-line shows post-snapshot events | UX / docs |
| F3.5 | Count bars have no scale | UX |
| F4.x | Various quirks | Investigation needed |

Of these, **F1.2 is the only one I would recommend fixing before further user studies**, because it makes the dashboard actively misleading about PNUT and could happen on any other token whose detection volume is large enough to stress the aggregator.
