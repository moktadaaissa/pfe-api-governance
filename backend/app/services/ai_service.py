import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL_NAME = "openai/gpt-oss-120b"


def _clean_json_response(content: str):
    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI returned invalid JSON: {exc}") from exc


def ai_review_openapi(data: dict):
    """
    Broad AI review for human-facing feedback.
    """
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
You are a strict and experienced API governance expert.

Your role is to review OpenAPI endpoints and evaluate their quality based on:
- clarity
- REST design principles
- naming conventions
- correctness of HTTP method usage

Be objective and professional:
- Do NOT invent problems if the endpoint is good
- BUT do NOT be too permissive — identify real design issues when they exist

For each endpoint, analyze:

1. Summary quality:
- clear, specific, meaningful?
- flag if vague or generic

2. Description quality:
- detailed enough?
- flag if too short or unclear

3. Endpoint naming:
- avoid verbs (get, create, update, delete)
- prefer resource-based naming
- detect unclear or inconsistent naming

4. HTTP method usage:
- GET → retrieve
- POST → create or trigger action
- PUT/PATCH → update
- flag incorrect or debatable usage

Return ONLY valid JSON (no markdown, no explanation).

Each item must follow this structure:
[
  {{
    "endpoint": "GET /users",
    "status": "good",
    "issues": [],
    "comment": "Well-designed endpoint with clear naming and proper REST usage.",
    "suggestion": ""
  }},
  {{
    "endpoint": "POST /users/create",
    "status": "needs_improvement",
    "issues": ["uses verb in path", "REST design not optimal"],
    "comment": "",
    "suggestion": "Use '/users' with POST instead of '/users/create'."
  }}
]

Rules:
- If NO issues → status = "good"
- If issues exist → status = "needs_improvement"
- Be STRICT but FAIR

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

        content = response.choices[0].message.content or ""
        return _clean_json_response(content)

    except Exception as e:
        logger.error("ai_review_openapi failed: %s", e, exc_info=True)
        return {"error": str(e)}


def ai_generate_safe_fixes(data: dict):
    """
    Narrow AI output for simulation only.
    Generates safe structured replacements.

    Allowed fields:
    - summary
    - description
    - operationId
    - tags
    - response_description
    """
    try:
        paths = data.get("paths", {})
        extracted = []

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue

                responses = details.get("responses", {})
                extracted_responses = []

                if isinstance(responses, dict):
                    for status_code, response_details in responses.items():
                        extracted_responses.append({
                            "status_code": str(status_code),
                            "description": response_details.get("description", "")
                            if isinstance(response_details, dict) else ""
                        })

                extracted.append({
                    "path": path,
                    "method": str(method).lower(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "operationId": details.get("operationId", ""),
                    "tags": details.get("tags", []),
                    "responses": extracted_responses
                })

        prompt = f"""
You are an API governance assistant.

Your task is to generate ONLY safe replacement suggestions for fields that can be reliably improved.

Allowed fields:
- summary
- description
- operationId
- tags
- response_description

Allowed action:
- replace

Important rules:
- Return ONLY valid JSON
- Return a JSON array
- Do not include markdown
- Do not suggest path renaming
- Do not suggest HTTP method changes
- Do not suggest requestBody
- Do not suggest schema/content changes
- Only suggest replacements when you are confident
- If an existing field is already good, do not include it
- Be conservative

Rules for response_description:
- Only suggest response_description for an existing response object
- Include a "target" object with "status_code"
- Example:
  {{
    "path": "/users",
    "method": "get",
    "field": "response_description",
    "action": "replace",
    "target": {{
      "status_code": "400"
    }},
    "value": "Invalid request."
  }}

Output format:
[
  {{
    "path": "/users",
    "method": "get",
    "field": "summary",
    "action": "replace",
    "value": "List users"
  }}
]

Guidelines:
- summary: short and clear
- description: concrete and informative
- operationId: concise camelCase
- tags: short resource grouping labels, e.g. ["Users"]
- response_description: concise and meaningful for the specific status code

Endpoints:
{json.dumps(extracted, ensure_ascii=False, indent=2)}
"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You generate safe structured OpenAPI field fixes."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-OpenRouter-Title": "PFE API Governance",
            },
        )

        content = response.choices[0].message.content or ""
        parsed = _clean_json_response(content)

        if not isinstance(parsed, list):
            logger.warning("ai_generate_safe_fixes: expected list, got %s", type(parsed).__name__)
            return {"error": "AI did not return a list of fixes"}

        return parsed

    except Exception as e:
        logger.error("ai_generate_safe_fixes failed: %s", e, exc_info=True)
        return {"error": str(e)}
    
def ai_review_duplicate_match(uploaded_endpoint: dict, matched_endpoint: dict, matched_api: dict, similarity: float):
    """
    AI-assisted duplicate explanation.
    Used only after deterministic cosine similarity finds a suspicious match.
    """
    try:
        prompt = f"""
You are an API governance expert.

Your task is to review whether two API endpoints are functionally duplicate, overlapping, or different.

Return ONLY valid JSON. No markdown.

Use this format:
{{
  "ai_duplicate_decision": "duplicate" | "overlap" | "different",
  "confidence": 0-100,
  "reason": "short professional explanation",
  "recommendation": "what governance reviewer should do"
}}

Uploaded endpoint:
{json.dumps(uploaded_endpoint, ensure_ascii=False, indent=2)}

Matched existing endpoint:
{json.dumps(matched_endpoint, ensure_ascii=False, indent=2)}

Matched API:
{json.dumps(matched_api, ensure_ascii=False, indent=2)}

Deterministic cosine similarity:
{similarity}
"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert API governance reviewer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-OpenRouter-Title": "PFE API Governance",
            },
        )

        content = response.choices[0].message.content or ""
        parsed = _clean_json_response(content)

        if not isinstance(parsed, dict):
            return {
                "ai_duplicate_decision": "unknown",
                "confidence": 0,
                "reason": "AI response format was invalid.",
                "recommendation": "Review manually."
            }

        return parsed

    except Exception as e:
        logger.error("ai_review_duplicate_match failed: %s", e, exc_info=True)
        return {
            "ai_duplicate_decision": "unavailable",
            "confidence": 0,
            "reason": f"AI duplicate review unavailable: {str(e)}",
            "recommendation": "Use deterministic similarity result and review manually if needed."
        }