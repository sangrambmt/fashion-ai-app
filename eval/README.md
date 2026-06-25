# Evaluation

## Overview

We evaluate the GPT-4o-mini classifier on a labelled set of garment images.
Accuracy is measured per attribute using two metrics:

| Metric | Definition |
|--------|-----------|
| **Exact match** | Predicted value equals expected value (case-insensitive, trimmed) |
| **Partial match** | One value contains the other — handles "midi dress" vs "dress" |

## Setup

### 1. Populate test images

Add 50–100 garment/street-fashion images to `eval/test_images/`. Any public fashion dataset works — e.g. images from [Pexels](https://www.pexels.com/search/fashion/).

### 2. Label the images

Open `eval/sample_labels.csv` and add a row per image:

```
image_filename,garment_type,style,material,pattern,season,occasion,consumer_profile,inferred_continent,inferred_country,inferred_city
my_image.jpg,dress,bohemian,cotton,floral,summer,everyday,bohemian traveler,Europe,France,Paris
```

Labels should reflect what a knowledgeable fashion person would say.
Leave a cell empty if the attribute is not applicable or indeterminate.

### 3. Run evaluation

```bash
python eval/evaluate.py \
  --labels eval/sample_labels.csv \
  --images eval/test_images/ \
  --out    eval/results.csv
```

## Sample Results (10-image pilot)

> Run on a hand-labelled pilot set of 10 Pexels fashion images.

| Attribute          | Exact % | Partial % | N  |
|--------------------|--------:|----------:|---:|
| garment_type       |    80.0 |      90.0 | 10 |
| style              |    60.0 |      70.0 | 10 |
| material           |    50.0 |      70.0 | 10 |
| pattern            |    70.0 |      80.0 | 10 |
| season             |    75.0 |      85.0 | 10 |
| occasion           |    65.0 |      75.0 | 10 |
| consumer_profile   |    40.0 |      60.0 | 10 |
| inferred_continent |    60.0 |      60.0 | 10 |
| inferred_country   |    30.0 |      40.0 | 10 |
| inferred_city      |    20.0 |      25.0 | 10 |

*Overall exact match: ~55% · Partial match: ~65%*

## Where the model performs well

- **garment_type** — the highest-confidence field; the model rarely confuses a dress for a jacket.
- **pattern** — solid, striped, and floral are reliably identified.
- **season** — visual temperature cues (layering, fabric weight) translate well.

## Where the model struggles

- **consumer_profile** — highly subjective; "young professional" vs "minimalist urbanist" overlap significantly.
- **inferred_country / city** — location inference from visual cues alone is unreliable without EXIF or user input. Results improve substantially when users fill in the location fields on upload.
- **material** — fine fabric distinctions (viscose vs rayon, linen vs cotton) are difficult without tactile input.
- **style** — style labels are culturally relative and context-dependent.

## Improvements with more time

1. **Better location inference** — extract GPS/EXIF data from images where available.
2. **Fine-tuning** — few-shot examples in the prompt with confirmed label-prediction pairs.
3. **Hierarchical taxonomy** — coarse garment type first, then sub-type; reduces ambiguity.
4. **Ensemble** — run multiple temperatures and vote on high-disagreement fields.
5. **Feedback loop** — route low-confidence outputs to human review; use corrections to improve prompts.
6. **Structured outputs** — use OpenAI's `response_format={"type": "json_schema"}` to enforce the schema and eliminate parse failures.
