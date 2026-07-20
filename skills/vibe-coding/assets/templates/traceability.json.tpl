{
  "$schema": "skills/vibe-coding/assets/schemas/traceability.schema.json",
  "schema_version": "1.0",
  "mappings": [
    {
      "scenario_id": "__SCENARIO_ID__",
      "qa_case_refs": ["__QA_CASE_ID__"],
      "automated_test_refs": ["__AUTOMATED_TEST_REF__"],
      "evaluation_asset_refs": ["__EVALUATION_ASSET_REF__"],
      "business_signal_refs": ["__BUSINESS_SIGNAL_ID__"],
      "business_signal_rules": [
        {"signal_id": "__BUSINESS_SIGNAL_ID__", "source": "__MEASUREMENT_SOURCE__", "operator": "__SUPPORTED_OPERATOR__", "expected": "__EXPECTED_VALUE__"}
      ],
      "business_owner_approval": {"approved_by": "__BUSINESS_OWNER__", "confirmed_version": "__SPEC_CONFIRMED_VERSION__"},
      "verification_commands": [
        ["__TEST_EXECUTABLE__", "__TEST_ARG__"]
      ],
      "evidence_paths": ["docs/evidence/__SCENARIO_ID__.json"]
    }
  ]
}
