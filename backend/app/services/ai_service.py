import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL_NAME = "openai/gpt-oss-120b"
# You can change this later to another OpenRouter model if you want.


def ai_review_openapi(data: dict):
    try:
        paths = data.get("paths", {})
        extracted = []

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue

                extracted.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", "")
                })

        prompt = f"""
You are an expert API design reviewer.

Analyze the following OpenAPI endpoints.

For each endpoint, review:
1. Summary quality
2. Description quality
3. Endpoint naming (avoid verbs, clarity)
4. HTTP method usage

Return ONLY valid JSON.
Do not use markdown.
Do not wrap the response in ```json.

Return this exact structure:
[
  {{
    "endpoint": "GET /users",
    "issues": ["summary too vague"],
    "suggestion": "Improve summary to 'Retrieve user by ID'"
  }}
]

Endpoints:
{json.dumps(extracted, ensure_ascii=False, indent=2)}
"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert API reviewer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-OpenRouter-Title": "PFE API Governance",
            },
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        return json.loads(content)

    except Exception as e:
        return {"error": str(e)}