import re
from typing import Any


VALID_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}

VALID_PATH_LEVEL_FIELDS = {"parameters", "summary", "description", "servers"}

ACTION_POST_SEGMENTS = {
    "activate", "deactivate", "cancel", "approve", "reject",
    "suspend", "unsuspend", "lock", "unlock",
    "reset-password", "resend", "verify", "block", "close"
}


def _is_action_post(path: str) -> bool:
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if not segments:
        return False

    last_segment = segments[-1].lower()
    return not last_segment.startswith("{") and last_segment in ACTION_POST_SEGMENTS


def _extract_path_parameters(path: str) -> list[str]:
    return re.findall(r"{([^}]+)}", path)


def _collect_operation_parameters(path_item: dict, operation: dict) -> list[dict]:
    parameters = []

    path_level_params = path_item.get("parameters", [])
    if isinstance(path_level_params, list):
        parameters.extend([p for p in path_level_params if isinstance(p, dict)])

    operation_params = operation.get("parameters", [])
    if isinstance(operation_params, list):
        parameters.extend([p for p in operation_params if isinstance(p, dict)])

    return parameters


def _has_schema_in_content(content: Any) -> bool:
    if not isinstance(content, dict) or not content:
        return False

    for media_type, media_obj in content.items():
        if not isinstance(media_obj, dict):
            continue

        schema = media_obj.get("schema")
        if isinstance(schema, dict) and schema:
            return True

    return False


def _get_response_codes(responses: dict) -> tuple[list[str], list[str]]:
    success_codes = []
    error_codes = []

    if not isinstance(responses, dict):
        return success_codes, error_codes

    for status_code in responses.keys():
        code = str(status_code)

        if code.startswith("2"):
            success_codes.append(code)

        if code.startswith("4") or code.startswith("5") or code == "default":
            error_codes.append(code)

    return success_codes, error_codes


def _scenario_action(method: str, path: str) -> str:
    method = method.upper()

    if method == "GET":
        return f"Retrieve data from {path} and expect a documented success response."
    if method == "POST":
        return f"Submit a request to {path} and verify the documented creation or action response."
    if method == "PUT":
        return f"Replace a resource through {path} using the declared request body."
    if method == "PATCH":
        return f"Partially update a resource through {path} using the declared request body."
    if method == "DELETE":
        return f"Delete or remove a resource through {path} and verify the documented response."

    return f"Execute {method} {path} and verify the documented behavior."


def _status_from_score(score: int) -> str:
    if score >= 85:
        return "test_ready"
    if score >= 55:
        return "partial"
    return "not_ready"


def _pipeline_status(prototype_status: str, has_structure_issues: bool) -> list[dict]:
    return [
        {
            "stage": "Import OpenAPI Specification",
            "status": "passed",
            "description": "The file was uploaded and parsed successfully."
        },
        {
            "stage": "Structural Validation",
            "status": "blocked" if has_structure_issues else "passed",
            "description": (
                "Structural errors must be fixed before reliable prototype testing."
                if has_structure_issues
                else "The OpenAPI structure is valid enough for prototype analysis."
            )
        },
        {
            "stage": "Prototype Readiness Simulation",
            "status": prototype_status,
            "description": "The system estimated whether endpoints are ready for mock testing."
        },
        {
            "stage": "Governance Gate Review",
            "status": "waiting",
            "description": "Final publication decision remains handled by the governance engine."
        },
        {
            "stage": "Publish",
            "status": "waiting",
            "description": "Publishing remains separate from prototype simulation."
        }
    ]


