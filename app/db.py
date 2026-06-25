import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "fashion.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                filename         TEXT DEFAULT '',
                image_path       TEXT NOT NULL,
                description      TEXT DEFAULT '',
                garment_type     TEXT DEFAULT '',
                style            TEXT DEFAULT '',
                material         TEXT DEFAULT '',
                color_palette    TEXT DEFAULT '',
                pattern          TEXT DEFAULT '',
                season           TEXT DEFAULT '',
                occasion         TEXT DEFAULT '',
                consumer_profile TEXT DEFAULT '',
                trend_notes      TEXT DEFAULT '',
                location_context TEXT DEFAULT '',
                ai_continent     TEXT DEFAULT '',
                ai_country       TEXT DEFAULT '',
                ai_city          TEXT DEFAULT '',
                continent        TEXT DEFAULT '',
                country          TEXT DEFAULT '',
                city             TEXT DEFAULT '',
                upload_year      INTEGER,
                upload_month     INTEGER,
                upload_date      TEXT DEFAULT '',
                designer         TEXT DEFAULT '',
                designer_tags    TEXT DEFAULT '',
                designer_notes   TEXT DEFAULT '',
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(images)")}
    new_cols = [
        ("filename",     "TEXT DEFAULT ''"),
        ("ai_continent", "TEXT DEFAULT ''"),
        ("ai_country",   "TEXT DEFAULT ''"),
        ("ai_city",      "TEXT DEFAULT ''"),
        ("continent",    "TEXT DEFAULT ''"),
        ("country",      "TEXT DEFAULT ''"),
        ("city",         "TEXT DEFAULT ''"),
        ("upload_year",  "INTEGER"),
        ("upload_month", "INTEGER"),
        ("upload_date",  "TEXT DEFAULT ''"),
        ("designer",     "TEXT DEFAULT ''"),
    ]
    for name, defn in new_cols:
        if name not in existing:
            conn.execute(f"ALTER TABLE images ADD COLUMN {name} {defn}")


def save_image(
    image_path: str,
    data: dict,
    location: dict = None,
    designer: str = "",
) -> int:
    location = location or {}
    now = datetime.now()
    color = data.get("color_palette", "")
    if isinstance(color, list):
        color = json.dumps(color)

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images (
                filename, image_path,
                description, garment_type, style, material, color_palette, pattern,
                season, occasion, consumer_profile, trend_notes, location_context,
                ai_continent, ai_country, ai_city,
                continent, country, city,
                upload_year, upload_month, upload_date,
                designer
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                Path(image_path).name,
                image_path,
                data.get("description", ""),
                data.get("garment_type", ""),
                data.get("style", ""),
                data.get("material", ""),
                color,
                data.get("pattern", ""),
                data.get("season", ""),
                data.get("occasion", ""),
                data.get("consumer_profile", ""),
                data.get("trend_notes", ""),
                data.get("location_context", ""),
                data.get("inferred_continent", ""),
                data.get("inferred_country", ""),
                data.get("inferred_city", ""),
                location.get("continent", ""),
                location.get("country", ""),
                location.get("city", ""),
                now.year,
                now.month,
                now.strftime("%Y-%m-%d"),
                designer,
            ),
        )
        return cursor.lastrowid


def get_images(
    search: str = "",
    garment_types: list = None,
    styles: list = None,
    materials: list = None,
    patterns: list = None,
    seasons: list = None,
    occasions: list = None,
    consumer_profiles: list = None,
    continents: list = None,
    countries: list = None,
    cities: list = None,
    years: list = None,
    months: list = None,
    designers: list = None,
) -> list:
    query = "SELECT * FROM images WHERE 1=1"
    params: list = []

    if search:
        for term in search.lower().split():
            frag = f"%{term}%"
            query += """ AND (
                lower(description) LIKE ? OR lower(trend_notes) LIKE ? OR
                lower(designer_tags) LIKE ? OR lower(designer_notes) LIKE ? OR
                lower(location_context) LIKE ? OR lower(garment_type) LIKE ? OR
                lower(style) LIKE ? OR lower(material) LIKE ? OR lower(color_palette) LIKE ?
            )"""
            params.extend([frag] * 9)

    def _in_filter(field: str, values: list):
        nonlocal query, params
        if not values:
            return
        ph = ",".join("?" * len(values))
        query += f" AND lower({field}) IN ({ph})"
        params.extend(v.lower() for v in values)

    _in_filter("garment_type", garment_types or [])
    _in_filter("style", styles or [])
    _in_filter("material", materials or [])
    _in_filter("pattern", patterns or [])
    _in_filter("season", seasons or [])
    _in_filter("occasion", occasions or [])
    _in_filter("consumer_profile", consumer_profiles or [])
    _in_filter("designer", designers or [])

    # Location: match user-provided OR AI-inferred
    for user_field, ai_field, values in [
        ("continent", "ai_continent", continents or []),
        ("country",   "ai_country",   countries or []),
        ("city",      "ai_city",      cities or []),
    ]:
        if values:
            ph = ",".join("?" * len(values))
            vals = [v.lower() for v in values]
            query += f" AND (lower({user_field}) IN ({ph}) OR lower({ai_field}) IN ({ph}))"
            params.extend(vals + vals)

    if years:
        ph = ",".join("?" * len(years))
        query += f" AND upload_year IN ({ph})"
        params.extend(years)

    if months:
        ph = ",".join("?" * len(months))
        query += f" AND upload_month IN ({ph})"
        params.extend(months)

    query += " ORDER BY id DESC"

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_filter_options() -> dict:
    simple = [
        "garment_type", "style", "material", "pattern",
        "season", "occasion", "consumer_profile", "designer",
        "upload_year", "upload_month",
    ]
    opts: dict = {}
    with connect() as conn:
        for field in simple:
            rows = conn.execute(
                f"SELECT DISTINCT {field} FROM images "
                f"WHERE {field} != '' AND {field} IS NOT NULL ORDER BY {field}"
            ).fetchall()
            opts[field] = [r[0] for r in rows]

        for user_f, ai_f in [
            ("continent", "ai_continent"),
            ("country",   "ai_country"),
            ("city",      "ai_city"),
        ]:
            rows = conn.execute(f"""
                SELECT DISTINCT val FROM (
                    SELECT {user_f} AS val FROM images
                    WHERE {user_f} != '' AND {user_f} IS NOT NULL
                    UNION
                    SELECT {ai_f} AS val FROM images
                    WHERE {ai_f} != '' AND {ai_f} IS NOT NULL
                      AND lower({ai_f}) != 'unknown'
                ) ORDER BY val
            """).fetchall()
            opts[user_f] = [r[0] for r in rows]

    return opts


def update_notes(image_id: int, tags: str, notes: str):
    with connect() as conn:
        conn.execute(
            "UPDATE images SET designer_tags = ?, designer_notes = ? WHERE id = ?",
            (tags, notes, image_id),
        )


def delete_image(image_id: int) -> Optional[str]:
    with connect() as conn:
        row = conn.execute(
            "SELECT image_path FROM images WHERE id = ?", (image_id,)
        ).fetchone()
        conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
    return row["image_path"] if row else None
