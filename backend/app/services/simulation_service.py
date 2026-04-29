from copy import deepcopy

from app.services.validator import validate_openapi_structure
from app.services.best_practices import validate_best_practices
from app.services.scoring import compute_apri
from app.services.ai_service import ai_generate_safe_fixes

SAFE_FIELDS = {
    "summary",
    "description",
    "operationId",
    "tags",
    "response_description",
}


def apply_safe_suggestions(spec: dict, suggestions: list) -> tuple[list, list]:
    applied_changes = []
    skipped_changes = []

    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return applied_changes, skipped_changes

    for item in suggestions:
        try:
            path = item.get("path")
            method = str(item.get("method", "")).lower()
            field = item.get("field")
            action = item.get("action")
            value = item.get("value")
            target = item.get("target", {})

            if action != "replace":
                skipped_changes.append({
                    "reason": "unsupported_action",
                    "suggestion": item
                })
                continue

            if field not in SAFE_FIELDS:
                skipped_changes.append({
                    "reason": "unsafe_field",
                    "suggestion": item
                })
                continue

            if path not in paths or not isinstance(paths[path], dict):
                skipped_changes.append({
                    "reason": "path_not_found",
                    "suggestion": item
                })
                continue

            if method not in paths[path] or not isinstance(paths[path][method], dict):
                skipped_changes.append({
                    "reason": "method_not_found",
                    "suggestion": item
                })
                continue

            operation = paths[path][method]

            if field in {"summary", "description", "operationId"}:
                if not isinstance(value, str) or not value.strip():
                    skipped_changes.append({
                        "reason": "invalid_string_value",
                        "suggestion": item
                    })
                    continue

                old_value = operation.get(field)
                operation[field] = value

                applied_changes.append({
                    "path": path,
                    "method": method.upper(),
                    "field": field,
                    "old_value": old_value,
                    "new_value": value
                })
                continue

            if field == "tags":
                if (
                    not isinstance(value, list)
                    or len(value) == 0
                    or not all(isinstance(tag, str) and tag.strip() for tag in value)
                ):
                    skipped_changes.append({
                        "reason": "invalid_tags_value",
                        "suggestion": item
                    })
                    continue

                old_value = operation.get("tags")
                operation["tags"] = value

                applied_changes.append({
                    "path": path,
                    "method": method.upper(),
                    "field": "tags",
                    "old_value": old_value,
                    "new_value": value
                })
                continue

            if field == "response_description":
                status_code = str(target.get("status_code", "")).strip()
                responses = operation.get("responses", {})

                if not status_code:
                    skipped_changes.append({
                        "reason": "missing_status_code_target",
                        "suggestion": item
                    })
                    continue

                if not isinstance(value, str) or not value.strip():
                    skipped_changes.append({
                        "reason": "invalid_response_description_value",
                        "suggestion": item
                    })
                    continue

                if not isinstance(responses, dict):
                    skipped_changes.append({
                        "reason": "responses_not_found",
                        "suggestion": item
                    })
                    continue

                if status_code not in responses or not isinstance(responses[status_code], dict):
                    skipped_changes.append({
                        "reason": "response_status_not_found",
                        "suggestion": item
                    })
                    continue

                old_value = responses[status_code].get("description")
                responses[status_code]["description"] = value

                applied_changes.append({
                    "path": path,
                    "method": method.upper(),
                    "field": "response_description",
                    "target": {"status_code": status_code},
                    "old_value": old_value,
                    "new_value": value
                })
                continue

        except Exception as e:
            skipped_changes.append({
                "reason": f"exception: {str(e)}",
                "suggestion": item
            })

    return applied_changes, skipped_changes


def simulate_ai_improvement(data: dict, suggestions: list | None = None) -> dict:
    try:
        simulated_copy = deepcopy(data)

        if suggestions is None:
            suggestions = ai_generate_safe_fixes(data)

        if isinstance(suggestions, dict) and suggestions.get("error"):
            return {
                "simulated": False,
                "error": suggestions["error"],
                "message": "Safe-fix simulation could not be generated.",
                "applied_changes": [],
                "skipped_changes": [],
                "remaining_issues": [],
                "remaining_structure_issues": [],
                "simulated_score": None,
                "simulated_grade": None,
                "simulated_publishable": None,
                "simulated_category_scores": {},
                "simulated_ratios": {},
            }

        if not isinstance(suggestions, list):
            return {
                "simulated": False,
                "error": "AI suggestions format is invalid",
                "message": "Safe-fix simulation could not be generated.",
                "applied_changes": [],
                "skipped_changes": [],
                "remaining_issues": [],
                "remaining_structure_issues": [],
                "simulated_score": None,
                "simulated_grade": None,
                "simulated_publishable": None,
                "simulated_category_scores": {},
                "simulated_ratios": {},
            }

        if len(suggestions) == 0:
            structure_issues = validate_openapi_structure(simulated_copy)
            best_practice_issues = validate_best_practices(simulated_copy)
            apri_result = compute_apri(simulated_copy, structure_issues, best_practice_issues)

            return {
                "simulated": True,
                "error": None,
                "message": "No safe AI fixes were confidently generated for simulation.",
                "applied_changes": [],
                "skipped_changes": [],
                "remaining_issues": best_practice_issues,
                "remaining_structure_issues": structure_issues,
                "simulated_score": apri_result["apri_score"],
                "simulated_grade": apri_result["grade"],
                "simulated_publishable": apri_result["publishable"],
                "simulated_category_scores": apri_result.get("category_scores", {}),
                "simulated_ratios": apri_result.get("ratios", {}),
            }

        applied_changes, skipped_changes = apply_safe_suggestions(simulated_copy, suggestions)

        structure_issues = validate_openapi_structure(simulated_copy)
        best_practice_issues = validate_best_practices(simulated_copy)
        apri_result = compute_apri(simulated_copy, structure_issues, best_practice_issues)

        message = "Safe AI fixes were simulated on an internal copy of the uploaded file."
        if len(applied_changes) == 0:
            message = "Safe AI fix suggestions were generated, but none could be applied."

        return {
            "simulated": True,
            "error": None,
            "message": message,
            "applied_changes": applied_changes,
            "skipped_changes": skipped_changes,
            "remaining_issues": best_practice_issues,
            "remaining_structure_issues": structure_issues,
            "simulated_score": apri_result["apri_score"],
            "simulated_grade": apri_result["grade"],
            "simulated_publishable": apri_result["publishable"],
            "simulated_category_scores": apri_result.get("category_scores", {}),
            "simulated_ratios": apri_result.get("ratios", {}),
        }

    except Exception as e:
        return {
            "simulated": False,
            "error": str(e),
            "message": "Safe-fix simulation failed unexpectedly.",
            "applied_changes": [],
            "skipped_changes": [],
            "remaining_issues": [],
            "remaining_structure_issues": [],
            "simulated_score": None,
            "simulated_grade": None,
            "simulated_publishable": None,
            "simulated_category_scores": {},
            "simulated_ratios": {},
        }