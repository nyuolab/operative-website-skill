# Website fidelity and content contract

The retained source is the visual and behavioral baseline. Preserve its CSS tokens, spacing, compact card shape, controls, toolbar and overall arrangement. Default output is an educational anatomy guide for a general audience; no developer terminology in ordinary controls or guide cards.

## Layout

- Compact header with the procedure's Title Case name, without a final period. Remove old case-specific titles and subtitles.
- Desktop: about 70% interactive model, 30% Guide / Indications / Papers panel. Fill viewport height and keep the outer page from scrolling; allow internal scrolling in the guide and layer panel. Smaller screens stack model/content within a dynamic-height viewport with usable internal scrolling. Give the model all remaining height after a compact reader showing the active step title and first two sentences; measure the active card at the current width, with a reasonable cap for short screens. Recompute on resize and rotation. Keep the outer page fixed.
- No bottom educational/source/offline status strip, no green configuration box over the model, no list or gallery of “12 models,” no redundant configuration subtitle.
- For a requested family, compact and clearly labeled “Choose the Surgical Approach” options at the top. For one procedure, omit this block entirely and reclaim its vertical space. Do not replace it with a pointless one-option dropdown.
- Box the Papers count as a number badge. Retain obvious active states and keyboard access.

## Mobile controls and reading

On mobile, hide automatic anatomy labels by default, while preserving one label when a user taps a structure and an optional labels checkbox in the layer menu. Do not show the top-left model/step title or isolated-context tag above the small identification prompt. Preserve the page's compact procedure title.

At the bottom of the model, show only Reset View and the Layers & View opener next to one another. Hide bottom orientation-preset buttons and the stage/status strip. Retain the model's upper mode/action controls. Move Previous / Next beside the Guide / Indications / Papers tabs; keep this navigation semantically separate from the tablist. Selecting Next from another tab returns to Guide. Each active step, including the final step, must start at the top of the internal guide panel immediately below the tabs; leave sufficient scroll space after the last card to allow that alignment. Avoid scrolling the outer page.

The Layers & View menu opens upward from the dock, stays aligned within the horizontal viewport and scrolls internally. Its maximum height, padding and borders must fit the actual space above the dock; do not impose a minimum larger than the available space. Keep all existing Relevant / All controls and side options in it. Restore the desktop control locations when the breakpoint changes; move the existing elements rather than duplicating their IDs or event handlers. Keep desktop and mobile automatic-label preferences separately.

## Guide steps

Use the reference's action granularity. Its 27 steps distinguish: identify target/landmark; position and fix head; prepare and mark; drape; incise; preserve layers; mobilize the selected tissue plane; reflect and secure flap; raise periosteum; place burr holes; treat bone edges; detach dura; raise bone flap; flatten an obstructing ridge; place tack-up sutures; open the selected dural window; selected intradural exposure/clinoid work/cisternal work; and individual reconstruction stages through skin closure. This is a **granularity benchmark**, not a sequence to impose on other procedures.

Separate an action when it changes an important plane, exposure, instrument, risk relationship or reconstruction state. A step should do one comparable thing and explain why. Combine minor sub-actions only when they belong to the same operative transition. Use a short action title and 2–4 concise sentences. Keep cards compact enough to scan without long stretches of empty space. Do not put an entire approach, “perform surgery,” or unmodeled lesion treatment in one vague card. Do not add unsupported patient-specific angles, drug doses or exact measurements.

Every step needs a useful model state plus a visible change or relevant marking where possible. Do not claim that a symbol is a physical reconstruction. If a positioning/draping step lacks the actual frame/drapes geometry, a clear schematic orientation or boundary is acceptable, with its limit in credits/visualization details. No step should silently show a stale unrelated illustration. Default guide notes should be empty; omit the removed “Reference anatomy; only the highlighted opening or tissue displacement is illustrated” sentence.

## Indications

Explain which targets and exposure requirements suit the procedure and, for a family, each requested subtype. Distinguish pathology indications from soft-tissue preferences. Clicking an option must change the actual corresponding configuration and focus the relevant step; keyboard Enter/Space must do the same. In a single-procedure guide, clicking an indication can focus its pertinent exposure/target step without inventing variants.

## Model, sides and layers

- Retain Right / Left / Both under clearly named Procedure Side / Context. A unilateral procedure uses the chosen side; Both shows bilateral context and operates on the right. Preserve native left/right anatomy; do not reflect unilateral pathology or asymmetric anatomy and call it native. Midline procedures retain appropriate bilateral context and their actual midline path.
- Step and variant changes preserve the complete camera: orientation quaternion, camera frame, distance, pan, target and lens zoom. The selected context side persists too. Reset View and Home restore the full opening view and clear pan while keeping the active step, patient pose, layers and progress. Directional buttons use the opening distance and magnification. Surgeon’s View uses its own explicit distance and magnification. Recommended View and Focus Change apply the active step’s view, which can be a close-up. All camera presets use the launch anatomy pivot. Do not include the removed Operative View action. Preserve the separate Patient Position Anatomical/Operative toggle and sliders, Surgeon's View, orientation gizmo and schematic holder/table. The Position step can deliberately show the head-positioning transition; ordinary navigation must otherwise preserve the user's view. Side changes must not erase prior user choices unnecessarily.
- Each tissue category has two independent checkboxes: Relevant for the operative subset and All for available regional anatomy on the chosen side. Use categories that fit the new case, including fascia, muscle, bone, neural tissue, dura/membranes, vessels and nerves where applicable. All is a scope of available head/spine/other regional structures, not a promise of a complete atlas. No Relevant Only toggle or Restore Step Layers control.
- Recommended views keep the relevant unmanipulated brain, arteries and nerves enabled consistently across steps, subject to real geometric occlusion. For other regions use the analogous stable structures. Reflected or removed tissue follows cumulative procedure state.
- Full Head Context / Full Spine Context / other appropriate Full Context expands the currently enabled categories and restores the previous All selections when toggled back. Partial scope has a mixed state. Enabling All must not operate on or displace contralateral/context-only tissues.
- Every anatomically important layer referenced by the guide must be represented, or the omission explicitly identified. Do not silently mention fascia or interposed fat absent from the model. When native geometry is unavailable, fit a clearly documented original illustration with honest specificity.

