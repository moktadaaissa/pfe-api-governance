from fastapi import APIRouter, UploadFile, File, HTTPException
import yaml
import json

from app.services.validator import validate_openapi_structure
from app.services.best_practices import validate_best_practices
from app.services.scoring import compute_apri
from app.services.ai_service import ai_review_openapi

router = APIRouter()


@router.post("/upload-openapi")
async def upload_openapi(file: UploadFile = File(...)):

    if not file.filename.endswith((".yaml", ".yml", ".json")):
        raise HTTPException(status_code=400, detail="File must be YAML or JSON")

    content = await file.read()

    try:
        if file.filename.endswith((".yaml", ".yml")):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid OpenAPI file: {str(e)}")

    structure_issues = validate_openapi_structure(data)
    best_practice_issues = validate_best_practices(data)
    all_issues = structure_issues + best_practice_issues

    apri_result = compute_apri(data, structure_issues)
    ai_review = ai_review_openapi(data)

    if len(structure_issues) > 0:
        status = "Rejected"
    elif len(best_practice_issues) > 0:
        status = "Needs Improvement"
    else:
        status = "Valid"

    return {
        "filename": file.filename,
        "status": status,
        "apri_score": apri_result["apri_score"],
        "grade": apri_result["grade"],
        "publishable": apri_result["publishable"],
        "issue_summary": {
            "structure_errors": len(structure_issues),
            "best_practice_warnings": len(best_practice_issues),
            "total_issues": len(all_issues)
        },
        "category_scores": apri_result.get("category_scores", {}),
        "ratios": apri_result.get("ratios", {}),
        "structure_issues": structure_issues,
        "best_practice_issues": best_practice_issues,
        "issues": all_issues,
        "ai_review": ai_review,
        "detected_keys": list(data.keys()) if isinstance(data, dict) else []
    }