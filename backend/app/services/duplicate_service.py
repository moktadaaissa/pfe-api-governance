"""
duplicate_service.py — Multi-signal duplicate detection engine

Detection layers (applied in order):
  1. Exact match          — normalized path + method identical → 100% → "exact_duplicate"
  2. Structural signals   — ordered path similarity (LCS-based) + method match
  3. Semantic signals     — text similarity on summary, description, tags, operationId
  4. Combined score       — weighted fusion of structural + semantic signals
  5. AI review            — called on all matches above the suspicion threshold
  6. Final classification — exact_duplicate / strong_overlap / potential_overlap / different

Thresholds:
  combined_score >= 85  → strong_overlap   (AI always called)
  combined_score >= 55  → potential_overlap (AI always called)
  combined_score <  55  → filtered out (not reported)
"""

import re
from typing import Any

from app.services.db_service import get_connection, extract_endpoints
from app.services.ai_service import ai_review_duplicate_match


# ─── Path Normalization ────────────────────────────────────────────────────────

def normalize_path(path: str) -> str:
    """Replace all {param} segments with {} placeholder."""
    parts = []
    for part in path.strip("/").split("/"):
        if part.startswith("{") and part.endswith("}"):
            parts.append("{param}")
        else:
            parts.append(part.lower().strip())
    return "/" + "/".join(parts)


def path_segments(path: str) -> list[str]:
    return [p for p in normalize_path(path).strip("/").split("/") if p]


# ─── Structural Similarity (LCS-based, order-aware) ───────────────────────────

def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longest Common Subsequence — preserves segment order."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def compute_path_similarity(path_a: str, path_b: str) -> float:
    """
    Order-aware path similarity using LCS.
    /users/orders and /orders/users are NOT the same.
    Returns 0.0–100.0.
    """
    seg_a = path_segments(path_a)
    seg_b = path_segments(path_b)

    if not seg_a and not seg_b:
        return 100.0
    if not seg_a or not seg_b:
        return 0.0

    lcs = _lcs_length(seg_a, seg_b)
    max_len = max(len(seg_a), len(seg_b))
    return round((lcs / max_len) * 100, 2)


def compute_depth_similarity(path_a: str, path_b: str) -> float:
    """Penalize paths with very different depths."""
    d_a = len(path_segments(path_a))
    d_b = len(path_segments(path_b))
    if d_a == 0 and d_b == 0:
        return 100.0
    if d_a == 0 or d_b == 0:
        return 0.0
    return round((min(d_a, d_b) / max(d_a, d_b)) * 100, 2)


# ─── Semantic Similarity (token-based TF-style) ────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens, min length 2, split on camelCase too."""
    if not text:
        return set()
    # Split camelCase
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    tokens = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
    # Remove very generic stop words
    stopwords = {"the", "an", "is", "of", "to", "in", "for", "and", "or", "a", "by", "get", "set"}
    return {t for t in tokens if t not in stopwords}


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def compute_text_similarity(text_a: str, text_b: str) -> float:
    """Token-level Jaccard similarity between two text fields. Returns 0.0–100.0."""
    return round(_jaccard(_tokenize(text_a), _tokenize(text_b)) * 100, 2)


def compute_tags_similarity(tags_a: str, tags_b: str) -> float:
    """Compare comma-separated tag strings."""
    set_a = {t.strip().lower() for t in tags_a.split(",") if t.strip()} if tags_a else set()
    set_b = {t.strip().lower() for t in tags_b.split(",") if t.strip()} if tags_b else set()
    return round(_jaccard(set_a, set_b) * 100, 2)


# ─── Combined Score ────────────────────────────────────────────────────────────

WEIGHTS = {
    "path":        0.40,   # Structural — most important signal
    "depth":       0.08,   # Penalize very different path depths
    "summary":     0.20,   # What the endpoint does
    "description": 0.15,   # Detailed intent
    "tags":        0.10,   # Resource grouping
    "operation_id":0.07,   # Naming intent
}