def simulate_prototype_pipeline(
    data: dict,
    structure_issues: list | None = None,
    best_practice_issues: list | None = None
) -> dict:
    """
    Non-blocking prototype/testing simulation.

    This module does not change APRI, publishability, or governance decision.
    It only evaluates whether the OpenAPI definition is ready for a prototype/testing stage.
    """

    structure_issues = structure_issues or []
    best_practice_issues = best_practice_issues or []

    paths = data.get("paths", {})
    endpoint_results = []

    if not isinstance(paths, dict):
        return {
            "enabled": False,
            "status": "not_ready",
            "readiness_score": 0,
            "summary": {
                "total_operations": 0,
                "test_ready": 0,
                "partial": 0,
                "not_ready": 0
            },
            "pipeline_stages": _pipeline_status("not_ready", True),
            "endpoint_results": [],
            "message": "Prototype simulation could not run because paths are not valid.",
            "non_blocking": True
        }

    for path, path_item in paths.items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            method_lower = str(method).lower()

            if method_lower in VALID_PATH_LEVEL_FIELDS:
                continue

            if method_lower not in VALID_METHODS:
                continue

            if not isinstance(operation, dict):
                continue

            passed_checks = []
            failed_checks = []
            warnings = []

            # Basic operation documentation
            if isinstance(operation.get("summary"), str) and operation.get("summary", "").strip():
                passed_checks.append("summary is present")
            else:
                failed_checks.append("missing operation summary")

            if isinstance(operation.get("description"), str) and operation.get("description", "").strip():
                passed_checks.append("description is present")
            else:
                failed_checks.append("missing operation description")

            if isinstance(operation.get("operationId"), str) and operation.get("operationId", "").strip():
                passed_checks.append("operationId is present")
            else:
                failed_checks.append("missing operationId")

            if isinstance(operation.get("tags"), list) and len(operation.get("tags", [])) > 0:
                passed_checks.append("tags are present")
            else:
                failed_checks.append("missing operation tags")

            # Responses
            responses = operation.get("responses", {})
            success_codes, error_codes = _get_response_codes(responses)

            if isinstance(responses, dict) and responses:
                passed_checks.append("responses section is present")
            else:
                failed_checks.append("missing or empty responses section")

            if success_codes:
                passed_checks.append("success response is documented")
            else:
                failed_checks.append("missing 2xx success response")

            if error_codes:
                passed_checks.append("error response is documented")
            else:
                failed_checks.append("missing 4xx/5xx/default error response")

            response_descriptions_ok = True
            response_schema_count = 0
            response_content_count = 0

            if isinstance(responses, dict):
                for status_code, response_obj in responses.items():
                    if not isinstance(response_obj, dict):
                        failed_checks.append(f"response {status_code} is not an object")
                        response_descriptions_ok = False
                        continue

                    description = response_obj.get("description")
                    if not isinstance(description, str) or not description.strip():
                        failed_checks.append(f"response {status_code} is missing description")
                        response_descriptions_ok = False

                    content = response_obj.get("content")
                    if isinstance(content, dict) and content:
                        response_content_count += 1
                        if _has_schema_in_content(content):
                            response_schema_count += 1
                        else:
                            warnings.append(f"response {status_code} has content without schema")

            if response_descriptions_ok and isinstance(responses, dict) and responses:
                passed_checks.append("all response descriptions are present")

            if response_content_count > 0:
                if response_schema_count == response_content_count:
                    passed_checks.append("response schemas are available for documented content")
                else:
                    warnings.append("some response content entries do not define schemas")
            else:
                warnings.append("no response body schemas available for mock validation")

            # Request body readiness
            requires_body = False

            if method_lower in {"put", "patch"}:
                requires_body = True
            elif method_lower == "post" and not _is_action_post(path):
                requires_body = True

            if requires_body:
                request_body = operation.get("requestBody")

                if isinstance(request_body, dict):
                    passed_checks.append("requestBody is present")

                    content = request_body.get("content")
                    if isinstance(content, dict) and content:
                        passed_checks.append("requestBody content is defined")

                        if _has_schema_in_content(content):
                            passed_checks.append("requestBody schema is defined")
                        else:
                            failed_checks.append("requestBody content is missing schema")
                    else:
                        failed_checks.append("requestBody content is missing")
                else:
                    failed_checks.append("requestBody is required for this operation")
            else:
                passed_checks.append("requestBody is not required for this operation")

            # Path parameter readiness
            declared_params = _collect_operation_parameters(path_item, operation)
            path_params = _extract_path_parameters(path)

            for param_name in path_params:
                matching = [
                    p for p in declared_params
                    if p.get("name") == param_name and p.get("in") == "path"
                ]

                if not matching:
                    failed_checks.append(f"path parameter '{param_name}' is not declared")
                    continue

                param = matching[0]

                if param.get("required") is True:
                    passed_checks.append(f"path parameter '{param_name}' is required")
                else:
                    failed_checks.append(f"path parameter '{param_name}' must be required")

                if isinstance(param.get("schema"), dict) and param.get("schema"):
                    passed_checks.append(f"path parameter '{param_name}' has schema")
                else:
                    failed_checks.append(f"path parameter '{param_name}' is missing schema")

            # Score per endpoint
            total_checks = len(passed_checks) + len(failed_checks)
            endpoint_score = round((len(passed_checks) / total_checks) * 100) if total_checks else 0

            if warnings and endpoint_score >= 90:
                endpoint_score = 85

            endpoint_status = _status_from_score(endpoint_score)

            mock_scenario = {
                "name": f"Prototype {method_upper(method_lower)} {path}",
                "description": _scenario_action(method_lower, path),
                "expected_success_response": success_codes[0] if success_codes else None,
                "expected_error_response": error_codes[0] if error_codes else None,
                "requires_request_body": requires_body,
                "can_validate_request_payload": "requestBody schema is defined" in passed_checks,
                "can_validate_response_payload": response_schema_count > 0,
            }

            endpoint_results.append({
                "endpoint": f"{method_upper(method_lower)} {path}",
                "method": method_upper(method_lower),
                "path": path,
                "status": endpoint_status,
                "readiness_score": endpoint_score,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "warnings": warnings,
                "mock_scenario": mock_scenario
            })

    total_operations = len(endpoint_results)
    test_ready = len([item for item in endpoint_results if item["status"] == "test_ready"])
    partial = len([item for item in endpoint_results if item["status"] == "partial"])
    not_ready = len([item for item in endpoint_results if item["status"] == "not_ready"])

    if total_operations == 0:
        readiness_score = 0
    else:
        readiness_score = round(
            sum(item["readiness_score"] for item in endpoint_results) / total_operations,
            2
        )

    if structure_issues:
        overall_status = "not_ready"
    elif readiness_score >= 85:
        overall_status = "test_ready"
    elif readiness_score >= 55:
        overall_status = "partial"
    else:
        overall_status = "not_ready"

    return {
        "enabled": True,
        "status": overall_status,
        "readiness_score": readiness_score,
        "summary": {
            "total_operations": total_operations,
            "test_ready": test_ready,
            "partial": partial,
            "not_ready": not_ready
        },
        "pipeline_stages": _pipeline_status(overall_status, len(structure_issues) > 0),
        "endpoint_results": endpoint_results,
        "message": (
            "Prototype simulation estimates whether the OpenAPI definition is ready "
            "for mock testing before publication. It does not call real endpoints and "
            "does not affect APRI scoring or governance decision."
        ),
        "non_blocking": True,
        "related_best_practice_issues": len(best_practice_issues)
    }


def method_upper(method: str) -> str:
    return str(method).upper()