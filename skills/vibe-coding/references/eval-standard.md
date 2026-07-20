# Eval Standard

## Acceptance Eval and scored Eval

Every project has an `eval_full` acceptance gate. For ordinary deterministic
software, this is a versioned set of end-to-end acceptance cases derived from the
Business Owner-confirmed success scenarios; it may invoke existing deterministic
checks, but it must report the named cases and observed business outcomes rather
than merely aliasing a unit-test command.

Projects whose quality is probabilistic, scored, or business-effect based need the
additional scored Eval design below: algorithms, models, Agents, search, ranking,
classification, generation, automated decisions, or behavior whose success cannot
be fully expressed as deterministic assertions. Do not rename ordinary unit tests
as scored Eval, and do not force probabilistic metrics onto deterministic behavior.

## Design before implementation

`docs/eval-plan.md` always defines the acceptance cases. When scored Eval applies,
it additionally defines:

- business question and metric linkage;
- candidate input/output contract and eligibility rules;
- baseline and the minimum meaningful improvement;
- Golden Cases, edge/negative cases, permission and dependency failures, historical
  failures, and blocking examples;
- scoring rules, thresholds, confidence/variance treatment, and business meaning;
- independent holdout data and leakage controls;
- latency, cost, resource, privacy, and runtime constraints;
- exact command, environment, seed/randomness control, and evidence output.

Create the Eval harness and a baseline result before optimizing the complete
implementation. Do not choose thresholds only after seeing the candidate score.

## Run record

Every run captures dataset version, model/algorithm/dependency versions,
configuration, prompts where applicable, thresholds, environment, random seed or
sampling settings, commit, per-case output and score, aggregate metrics, blocking
failures, cost/latency/resource measures, and difference from baseline.

## Integrity

Do not use repeatedly tuned development examples as the only acceptance set,
modify the rubric to make the candidate pass, hide failed cases behind an average,
or claim improvement without comparing the pinned baseline. Blocking safety,
permission, or business-invariant failures override aggregate scores.

Automatic tuning is allowed only inside confirmed data, cost, provider, metric,
and business boundaries. Changing model/provider, data source, business threshold,
scoring rule, or cost ceiling requires user decision and artifact updates.

Final delivery uses a fresh full Eval on the delivery commit and independent
review of both the harness and results.