def compute_combined_score(
    uploaded: dict,
    existing: dict,
) -> dict[str, float]:
    """
    Compute a multi-signal similarity score between two endpoints.
    Returns individual signal scores and a weighted combined score.
    """
    path_sim   = compute_path_similarity(uploaded["path"], existing["path"])
    depth_sim  = compute_depth_similarity(uploaded["path"], existing["path"])
    summary_sim = compute_text_similarity(
        uploaded.get("summary", ""), existing.get("summary", "")
    )
    desc_sim   = compute_text_similarity(
        uploaded.get("description", ""), existing.get("description", "")
    )
    tags_sim   = compute_tags_similarity(
        uploaded.get("tags", ""), existing.get("tags", "")
    )
    op_sim     = compute_text_similarity(
        uploaded.get("operation_id", ""), existing.get("operation_id", "")
    )

    combined = (
        WEIGHTS["path"]         * path_sim +
        WEIGHTS["depth"]        * depth_sim +
        WEIGHTS["summary"]      * summary_sim +
        WEIGHTS["description"]  * desc_sim +
        WEIGHTS["tags"]         * tags_sim +
        WEIGHTS["operation_id"] * op_sim
    )

    return {
        "path_similarity":        path_sim,
        "depth_similarity":       depth_sim,
        "summary_similarity":     summary_sim,
        "description_similarity": desc_sim,
        "tags_similarity":        tags_sim,
        "operation_id_similarity": op_sim,
        "combined_score":         round(combined, 2),
    }


# ─── Classification ────────────────────────────────────────────────────────────

STRONG_OVERLAP_THRESHOLD   = 85.0
POTENTIAL_OVERLAP_THRESHOLD = 55.0


def classify_match(
    uploaded: dict,
    existing: dict,
    scores: dict,
) -> str | None:
    """
    Returns the duplicate type string or None if not suspicious enough.
    Exact duplicates are detected before scoring.
    """
    combined = scores["combined_score"]

    if combined >= STRONG_OVERLAP_THRESHOLD:
        return "strong_overlap"
    if combined >= POTENTIAL_OVERLAP_THRESHOLD:
        return "potential_overlap"
    return None


# ─── Main Detection Function ───────────────────────────────────────────────────

