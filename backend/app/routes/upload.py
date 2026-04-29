from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import yaml
import json

from app.services.validator import validate_openapi_structure
from app.services.best_practices import validate_best_practices
from app.services.scoring import compute_apri
from app.services.ai_service import ai_review_openapi, ai_generate_safe_fixes
from app.services.simulation_service import simulate_ai_improvement
from app.services.duplicate_service import detect_duplicates
from app.services.db_service import save_api_to_catalog, list_catalog_apis
from app.services.prototype_service import simulate_prototype_pipeline
from app.services.auth_service import get_current_user, require_admin

router = APIRouter()


def _parse_uploaded_openapi(file: UploadFile, content: bytes):
    if not file.filename.endswith((".yaml", ".yml", ".json")):
        raise HTTPException(status_code=400, detail="File must be YAML or JSON")

    try:
        if file.filename.endswith((".yaml", ".yml")):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid OpenAPI file: {str(e)}")

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="OpenAPI file must parse to an object")

    return data


def _compute_duplicate_status(duplicate_matches: list) -> str:
    if any(match.get("type") == "exact_duplicate" for match in duplicate_matches):
        return "blocked"
    if duplicate_matches:
        return "warning"
    return "clean"


def _compute_governance_decision(
    structure_issues: list,
    apri_result: dict,
    duplicate_status: str,
) -> str:
    if structure_issues:
        return "BLOCK"
    if duplicate_status == "blocked":
        return "BLOCK"
    if not apri_result.get("publishable", False):
        return "NEEDS_FIX"
    return "ALLOW"


@router.get("/catalog")
async def get_catalog(current_user: dict = Depends(get_current_user)):
    return {
        "apis": list_catalog_apis()
    }


@router.post("/upload-openapi")
async def upload_openapi(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()
    data = _parse_uploaded_openapi(file, content)

    structure_issues = validate_openapi_structure(data)
    best_practice_issues = validate_best_practices(data)
    all_issues = structure_issues + best_practice_issues

    apri_result = compute_apri(data, structure_issues, best_practice_issues)

    broad_ai_review = ai_review_openapi(data)
    safe_fix_suggestions = ai_generate_safe_fixes(data)

    simulation_result = simulate_ai_improvement(
        data,
        safe_fix_suggestions if isinstance(safe_fix_suggestions, list) else None
    )

    prototype_result = simulate_prototype_pipeline(
        data,
        structure_issues=structure_issues,
        best_practice_issues=best_practice_issues
    )

    duplicate_matches = detect_duplicates(data)
    duplicate_status = _compute_duplicate_status(duplicate_matches)

    governance_decision = _compute_governance_decision(
        structure_issues,
        apri_result,
        duplicate_status
    )

    if structure_issues:
        status = "Rejected"
    elif best_practice_issues:
        status = "Needs Improvement"
    else:
        status = "Valid"

    simulated_score = simulation_result.get("simulated_score")
    score_improvement = None

    if simulated_score is not None:
        score_improvement = round(simulated_score - apri_result["apri_score"], 2)

    return {
        "filename": file.filename,
        "uploaded_by": current_user["username"],
        "user_role": current_user["role"],
        "status": status,
        "governance_decision": governance_decision,
        "apri_score": apri_result["apri_score"],
        "grade": apri_result["grade"],
        "publishable": apri_result["publishable"],
        "issue_summary": {
            "structure_errors": len(structure_issues),
            "best_practice_warnings": len(best_practice_issues),
            "total_issues": len(all_issues),
        },
        "category_scores": apri_result.get("category_scores", {}),
        "ratios": apri_result.get("ratios", {}),
        "structure_issues": structure_issues,
        "best_practice_issues": best_practice_issues,
        "issues": all_issues,
        "ai_review": {
            "broad_review": broad_ai_review,
            "safe_fix_suggestions": safe_fix_suggestions,
        },
        "simulation": {
            "enabled": simulation_result.get("simulated", False),
            "scope": "safe_fixes_only",
            "included_fix_types": [
                "summary",
                "description",
                "operationId",
                "tags",
                "response_description",
            ],
            "excluded_review_types": [
                "endpoint naming",
                "REST design",
                "HTTP method usage",
                "request body definition",
                "schema/response modeling",
                "path restructuring",
                "parameter redesign",
                "status code redesign",
            ],
            "explanation": (
                "This simulated score is based only on safe AI fixes automatically "
                "applied to an internal copy of your OpenAPI file. These include "
                "documentation and metadata improvements such as summaries, descriptions, "
                "operation IDs, tags, and response descriptions. Broader design suggestions "
                "were not auto-applied and should be reviewed manually."
            ),
            "message": simulation_result.get("message"),
            "based_on_safe_fixes": safe_fix_suggestions if isinstance(safe_fix_suggestions, list) else [],
            "simulated_score": simulated_score,
            "simulated_grade": simulation_result.get("simulated_grade"),
            "simulated_publishable": simulation_result.get("simulated_publishable"),
            "score_improvement": score_improvement,
            "applied_changes": simulation_result.get("applied_changes", []),
            "skipped_changes": simulation_result.get("skipped_changes", []),
            "remaining_issues": simulation_result.get("remaining_issues", []),
            "remaining_structure_issues": simulation_result.get("remaining_structure_issues", []),
            "simulated_category_scores": simulation_result.get("simulated_category_scores", {}),
            "simulated_ratios": simulation_result.get("simulated_ratios", {}),
            "error": simulation_result.get("error"),
        },
        "prototype_testing": prototype_result,
        "duplicates": {
            "status": duplicate_status,
            "count": len(duplicate_matches),
            "matches": duplicate_matches,
        },
        "catalog_entry_id": None,
        "detected_keys": list(data.keys()),
    }


@router.post("/publish-openapi")
async def publish_openapi(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin)
):
    content = await file.read()
    data = _parse_uploaded_openapi(file, content)

    structure_issues = validate_openapi_structure(data)
    best_practice_issues = validate_best_practices(data)
    apri_result = compute_apri(data, structure_issues, best_practice_issues)

    duplicate_matches = detect_duplicates(data)
    duplicate_status = _compute_duplicate_status(duplicate_matches)

    governance_decision = _compute_governance_decision(
        structure_issues,
        apri_result,
        duplicate_status
    )

    if governance_decision != "ALLOW":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This API cannot be published yet.",
                "decision": governance_decision,
                "structure_issues": structure_issues,
                "best_practice_issues": best_practice_issues,
                "duplicates": {
                    "status": duplicate_status,
                    "count": len(duplicate_matches),
                    "matches": duplicate_matches,
                },
                "publishable": apri_result.get("publishable", False),
                "apri_score": apri_result.get("apri_score"),
                "grade": apri_result.get("grade"),
            },
        )

    saved_api_id = save_api_to_catalog(data, file.filename)

    return {
        "message": "API published to governance catalog successfully.",
        "published_by": current_user["username"],
        "role": current_user["role"],
        "decision": governance_decision,
        "catalog_entry_id": saved_api_id,
        "duplicates": {
            "status": duplicate_status,
            "count": len(duplicate_matches),
            "matches": duplicate_matches,
        },
    }