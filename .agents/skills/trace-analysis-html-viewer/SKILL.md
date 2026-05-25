---
name: trace-analysis-html-viewer
description: Create a standalone HTML viewer for ManiScope user trace analysis artifacts, especially User Reasoning Forests, Recommendation Plan Forests, reasoning graphs, trace-step maps, screenshots, and Markdown reports. Use when asked to visualize or browse trace-analysis outputs in a local HTML file.
---

# Trace Analysis HTML Viewer

Use this skill to create a local, standalone HTML page for browsing artifacts from the `user-trace-analysis` workflow. The common output is `TRACE/analysis-results/trees.html`, but adapt the filename when the user asks for a different viewer.

## Inputs

Prefer these artifacts under `TRACE/analysis-results/` when present:

- `user-reasoning-forest.json`: descriptive forest rooted at Hypotheses.
- `recommendation-plan-forest.json`: prescriptive forest rooted at reasoning gaps or expansion sources.
- `reasoning-graph.json` and `recommendation-plan-graph.json`: canonical shared-node sources for cross-checking.
- `analysis-report.md`, `trace-step-map.md`, `user-reasoning-forest.md`, `recommendation-plan-forest.md`: readable context and labels.
- `../images/`: raw trace screenshots referenced through `screenshot:../images/...` provenance.
- `continued-investigation-assets/` or another assets folder under `analysis-results`: rendered follow-up images referenced through `render:<relative-path>` provenance.

If an artifact is missing, make a useful partial viewer rather than blocking. State which inputs were omitted.

## Viewer Requirements

Build an actual analysis artifact browser, not a decorative page.

- Use a standalone HTML file that works from `file://`.
- Embed JSON data directly in the page unless the user asks for external JSON loading. This avoids local CORS failures.
- Render User Reasoning Forest and Recommendation Plan Forest separately.
- Show tree views left-to-right with nodes arranged by depth and leaves vertically spaced.
- Color nodes by `kind` and links by `relation`.
- Keep all trees open by default.
- Provide search and forest filtering when both user and plan forests are available.
- Put node details in a modal opened by clicking a node. Do not rely on a table below the graph for primary details.
- If node provenance contains `screenshot:<relative-path>` or `render:<relative-path>`, show the actual image in the modal and keep the path as caption text.
- When `reasoning-graph-patch-*.json` or augmented graph metadata identifies agent-created follow-up nodes, make those patch nodes visually distinct in the tree and show patch file, patch run, actor, source, and `planRef` in the modal. Users should not need to infer patched nodes from naming conventions alone.
- If an augmented graph contains new agent-created Hypothesis roots, do not duplicate those roots in the general augmented user forest. Show the general augmented forest as original user roots with patch nodes mixed in, and show new agent-created roots only in a separate executed adjacent hypothesis forest.
- Keep evidence/provenance visible by default. Do not hide it behind a toggle unless the user asks.
- Support zoom buttons, trackpad pinch where supported, and `Cmd/Ctrl + scroll` zoom inside the tree viewport.
- Set initial zoom by fitting the smaller tree dimension to the viewport, leaving the larger dimension scrollable.
- Preserve pointer-centered zoom so the content under the cursor remains stable.

## Terminology Legend

Use the `user-trace-analysis` terminology matrix for node legends:

| Scope | Intention Space | Action Space | Finding Space |
|---|---|---|---|
| Low | Task | Interaction, RecommendedInteraction | Finding |
| Mid | AnalyticQuestion | AnalyticActivity | Finding |
| High | Hypothesis | InvestigationStrategy | Finding |

Notes:

- `RecommendedInteraction` is a plan-side analogue of `Interaction`.
- `ExpectedFinding` is a plan target, not evidence. Put it outside or alongside the core matrix if needed.
- Put plan scaffold nodes such as `SourceNode`, `ReasoningGap`, and `ExpansionRationale` in a separate "Plan scaffold" legend group.
- Keep the relation legend separate from the node matrix.

## Implementation Steps

1. Inspect available artifacts with `rg --files TRACE/analysis-results TRACE/images` and identify JSON, Markdown, and image assets.
2. Validate JSON with `jq empty` before embedding it.
3. Read enough Markdown to understand the titles, forest purpose, and terminology. Do not blindly trust JSON labels if the report contradicts them.
4. Create the HTML with plain HTML, CSS, and browser JavaScript. Avoid adding a build step.
5. Escape embedded JSON safely. In JavaScript source, prefer assigning parsed JSON from a script-generated literal or a safely serialized value.
6. Implement layout from parent-child links:
   - Build node maps from `instanceId`.
   - Attach children using `parentInstanceId`.
   - Position by depth on x-axis and leaf order on y-axis.
   - Draw SVG Bezier links behind absolutely positioned node buttons.
7. Implement modal details:
   - Badges for `kind`, `scope`, `space`, relation, and expected-only status.
   - Image gallery above metadata rows when screenshot or render provenance exists.
   - Rows for instance ID, canonical ID, confidence, activity type, interaction type, source or target node, and evidence.
8. Implement zoom:
   - Scale a canvas inside a sized wrapper.
   - Adjust wrapper width and height to scaled dimensions so scrollbars remain correct.
   - Intercept `wheel` only when `event.metaKey` or `event.ctrlKey` is set.
   - Listen for `gesturestart` and `gesturechange` for WebKit-style pinch events.
9. Add compact visual polish:
   - Stable node dimensions.
   - Responsive table and modal behavior.
   - No nested decorative cards.
   - Text wraps without overflowing nodes or buttons.

## Validation

Before finishing:

- Run `git diff --check -- TRACE/analysis-results/trees.html`.
- Parse the embedded script with Node:

```bash
node <<'NODE'
const fs = require('fs');
const html = fs.readFileSync('TRACE/analysis-results/trees.html', 'utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)?.[1];
if (!script) throw new Error('missing script');
new Function(script);
console.log('script parses');
NODE
```

- Check that referenced screenshot paths exist for at least one screenshot-backed node.
- If browser verification is possible, open the HTML and click a screenshot-backed node to verify the modal renders the image. If `file://` browser access is blocked, say so and rely on static validation.

## Common Pitfalls

- Do not fit the initial zoom to the full tree height for tall trees; it makes nodes unreadably small. Fit the smaller tree dimension and leave the other dimension scrollable.
- Do not show only screenshot paths when images exist. Render the images.
- Do not collapse all details into a permanent table below the graph. Use click-to-open node modals.
- Do not use external libraries from CDNs for a local artifact viewer unless the user explicitly wants network-dependent output.
- Do not overwrite generated analysis artifacts while creating the viewer.
