import csv
import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_brand_candidates.py"
spec = importlib.util.spec_from_file_location("generate_brand_candidates", SCRIPT)
generator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generator
spec.loader.exec_module(generator)


def test_generated_candidates_leave_brand_score_blank_and_expose_generation_priority():
    rows = generator.generate_rows(12)

    assert rows
    assert all(row["brand_score_10"] == "" for row in rows)
    assert all("generation_priority" in row for row in rows)
    assert all("品牌质量评分" in row["generation_priority_note"] for row in rows)


def test_generator_cli_keeps_candidate_csv_shape_without_brand_scoring(tmp_path):
    output = tmp_path / "candidates.csv"
    generator.write_candidates(output, 5)

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert rows[0]["brand_score_10"] == ""
    assert "generation_priority" in rows[0]
    assert "品牌质量评分" in rows[0]["generation_priority_note"]
