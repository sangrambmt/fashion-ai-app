"""Unit tests for classifier.parse_model_output."""
import json
import pytest
from app.classifier import parse_model_output


def _make_json(**overrides) -> str:
    base = {
        "description": "A plain white t-shirt.",
        "garment_type": "shirt",
        "style": "casual",
        "material": "cotton",
        "color_palette": ["white"],
        "pattern": "solid",
        "season": "all-season",
        "occasion": "everyday",
        "consumer_profile": "general",
        "trend_notes": "basics staple",
        "location_context": "unknown",
        "inferred_continent": "unknown",
        "inferred_country": "unknown",
        "inferred_city": "unknown",
    }
    base.update(overrides)
    return json.dumps(base)


# valid JSON 

def test_parses_clean_json():
    result = parse_model_output(_make_json())
    assert result["garment_type"] == "shirt"
    assert result["style"] == "casual"


def test_parses_json_with_markdown_fence():
    raw = f"```json\n{_make_json()}\n```"
    result = parse_model_output(raw)
    assert result["material"] == "cotton"


def test_parses_json_with_generic_fence():
    raw = f"```\n{_make_json()}\n```"
    result = parse_model_output(raw)
    assert result["season"] == "all-season"


def test_parses_json_with_leading_prose():
    raw = f"Here is the analysis:\n{_make_json()}"
    result = parse_model_output(raw)
    assert result["occasion"] == "everyday"


def test_parses_json_with_trailing_prose():
    raw = f"{_make_json()}\nLet me know if you need more details."
    result = parse_model_output(raw)
    assert result["pattern"] == "solid"


def test_color_palette_returned_as_list():
    result = parse_model_output(_make_json(color_palette=["white", "grey"]))
    assert isinstance(result["color_palette"], list)
    assert "white" in result["color_palette"]


def test_color_palette_string_normalised_to_list():
    """Model sometimes returns a comma-separated string instead of an array."""
    obj = json.loads(_make_json())
    obj["color_palette"] = "white, grey"
    result = parse_model_output(json.dumps(obj))
    assert isinstance(result["color_palette"], list)
    assert "white" in result["color_palette"]


def test_all_required_fields_present():
    required = [
        "description", "garment_type", "style", "material", "color_palette",
        "pattern", "season", "occasion", "consumer_profile", "trend_notes",
        "location_context", "inferred_continent", "inferred_country", "inferred_city",
    ]
    result = parse_model_output(_make_json())
    for field in required:
        assert field in result, f"Missing field: {field}"


# invalid JSON 

def test_raises_on_plain_text():
    with pytest.raises((ValueError, Exception)):
        parse_model_output("The image shows a red jacket.")


def test_raises_on_truncated_json():
    with pytest.raises(Exception):
        parse_model_output('{"garment_type": "dress", "style":')
