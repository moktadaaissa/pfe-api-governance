from typing import Any
from app.services.db_service import get_connection, extract_endpoints


def normalize_path(path: str) -> str:
    parts = []
    for part in path.strip("/").split("/"):
        if part.startswith("{") and part.endswith("}"):
            parts.append("{}")
        else:
            parts.append(part.lower())
    return "/" + "/".join(parts)


def path_segments(path: str) -> list[str]:
    return [p.lower() for p in path.strip("/").split("/") if p]


def compute_path_similarity(path_a: str, path_b: str) -> float:
    seg_a = path_segments(normalize_path(path_a))
    seg_b = path_segments(normalize_path(path_b))

    if not seg_a and not seg_b:
        return 100.0

    common = len(set(seg_a) & set(seg_b))
    total = len(set(seg_a) | set(seg_b))

    if total == 0:
        return 0.0

    return round((common / total) * 100, 2)


def classify_duplicate(path_a: str, method_a: str, path_b: str, method_b: str) -> tuple[str | None, float]:
    norm_a = normalize_path(path_a)
    norm_b = normalize_path(path_b)

    method_a = method_a.lower()
    method_b = method_b.lower()

    if method_a == method_b and norm_a == norm_b:
        return "exact_duplicate", 100.0

    similarity = compute_path_similarity(path_a, path_b)

    if method_a == method_b and similarity >= 60:
        return "potential_overlap", similarity

    return None, similarity


def detect_duplicates(data: dict) -> list[dict[str, Any]]:
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
        apis.id AS api_id,
        apis.filename,
        apis.title,
        apis.version
    FROM endpoints
    JOIN apis ON endpoints.api_id = apis.id
    """)

    existing_rows = cursor.fetchall()
    conn.close()

    matches = []

    for uploaded in uploaded_endpoints:
        for row in existing_rows:
            duplicate_type, similarity = classify_duplicate(
                uploaded["path"],
                uploaded["method"],
                row["path"],
                row["method"]
            )

            if duplicate_type is None:
                continue

            matches.append({
                "type": duplicate_type,
                "similarity": similarity,
                "uploaded_endpoint": {
                    "path": uploaded["path"],
                    "method": uploaded["method"].upper()
                },
                "matched_api": {
                    "id": row["api_id"],
                    "filename": row["filename"],
                    "title": row["title"],
                    "version": row["version"]
                },
                "matched_endpoint": {
                    "path": row["path"],
                    "method": row["method"].upper()
                }
            })

    matches.sort(key=lambda x: (x["type"] != "exact_duplicate", -x["similarity"]))
    return matches