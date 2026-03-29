from fastapi import APIRouter, UploadFile, File, HTTPException
import yaml
import json

from app.services.validator import validate_openapi_structure
from app.services.best_practices import validate_best_practices

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

        structure_issues = validate_openapi_structure(data)
        best_practice_issues = validate_best_practices(data)

        issues = structure_issues + best_practice_issues

        status = "Valid"
        score = 100

        # Structural errors block the API
        if len(structure_issues) > 0:
            status = "Rejected"
            score = 0

        # Best practice warnings reduce score
        elif len(best_practice_issues) > 0:
            status = "Needs Improvement"
            score = max(100 - (len(best_practice_issues) * 5), 60)

        return {
            "filename": file.filename,
            "status": status,
            "score": score,
            "issues": issues,
            "detected_keys": list(data.keys()) if isinstance(data, dict) else []
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid OpenAPI file: {str(e)}")