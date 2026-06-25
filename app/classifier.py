import os
import base64
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT = """You are a fashion intelligence assistant.

Analyze this garment image and return ONLY a valid JSON object with these exact fields:

{
  "description": "detailed natural-language description of the garment and its visual details",
  "garment_type": "single noun, e.g. dress / jacket / trousers / shirt / skirt / coat / blouse",
  "style": "e.g. casual / formal / bohemian / streetwear / minimalist / vintage / athleisure",
  "material": "primary fabric, e.g. cotton / silk / denim / wool / polyester / linen / leather",
  "color_palette": ["primary color", "secondary color"],
  "pattern": "e.g. solid / floral / striped / geometric / plaid / abstract / animal print",
  "season": "spring / summer / autumn / winter / all-season",
  "occasion": "e.g. everyday / workwear / evening / athletic / festival / beach",
  "consumer_profile": "brief target archetype, e.g. young professional / bohemian traveler / minimalist urbanist",
  "trend_notes": "current trend relevance, design influences, or market positioning",
  "location_context": "inferred setting or cultural context visible in the image",
  "inferred_continent": "continent inferred from visual/cultural cues — Africa/Asia/Europe/North America/South America/Oceania — or 'unknown'",
  "inferred_country": "country if determinable from visual or cultural cues, else 'unknown'",
  "inferred_city": "city if determinable, else 'unknown'"
}

Rules:
- Keep all values concise (≤ 10 words each).
- color_palette must be a JSON array of strings.
- If unsure about a field, use "unknown".
- Return ONLY the JSON object — no prose, no markdown fences."""


def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def parse_model_output(text: str) -> dict:
    """Parse raw model text into a structured dict.

    Handles markdown code fences and stray text around the JSON block.
    Raises ValueError if no valid JSON object is found.
    """
    text = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:]
        # Drop trailing fence
        if inner and inner[-1].strip().startswith("```"):
            inner = inner[:-1]
        text = "\n".join(inner).strip()

    # Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in model output: {text[:300]!r}")

    parsed = json.loads(text[start:end])

    # Normalise color_palette to a list
    cp = parsed.get("color_palette", [])
    if isinstance(cp, str):
        parsed["color_palette"] = [c.strip() for c in cp.split(",") if c.strip()]

    return parsed


def classify_image(image_path: str) -> dict:
    ext = image_path.lower().rsplit(".", 1)[-1]
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    b64 = image_to_base64(image_path)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ],
        temperature=0.2,
    )

    return parse_model_output(response.choices[0].message.content)
