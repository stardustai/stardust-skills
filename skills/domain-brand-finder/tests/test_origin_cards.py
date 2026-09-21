import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_origin_cards.py"
spec = importlib.util.spec_from_file_location("validate_origin_cards", SCRIPT)
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def good_card():
    return {
        "name": "Axen",
        "source_roots": [{"word": "axis"}, {"word": "intent"}],
        "construction": {
            "output": "axen",
            "retained_spans": [
                {"source": "axis", "span": [0, 2], "output_span": [0, 2], "text": "ax"},
                {"source": "intent", "span": [3, 5], "output_span": [2, 4], "text": "en"},
            ],
            "inserted_spans": [],
            "mutated_spans": [],
            "overlap_spans": [],
        },
    }


def test_valid_card_reconstructs_every_output_character_once():
    result = validator.validate_cards([good_card()])
    assert result["complete"] is True
    assert result["cards"][0]["errors"] == []


def test_missing_inserted_letter_is_rejected():
    card = good_card()
    card["name"] = card["construction"]["output"] = "axeln"
    card["construction"]["retained_spans"][1]["output_span"] = [3, 5]
    result = validator.validate_cards([card])
    assert result["complete"] is False
    assert result["cards"][0]["status"] == "SOURCE_RECORD_INCONSISTENT"
    assert any("has no provenance" in error for error in result["cards"][0]["errors"])


def test_retained_and_mutated_overlap_is_rejected():
    card = good_card()
    card["construction"]["mutated_spans"] = [{
        "source": "intent",
        "source_span": [3, 5],
        "source_text": "en",
        "output_span": [2, 4],
        "output_text": "en",
    }]
    result = validator.validate_cards([card])
    assert result["complete"] is False
    assert any("double-counted" in error for error in result["cards"][0]["errors"])


def test_mutation_length_mismatch_is_rejected():
    card = good_card()
    card["construction"]["retained_spans"] = [card["construction"]["retained_spans"][0]]
    card["construction"]["mutated_spans"] = [{
        "source": "intent",
        "source_span": [3, 6],
        "source_text": "ent",
        "output_span": [2, 4],
        "output_text": "e n",
    }]
    result = validator.validate_cards([card])
    assert result["complete"] is False
    assert any("output_text length" in error for error in result["cards"][0]["errors"])
