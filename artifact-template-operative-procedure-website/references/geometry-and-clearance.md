# Geometry and clearance

Use the atlas in its native alignment. Record source object IDs, units, common region axes and transforms, and mesh coverage before modeling. Apply the saved object world matrix followed by a single region matrix. Correct triangle winding for a reflected combined transform on native meshes and on tessellated curves. The shared `transform_mesh` helper in `scripts/mesh_geometry.py` uses column-vector matrices. Transpose a row-vector source matrix once at the adapter boundary. Check representative vertex coordinates against the source, including both sides, before rendering. A mesh name alone does not establish that it covers the target region.

Fit additions to native surfaces. Use `axis_crossings` to inspect adjacent contours and lumen boundaries. Use closed, separately registered surfaces where possible. Confirm that cords and nerves follow the canal and openings and clear surrounding bone at rest and with adjacent bone motion. When atlas coverage is incomplete, label any reconstruction explicitly and identify the native landmarks that support it. Verify both sides before reusing a mirrored illustration.

Use native skin and muscle depth relationships to fit the superficial envelope, layered incision and flap hinges. Check neutral, opening, retraction, release and closure poses. Sample both flap surfaces, the margins and the neighboring tissue. Refit a scalp or skin surface that clips through the tissue beneath it. Keep normal apposition, attachment and deliberate cutting contact visible.

Fit hardware against the local native support surfaces. Center the footprint on the intended load-bearing anatomy and sample the full contact belt, including triangle interiors where coarse faces can cut across curved bone. Verify the entry point and shape against the applicable technique. Test screw and anchor terminal points in their designated bone, and check their actual trajectories for neighboring bone and neural or vascular structures. A tip-only check gives no information about a shaft. For an instrument, specify entry, shaft axis, working tip, working corridor and intended contacts from evidence and landmarks. Test the full instrument at each sampled phase, including insertion and withdrawal. An interbody decompression tool, for example, follows the open disc space to the target. A tool or implant may have permitted contact with its designated tissue or hardware component.

## Cranial windows and dura

Fit the dural bed to sampled inner-table and cortical surfaces, with the flap base on the documented attachment. Keep the stationary dural margin and the moving leaf complementary. Reveal the incision before curling the leaf and use the same deformation for rendering, picking, labels and reverse closure. Check open, closed and intermediate poses against the rim, scalp, brain and venous sinuses.

Keep the native cortical bone appearance on both ordinary tables. Limit cut-face shading to the actual kerf and verify that it never appears on uncut backfaces. Lift a discrete bone flap free of the fixed rim before carrying it away. Carry the inner table, outer table and cut edges as one object, then reuse the motion in reverse for replacement. Check the fully seated state for seams, duplicate surfaces and exposed interiors.

## Sample and check

Use the finished site’s state to sample each variant, operative side and relevant layer context. Sample the separate Before frame, start, end, every intermediate boundary where motion or visibility changes, and intermediate poses through each nonlinear movement. Include sufficient resolution near narrow spaces. Export model-space triangles with the same cut and deformation as the renderer. Include the full geometry for both the shaft and working tip. The audit measures strict triangle crossings in sampled poses. Check coplanar overlaps, enclosed meshes, self-intersection, clinical relevance and continuity between samples separately.

Run:

```sh
python3 scripts/check_geometry.py --meshes project/data/mesh-data.json \
  --plan project/research/geometry-plan.json --report project/research/geometry-report.json \
  --clearance-data project/data/clearance-data.json
```

The scripts use Python and NumPy. Keep the plan and report in working research files. The deployable JSON contains only the mesh IDs and visibility conditions.

- `restPairs` lists native and added mesh pairs that must clear at rest.
- `fixation` entries have a `body` mesh ID and a `tip` with optional `seatedPoints`, in checked model coordinates. Use a closed target volume and include points along the seated hardware.
- Each `steps` entry has a `key` and `frames`. A frame has `progress` (0 through 1, or `"before"`) and `meshes`, keyed by mesh ID with optional `offset` and optional explicit `triangles` in the same coordinates. Omit unavailable meshes from that frame. Use explicit triangles for cuts, rotations and deformations, or use an offset for pure translation. Include at least two available playback poses for each moving mesh. Key the template by sorted URL-encoded variant properties joined with `&`, operative side, and step ID, separated by `|`. For example, `clinoid=none&fissure=yes&muscle=subfascial|right|position`. In the retained unilateral template, Both displays both sides and uses the right operative side. Other adaptations may choose their own stable key if their runtime and producer agree.
- `contactPairs` lists reviewed intentional contact. `checkPairs` includes stationary pairs that must clear during the step. Moving pairs are automatically audited. `hideStationaryPairs` explicitly allows an incidental stationary object to be hidden if it intersects a moving participant. Approve display exclusions only after auditing the true geometry. In particular, fix an instrument or implant path through protected anatomy even if an explanatory view later hides nearby context. The audit reports unresolved crossings and exits unsuccessfully.

A moving participant retains visibility when a conflict is handled by a display exclusion. Use the union of overlaps over the entire step, including replay and slider scrubbing. If both participants move, keep both visible and correct their geometry or timing. Apply the same whole-step rules to rendering, picking, labels and 2D capture. Recompute at step/configuration/side/layer changes. Preserve layer preferences. Do not toggle an object on or off halfway through its step based on the current frame. For adaptations with progress-dependent availability (a tool enters or an implant becomes visible), evaluate whether an object belongs to the entire step independently of its current progress.

## Worked cervical example

Use `assets/examples/acdf/build_anatomy.py Startup.blend --output <project-data-directory>` to regenerate the ACDF anatomy example from the pinned atlas. It is an example for C4–7 ACDF and the documented teaching variants. Use the workflow and helpers above to fit a different region, anatomy dataset, procedure or implant. The example includes the cervical canal/foramina fit, deep instrument routes, the anterior incision and superficial layers, contoured interbody cages and central fixation. The detailed native cord asset in the example atlas does not cover the required cervical span. The illustration follows native dura and bony contours, and proximal roots are identified as illustrative. The native vertebral arteries retain their atlas courses, with small intersecting surfaces at C4 that remain a documented source limitation.

Run `python3 assets/examples/acdf/check_fit.py <project-data-directory>/mesh-data.json` for the example's canal and root clearance during distraction, seated cages and grafts, fixation tips, and sampled Kerrison trajectories. The last line reports the native C4 arterial crossings separately.

### Minimal motion plan

The example below allows a moving flap to hide an incidental static context surface if the actual sampled triangles cross. The three samples use the mesh record geometry plus the given translation. A curving flap needs explicit deformed triangles in each sampled frame. Replace the mesh IDs and make the case-specific sampler emit the same stage and side keys as the renderer.

```json
{
  "steps": [{
    "key": "clinoid=none&fissure=yes&muscle=subfascial|right|scalp-flap",
    "hideStationaryPairs": [["flap", "context"]],
    "frames": [
      {"progress": 0, "meshes": {"flap": {}, "context": {}}},
      {"progress": 0.5, "meshes": {"flap": {"offset": [0, 1, 0]}, "context": {}}},
      {"progress": 1, "meshes": {"flap": {"offset": [0, 2, 0]}, "context": {}}}
    ]
  }]
}
```
