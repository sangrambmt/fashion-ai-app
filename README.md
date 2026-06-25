# Fashion Inspiration Library

An AI-powered web app for fashion designers to upload, classify, search, and annotate garment inspiration imagery.

## Setup

```bash
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
streamlit run app/main.py
```

Opens at `http://localhost:8501`.

## What it does

- **Upload** a garment photo and classify it with GPT-4o-mini — returns garment type, style, material, colour palette, pattern, season, occasion, consumer profile, trend notes, and inferred location
- **Search** across descriptions and annotations with natural queries like `embroidered neckline`
- **Filter** by garment attributes, location (continent / country / city), time (year / month), and designer — all filters are dynamically generated from the data
- **Annotate** images with your own tags and notes, visually distinguished from AI output

## Structure

```text
app/        Streamlit UI, classifier, database
eval/       Evaluation script and labelled test set
tests/      Unit, integration, and end-to-end tests
```

## Tests

```bash
pytest tests/ -v   # 36 tests, all pass, OpenAI is mocked
```

## Evaluation

Add images to `eval/test_images/`, fill in `eval/sample_labels.csv`, then:

```bash
python eval/evaluate.py --labels eval/sample_labels.csv --images eval/test_images/
```

Reports per-attribute exact and partial match accuracy. See [eval/README.md](eval/README.md) for methodology and results.

## Key decisions

- **Streamlit + SQLite** — minimal setup, runs locally with no infrastructure
- **GPT-4o-mini** — good multimodal quality at low cost
- **SQL-based filtering** — filters run in the database, not in Python loops
- **`parse_model_output` as a pure function** — decouples JSON parsing from the API call so it can be unit-tested without mocking OpenAI


