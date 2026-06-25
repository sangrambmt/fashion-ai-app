import pytest
from pathlib import Path
import app.db as db_module


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """Point db.DB_PATH at a temp file and initialise a fresh schema."""
    test_db = tmp_path / "test_fashion.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db_module.init_db()
    return test_db


@pytest.fixture()
def sample_data() -> dict:
    return {
        "description": "A floral midi dress with puff sleeves in pastel yellow.",
        "garment_type": "dress",
        "style": "bohemian",
        "material": "cotton",
        "color_palette": ["yellow", "white"],
        "pattern": "floral",
        "season": "summer",
        "occasion": "everyday",
        "consumer_profile": "bohemian traveler",
        "trend_notes": "cottagecore revival, 2024 trend",
        "location_context": "outdoor market stall",
        "inferred_continent": "Europe",
        "inferred_country": "France",
        "inferred_city": "Paris",
    }
