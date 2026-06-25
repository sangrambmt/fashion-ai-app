"""Integration tests for db filtering — location, time, and text search."""
import pytest
import app.db as db


def _insert(tmp_db, image_path="img.jpg", **kwargs):
    data = {
        "description":      kwargs.pop("description", "a garment"),
        "garment_type":     kwargs.pop("garment_type", "dress"),
        "style":            kwargs.pop("style", "casual"),
        "material":         kwargs.pop("material", "cotton"),
        "color_palette":    kwargs.pop("color_palette", ["white"]),
        "pattern":          kwargs.pop("pattern", "solid"),
        "season":           kwargs.pop("season", "summer"),
        "occasion":         kwargs.pop("occasion", "everyday"),
        "consumer_profile": kwargs.pop("consumer_profile", "general"),
        "trend_notes":      kwargs.pop("trend_notes", ""),
        "location_context": kwargs.pop("location_context", ""),
        "inferred_continent": kwargs.pop("inferred_continent", ""),
        "inferred_country":   kwargs.pop("inferred_country", ""),
        "inferred_city":      kwargs.pop("inferred_city", ""),
    }
    location = kwargs.pop("location", {})
    designer = kwargs.pop("designer", "")
    return db.save_image(image_path, data, location=location, designer=designer)


# basic filtering 

def test_filter_by_garment_type(tmp_db):
    _insert(tmp_db, garment_type="dress")
    _insert(tmp_db, garment_type="jacket")
    rows = db.get_images(garment_types=["dress"])
    assert len(rows) == 1
    assert rows[0]["garment_type"] == "dress"


def test_filter_by_style(tmp_db):
    _insert(tmp_db, style="bohemian")
    _insert(tmp_db, style="minimalist")
    rows = db.get_images(styles=["minimalist"])
    assert len(rows) == 1


def test_filter_multiple_values(tmp_db):
    _insert(tmp_db, season="summer")
    _insert(tmp_db, season="winter")
    _insert(tmp_db, season="spring")
    rows = db.get_images(seasons=["summer", "winter"])
    assert len(rows) == 2


def test_no_filters_returns_all(tmp_db):
    _insert(tmp_db)
    _insert(tmp_db)
    assert len(db.get_images()) == 2


# full-text search 

def test_search_matches_description(tmp_db):
    _insert(tmp_db, description="embroidered neckline with gold thread")
    _insert(tmp_db, description="plain white t-shirt")
    rows = db.get_images(search="embroidered")
    assert len(rows) == 1
    assert "embroidered" in rows[0]["description"]


def test_search_matches_designer_notes(tmp_db):
    row_id = _insert(tmp_db)
    db.update_notes(row_id, "artisan", "found at a street market in Marrakech")
    rows = db.get_images(search="marrakech")
    assert len(rows) == 1


def test_search_case_insensitive(tmp_db):
    _insert(tmp_db, description="Silk Kimono from Kyoto")
    rows = db.get_images(search="kyoto")
    assert len(rows) == 1


def test_search_multi_term_AND_logic(tmp_db):
    _insert(tmp_db, description="vintage leather jacket streetwear")
    _insert(tmp_db, description="vintage floral dress summer")
    rows = db.get_images(search="vintage leather")
    assert len(rows) == 1


# location filters 

def test_filter_by_user_continent(tmp_db):
    _insert(tmp_db, location={"continent": "Europe", "country": "France", "city": "Paris"})
    _insert(tmp_db, location={"continent": "Asia", "country": "Japan", "city": "Tokyo"})
    rows = db.get_images(continents=["Europe"])
    assert len(rows) == 1
    assert rows[0]["continent"] == "Europe"


def test_filter_by_ai_continent(tmp_db):
    _insert(tmp_db, inferred_continent="Asia", inferred_country="Japan")
    _insert(tmp_db, inferred_continent="Europe")
    rows = db.get_images(continents=["Asia"])
    assert len(rows) == 1


def test_filter_continent_matches_either_user_or_ai(tmp_db):
    _insert(tmp_db, location={"continent": "Europe"})
    _insert(tmp_db, inferred_continent="Europe")
    _insert(tmp_db, location={"continent": "Asia"}, inferred_continent="Asia")
    rows = db.get_images(continents=["Europe"])
    assert len(rows) == 2


def test_filter_by_country(tmp_db):
    _insert(tmp_db, location={"country": "France"})
    _insert(tmp_db, location={"country": "Italy"})
    rows = db.get_images(countries=["France"])
    assert len(rows) == 1


def test_filter_by_city(tmp_db):
    _insert(tmp_db, location={"city": "Paris"})
    _insert(tmp_db, location={"city": "Milan"})
    rows = db.get_images(cities=["Paris"])
    assert len(rows) == 1


# time filters 

def test_filter_by_year(tmp_db):
    _insert(tmp_db)
    rows = db.get_images()
    year = rows[0]["upload_year"]
    result = db.get_images(years=[year])
    assert len(result) >= 1
    assert all(r["upload_year"] == year for r in result)


def test_filter_by_month(tmp_db):
    _insert(tmp_db)
    rows = db.get_images()
    month = rows[0]["upload_month"]
    result = db.get_images(months=[month])
    assert all(r["upload_month"] == month for r in result)


# designer filter 

def test_filter_by_designer(tmp_db):
    _insert(tmp_db, designer="alice")
    _insert(tmp_db, designer="bob")
    rows = db.get_images(designers=["alice"])
    assert len(rows) == 1
    assert rows[0]["designer"] == "alice"


# combined filters 

def test_combined_garment_and_location(tmp_db):
    _insert(tmp_db, garment_type="dress",  location={"continent": "Europe"})
    _insert(tmp_db, garment_type="jacket", location={"continent": "Europe"})
    _insert(tmp_db, garment_type="dress",  location={"continent": "Asia"})
    rows = db.get_images(garment_types=["dress"], continents=["Europe"])
    assert len(rows) == 1


def test_get_filter_options_returns_distinct_values(tmp_db):
    _insert(tmp_db, garment_type="dress",  style="casual")
    _insert(tmp_db, garment_type="dress",  style="formal")
    _insert(tmp_db, garment_type="jacket", style="casual")
    opts = db.get_filter_options()
    assert sorted(opts["garment_type"]) == ["dress", "jacket"]
    assert sorted(opts["style"]) == ["casual", "formal"]


def test_update_notes(tmp_db):
    row_id = _insert(tmp_db)
    db.update_notes(row_id, "handmade, artisan", "Purchased at a local market.")
    rows = db.get_images()
    assert rows[0]["designer_tags"] == "handmade, artisan"
    assert "local market" in rows[0]["designer_notes"]


def test_delete_image(tmp_db):
    _insert(tmp_db)
    rows_before = db.get_images()
    assert len(rows_before) == 1
    db.delete_image(rows_before[0]["id"])
    assert len(db.get_images()) == 0
