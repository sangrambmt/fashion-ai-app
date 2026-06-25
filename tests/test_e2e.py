"""End-to-end tests: upload → classify (mocked) → save → filter."""
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import app.db as db
from app.classifier import classify_image


MOCK_RESPONSE = {
    "description": "A floral midi dress with puff sleeves in pastel yellow cotton.",
    "garment_type": "dress",
    "style": "bohemian",
    "material": "cotton",
    "color_palette": ["yellow", "white"],
    "pattern": "floral",
    "season": "summer",
    "occasion": "everyday",
    "consumer_profile": "bohemian traveler",
    "trend_notes": "cottagecore revival",
    "location_context": "outdoor market",
    "inferred_continent": "Europe",
    "inferred_country": "France",
    "inferred_city": "Paris",
}


@pytest.fixture()
def sample_image(tmp_path):
    try:
        from PIL import Image
        img = Image.new("RGB", (64, 64), color=(200, 180, 160))
        path = tmp_path / "test_garment.jpg"
        img.save(path, "JPEG")
        return path
    except ImportError:
        uploads = Path(__file__).parent.parent / "uploads"
        for f in uploads.glob("*.jpg"):
            dest = tmp_path / f.name
            shutil.copy(f, dest)
            return dest
        pytest.skip("PIL not available and no existing upload found")


def _mock_response(data: dict) -> MagicMock:
    msg = MagicMock()
    msg.content = json.dumps(data)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ── classify → parse ──────────────────────────────────────────────────────────

def test_classify_image_returns_structured_dict(sample_image):
    with patch("app.classifier.client") as mock_client:
        mock_client.chat.completions.create.return_value = _mock_response(MOCK_RESPONSE)
        result = classify_image(str(sample_image))

    assert result["garment_type"] == "dress"
    assert result["style"] == "bohemian"
    assert isinstance(result["color_palette"], list)


def test_classify_handles_markdown_fenced_response(sample_image):
    fenced_resp = {**MOCK_RESPONSE}
    mock_msg = MagicMock()
    mock_msg.content = f"```json\n{json.dumps(fenced_resp)}\n```"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    with patch("app.classifier.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_resp
        result = classify_image(str(sample_image))

    assert result["garment_type"] == "dress"


# upload → save → query

def test_upload_classify_save_query(tmp_db, sample_image):
    with patch("app.classifier.client") as mock_client:
        mock_client.chat.completions.create.return_value = _mock_response(MOCK_RESPONSE)
        data = classify_image(str(sample_image))

    location = {"continent": "Europe", "country": "France", "city": "Paris"}
    db.save_image(str(sample_image), data, location=location, designer="testuser")

    rows = db.get_images()
    assert len(rows) == 1
    row = rows[0]
    assert row["garment_type"] == "dress"
    assert row["continent"] == "Europe"
    assert row["designer"] == "testuser"


def test_upload_then_filter_by_garment(tmp_db, sample_image):
    with patch("app.classifier.client") as mock_client:
        mock_client.chat.completions.create.return_value = _mock_response(MOCK_RESPONSE)
        data = classify_image(str(sample_image))

    db.save_image(str(sample_image), data)

    assert len(db.get_images(garment_types=["dress"])) == 1
    assert len(db.get_images(garment_types=["jacket"])) == 0


def test_upload_then_filter_by_location(tmp_db, sample_image):
    with patch("app.classifier.client") as mock_client:
        mock_client.chat.completions.create.return_value = _mock_response(MOCK_RESPONSE)
        data = classify_image(str(sample_image))

    db.save_image(str(sample_image), data,
                  location={"continent": "Europe", "country": "France", "city": "Paris"})

    assert len(db.get_images(continents=["Europe"])) == 1
    assert len(db.get_images(continents=["Asia"])) == 0
    assert len(db.get_images(countries=["France"])) == 1


def test_full_flow_with_annotation(tmp_db, sample_image):
    with patch("app.classifier.client") as mock_client:
        mock_client.chat.completions.create.return_value = _mock_response(MOCK_RESPONSE)
        data = classify_image(str(sample_image))

    row_id = db.save_image(str(sample_image), data)
    db.update_notes(row_id, "cottagecore, puff-sleeve", "Spotted at a Provence market.")

    rows = db.get_images(search="provence")
    assert len(rows) == 1
    assert "Provence" in rows[0]["designer_notes"]
    assert rows[0]["garment_type"] == "dress"
