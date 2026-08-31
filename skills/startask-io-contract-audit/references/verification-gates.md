# Verification Gates and Readiness

Use this reference before stating the first readiness conclusion. Re-read it after the scope card is frozen and before every completion or delivery claim. A gate passes only when its minimum evidence is recorded in the current turn. Record evidence that is present, missing, stale, conflicting, or not applicable; do not borrow a gate from a similar historical project.

## Gate model

| Gate | Name | Minimum passing evidence |
|---|---|---|
| G0 | Evidence inventory | Present, missing, stale, conflicting, and not-applicable evidence recorded |
| G1 | Static validation | Syntax/import/config/basic schema checks pass |
| G2 | Structural validation | Operator/annotation hierarchy, order, types, and counts match the frozen contract |
| G3 | Real small sample | Real data fields, enums, timeline, counts, and serialized values match the contract |
| G4 | Round-trip or visual | Coordinate inverse, RLE, point indexes, or geometry visualization satisfies declared invariants |
| G5 | Platform end-to-end | Actual platform import/default view/prelabel/export/platform validation passes |
| G6 | Customer acceptance | Customer environment, official validator, or formal acceptance evidence passes |

Start at G0 and stop at the highest consecutive gate supported by current-turn evidence. A later check cannot skip an earlier gate: report the lower unsupported gate and all higher gates as `not_verified`.

## Readiness vocabulary

Use exactly one value below. `highest_passed_gate` and `readiness` describe the evidence actually recorded, not a planned test level.

| Readiness | Use when |
|---|---|
| `DESIGN_ONLY` | The task has a proposed design or scope, but G0 evidence inventory is not complete. |
| `READY_FOR_IMPLEMENTATION` | G0 is complete, the material contract is frozen, and no critical conflict or missing evidence blocks implementation; no implementation verification gate has passed yet. |
| `BLOCKED` | A critical conflict, missing evidence, inaccessible required environment, or failed required check prevents the next claimed gate. State the blocker and the highest gate actually passed. |
| `LOCALLY_VERIFIED_ONLY` | G1, G2, G3, or G4 is the highest passed gate and there is no G5 evidence. |
| `PLATFORM_VERIFIED` | Gates G0 through G5 have passed consecutively; G6 has not passed. |
| `CLIENT_ACCEPTED` | Gates G0 through G6 have passed consecutively. |

Use `PLATFORM_VERIFIED` only after passing consecutively through G5, and use `CLIENT_ACCEPTED` only after passing consecutively through G6. Isolated later-gate evidence never promotes readiness when an earlier gate is unsupported. G1 through G4 prove only the stated local/static/sample/round-trip boundary, never platform or customer success.

## Data-type checklists

Apply the relevant checklist in addition to the gate model. Mark every inapplicable invariant explicitly as `NOT_APPLICABLE` with its reason.

### TEXT

- Verify the attachment shape (text value, record/list nesting, and required metadata) and its lineage from source record to serialized attachment.
- Verify operator order, annotation hierarchy, value types, enum mapping, turn/timeline order, and record counts against the frozen contract.
- Round-trip text escaping, Unicode/encoding, IDs, and source-to-output lineage without dropping or fabricating records.

### IMAGE

- Verify attachment shape, locator/metadata lineage, operator order, annotation hierarchy, types, and instance counts.
- Verify image width, height, channels/orientation, coordinate bounds, mask size, and image-to-annotation identity match the frozen contract.
- For masks, verify RLE/index decoding and re-encoding round-trip, mask dimensions, class/instance association, and output lineage.

### IMAGE_SEQUENCE

- Verify attachment shape, sequence/frame ordering, per-frame locator lineage, operator order, and annotation hierarchy.
- Verify each image size, frame ID, timestamp, and image-to-frame/pose alignment; do not align by array position alone.
- Verify per-frame mask size and RLE/index round-trip where masks exist, plus frame counts and source-to-output lineage.

### POINTCLOUD_SEQUENCE

- Verify attachment shape, point-cloud/frame ordering, operator order, annotation hierarchy, types, and per-frame counts.
- Verify frame ID, timestamp, pose/calibration alignment, coordinate convention, point count/order, and annotation-to-frame identity.
- Verify point indexes or geometry inverse/visual round-trip, bounds where declared, and source-to-output lineage.

### PointCloud_4D

- Verify attachment shape, continuous-frame timeline ordering, sensor/frame IDs, operator order, annotation hierarchy, and per-frame annotation counts.
- Verify timestamp, ego pose/calibration, coordinate frame, frame/pose alignment, point count/order, and track identity across frames.
- Verify point indexes or geometry inverse/visual round-trip, serialized temporal values, and lineage from every source frame to output attachment.

### semantic-segmentation2d

- Verify image attachment shape, operator order, semantic/instance annotation hierarchy, class enums, image size, and mask size.
- Verify mask-to-image identity, pixel-index conventions, RLE/index decode-and-encode round-trip, class/instance counts, and coordinate bounds.
- Verify source label, mask, image, and serialized output lineage; never replace unknown labels with a fallback class.

### semantic-segmentation3d

- Verify point-cloud attachment shape, operator order, semantic/instance annotation hierarchy, class enums, frame/pose alignment, and point count/order.
- Verify point-index conventions, index/RLE decoding and re-encoding round-trip, label cardinality, and point-cloud-to-annotation identity.
- Verify source point cloud, labels, frame IDs, and serialized output lineage; fail explicitly on unknown labels or mismatched point counts.

## Report template

```markdown
highest_passed_gate: G3
not_verified: G4, G5, G6
readiness: LOCALLY_VERIFIED_ONLY
evidence:
  - Real sample field and count checks passed
blockers:
  - Platform import and customer validator were not run
```

List only evidence actually observed in the current turn. `not_verified` must include every higher gate that lacks passing evidence, and `blockers` must explain what prevents the next required gate or delivery claim.