## Zoom and touch

Use the bundled Pterional PR #1 controls throughout each simulation. A one-pointer drag rotates around the fixed anatomy center. Shift/right-drag pans. Two fingers pan, pinch to zoom and twist to roll. Alt/Option-drag and Q/E roll, arrow keys rotate, plus/minus zoom and Home resets. Wheel, pinch and keys use lens magnification in the 0.25–16× range. Use view-space pan in both rendering and label projection. Clear prior pan at every view preset. Start a drag at five CSS pixels of displacement from the press and clear the gesture on cancellation, lost capture or window blur. Preserve complete framing through ordinary step navigation and 2D Figures mode.

Keep interaction frames responsive on complex meshes: while a pointer gesture is active, render the visible scene only and do not run the picking render or synchronous `readPixels` label-visibility pass. Keep render resolution and shader quality stable and suppress picking for the entire held gesture, including pauses longer than 140 ms. Debounce label and picking restoration until 140 ms after final pointer release. Keep click picking immediate, and do not leave the picker or labels stale after a gesture settles. Use GPU/browser profiling to diagnose any remaining cost; do not promise a frame rate without measured data.

## Lifelike tissues and motion

Preserve the default Surgical palette and Atlas teaching colors, tissue-specific shading, baked ambient occlusion and the low-precision shader fallback. Keep native anatomy separate from illustrative additions and decorative surface patterns. Preserve the layered scalp/subcutaneous slab, galea, areolar gap and pericranium, surface-fitted fascia/fat/dura, veins and arachnoid where relevant to the new procedure. Keep progressive incision, CPU/GPU-matched flap curl/peel, and separate galeal and skin closure. Preserve the PR's smooth surface-following outlined markings and their stage/arc-length reveals. Do not turn these into rigid translations or merely describe the effects in prose. See [the reuse map](lifelike-reference.md) for implementation locations and limits.

## Markings and instruments

Mark each meaningful maneuver with an anatomical landmark, trajectory, opening, displacement, region boundary, suture/fixation symbol or other appropriate representation. Circle a named landmark; trace a planned incision; actually develop burr holes; animate the correct dissection/opening/displacement. The visible highlight should identify the change itself, especially small deep bone work. Opening and closure states must persist correctly downstream. Before hides only the current change and its current instruments/markers; previously completed steps remain.

Cyan instruments should be large enough to see at their active stage and positioned/directed toward the actual action region. Use anatomically plausible schematic approaches; avoid presenting a straight illustrative tool as a validated safe trajectory. Do not silently pass tools through bone, nerves or vessels where the step has not established a corridor. The Instruments checkbox under Layers & View is the sole instruments toggle. Replay and the progress slider animate the relevant region without resetting the user's camera.

## Labels and 2D

One anatomical part is labeled at a time, in Title Case with medical abbreviations preserved. Desktop can show an automatic step label; mobile defaults to no automatic label and retains tap-to-identify. Keep its label box stable on the screen as the model rotates; attach its leader to retained visible points in the procedure-relevant region. Label an artery where it matters to the step, not a remote neck segment. Do not duplicate a structure or bounce labels between multiple boxes. When the intended region is occluded, avoid drawing a leader through solid anatomy; keep a stable understandable label state. Picking and visible labels must use the same depth/masks, including high-DPI screens and after camera changes.

In **2D Figures**, show a bundled original source figure for every active step and variant, with the figure number, a concise caption, attribution and a publisher link. For a paper-specific case, use that paper’s figures. Label a related image when the paper does not illustrate the exact action. The tab opens directly to the images without a file picker. Keep the selected step and the camera when switching modes. The short step text stays visible. A single small **Details** dropdown contains one teaching paragraph and compact source links. Explain the approach and anatomy in the first step. Keep 3D anatomy labels and leader lines hidden in 2D Figures.

## Operative video disclosure

For a supplied operative video file, place a collapsed, keyboard-accessible Operative Video disclosure immediately above the Guide / Indications / Papers tabs. Expanding it pushes the tabs and reader below the player in normal flow; collapsing it restores their space. Fit the desktop panel and the mobile reader without clipping, overlap, or breaking internal scrolling. Include source attribution and native controls. Do not autoplay.

Map each actually shown guide step to a verified timestamp. Every change of the active step seeks to that time whether the disclosure is open or closed; preserve the user's paused/playing state and do not reset the model camera or other guide state. Queue the most recent seek until video metadata loads. A step absent from the footage is explicitly labeled as unavailable and has no invented seek. Video frames in 2D Figures are independently identified, timestamped and credited. Handle missing or unsupported media without blocking the guide.

## Clinical overview and reading expansion

Provide an Overview tab with a substantial, cited teaching page tailored to the operation or single-article case. Address anatomy, indications, preoperative reasoning, outcomes and complications with the specificity supported by the sources. Use clear, moderately advanced third-person clinical prose for a second-year medical student; avoid both oversimplified coaching and unsupported first-person expert preference. Separate an anatomical study's observations from clinical outcomes.

Keep the normal layout visual-first. An accessible boundary control expands the reading panel to approximately 60% of the desktop layout and restores the original split; the article uses the panel's available width. On mobile the expanded reader takes most of the vertical space without covering controls. Retain the active tab, step and camera when toggling.