def detect_duplicates(data: dict) -> list[dict[str, Any]]:
    """
    Full multi-signal duplicate detection pipeline.

    For each uploaded endpoint:
      1. Check exact match (path + method after normalization)
      2. Compute multi-signal combined score for all existing endpoints
      3. For suspicious matches, call AI review
      4. Return sorted results (exact first, then by combined score desc)
    """
    uploaded_endpoints = extract_endpoints(data)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            endpoints.path,
            endpoints.method,
            endpoints.summary,
            endpoints.description,
            endpoints.operation_id,
            endpoints.tags,
            apis.id    AS api_id,
            apis.filename,
            apis.title,
            apis.version
        FROM endpoints
        JOIN apis ON endpoints.api_id = apis.id
    """)
    existing_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    matches = []

    for uploaded in uploaded_endpoints:
        norm_uploaded = normalize_path(uploaded["path"])

        for row in existing_rows:
            norm_existing = normalize_path(row["path"])

            # ── Layer 1: Exact match ──────────────────────────────────────────
            if (
                uploaded["method"].lower() == row["method"].lower()
                and norm_uploaded == norm_existing
            ):
                matches.append({
                    "type": "exact_duplicate",
                    "combined_score": 100.0,
                    "signal_scores": {
                        "path_similarity": 100.0,
                        "depth_similarity": 100.0,
                        "summary_similarity": compute_text_similarity(
                            uploaded.get("summary", ""), row.get("summary", "")
                        ),
                        "description_similarity": compute_text_similarity(
                            uploaded.get("description", ""), row.get("description", "")
                        ),
                        "tags_similarity": compute_tags_similarity(
                            uploaded.get("tags", ""), row.get("tags", "")
                        ),
                        "operation_id_similarity": compute_text_similarity(
                            uploaded.get("operation_id", ""), row.get("operation_id", "")
                        ),
                    },
                    "method_match": True,
                    "uploaded_endpoint": {
                        "path": uploaded["path"],
                        "method": uploaded["method"].upper(),
                        "summary": uploaded.get("summary", ""),
                        "tags": uploaded.get("tags", ""),
                    },
                    "matched_api": {
                        "id": row["api_id"],
                        "filename": row["filename"],
                        "title": row["title"],
                        "version": row["version"],
                    },
                    "matched_endpoint": {
                        "path": row["path"],
                        "method": row["method"].upper(),
                        "summary": row.get("summary", ""),
                        "tags": row.get("tags", ""),
                    },
                    "ai_review": {
                        "ai_duplicate_decision": "duplicate",
                        "confidence": 100,
                        "reason": "Exact path and method match after normalization.",
                        "recommendation": "Block publication. This endpoint already exists in the catalog.",
                    },
                })
                continue

            # ── Layer 2 & 3: Multi-signal scoring ────────────────────────────
            scores = compute_combined_score(uploaded, row)
            duplicate_type = classify_match(uploaded, row, scores)

            if duplicate_type is None:
                continue

            method_match = uploaded["method"].lower() == row["method"].lower()

            # ── Layer 4: AI review on all suspicious matches ──────────────────
            ai_result = ai_review_duplicate_match(
                uploaded_endpoint={
                    "path": uploaded["path"],
                    "method": uploaded["method"].upper(),
                    "summary": uploaded.get("summary", ""),
                    "description": uploaded.get("description", ""),
                    "tags": uploaded.get("tags", ""),
                    "operation_id": uploaded.get("operation_id", ""),
                },
                matched_endpoint={
                    "path": row["path"],
                    "method": row["method"].upper(),
                    "summary": row.get("summary", ""),
                    "description": row.get("description", ""),
                    "tags": row.get("tags", ""),
                    "operation_id": row.get("operation_id", ""),
                },
                matched_api={
                    "id": row["api_id"],
                    "filename": row["filename"],
                    "title": row["title"],
                    "version": row["version"],
                },
                similarity=scores["combined_score"],
            )

            # ── Layer 5: Upgrade/downgrade type based on AI decision ──────────
            ai_decision = ai_result.get("ai_duplicate_decision", "unknown")
            ai_confidence = ai_result.get("confidence", 0)

            # If AI says "different" with high confidence, suppress the match
            if ai_decision == "different" and ai_confidence >= 80:
                continue

            # If AI says "duplicate" with high confidence, upgrade to strong_overlap
            if ai_decision == "duplicate" and ai_confidence >= 75 and duplicate_type == "potential_overlap":
                duplicate_type = "strong_overlap"

            matches.append({
                "type": duplicate_type,
                "combined_score": scores["combined_score"],
                "signal_scores": scores,
                "method_match": method_match,
                "uploaded_endpoint": {
                    "path": uploaded["path"],
                    "method": uploaded["method"].upper(),
                    "summary": uploaded.get("summary", ""),
                    "tags": uploaded.get("tags", ""),
                },
                "matched_api": {
                    "id": row["api_id"],
                    "filename": row["filename"],
                    "title": row["title"],
                    "version": row["version"],
                },
                "matched_endpoint": {
                    "path": row["path"],
                    "method": row["method"].upper(),
                    "summary": row.get("summary", ""),
                    "tags": row.get("tags", ""),
                },
                "ai_review": ai_result,
            })

    # Sort: exact first, then strong_overlap, then potential_overlap, then by score desc
    type_order = {"exact_duplicate": 0, "strong_overlap": 1, "potential_overlap": 2}
    matches.sort(key=lambda x: (type_order.get(x["type"], 9), -x["combined_score"]))

    return matches