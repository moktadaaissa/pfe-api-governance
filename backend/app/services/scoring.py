def compute_apri(data: dict, structure_issues: list) -> dict:
    # Hard structural gate
    if len(structure_issues) > 0:
        return {
            "apri_score": 0.0,
            "publishable": False,
            "grade": "Rejected",
            "category_scores": {
                "documentation": 0.0,
                "operational_clarity": 0.0,
                "response_readiness": 0.0,
                "rest_design_quality": 0.0
            },
            "ratios": {
                "summary": 0.0,
                "description": 0.0,
                "response_description": 0.0,
                "description_adequacy": 0.0,
                "operation_id": 0.0,
                "tags": 0.0,
                "success_response": 0.0,
                "error_response": 0.0,
                "request_body": 0.0,
                "verb_rule": 0.0,
                "underscore_rule": 0.0
            }
        }

    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    valid_path_level_fields = {"parameters", "summary", "description", "servers"}
    discouraged_verbs = {"get", "create", "update", "delete", "set", "add", "remove"}

    action_post_segments = {
        "activate",
        "deactivate",
        "cancel",
        "approve",
        "reject",
        "suspend",
        "unsuspend",
        "lock",
        "unlock",
        "reset-password",
        "resend",
        "verify",
        "block",
        "close"
    }

    paths = data.get("paths", {})

    total_operations = 0
    operations_with_summary = 0
    operations_with_description = 0
    operations_with_good_description = 0
    operations_with_operation_id = 0
    operations_with_tags = 0
    operations_with_2xx = 0
    operations_with_error_response = 0

    total_responses = 0
    responses_with_description = 0

    applicable_request_body_ops = 0
    request_body_compliant_ops = 0

    total_paths = 0
    paths_without_discouraged_verbs = 0
    paths_without_underscores = 0

    if not isinstance(paths, dict):
        paths = {}

    for path, methods in paths.items():
        if not isinstance(path, str):
            continue

        total_paths += 1

        path_parts = [
            part for part in path.strip("/").split("/")
            if part and not part.startswith("{")
        ]

        has_discouraged_verb = False
        has_underscore = False

        for part in path_parts:
            clean_part = part.lower()

            for verb in discouraged_verbs:
                if clean_part == verb or clean_part.startswith(verb):
                    has_discouraged_verb = True
                    break

            if "_" in clean_part:
                has_underscore = True

        if not has_discouraged_verb:
            paths_without_discouraged_verbs += 1

        if not has_underscore:
            paths_without_underscores += 1

        if not isinstance(methods, dict):
            continue

        for method, details in methods.items():
            if method in valid_path_level_fields:
                continue

            if method.lower() not in valid_methods:
                continue

            if not isinstance(details, dict):
                continue

            total_operations += 1
            method_lower = method.lower()

            if isinstance(details.get("summary"), str) and details.get("summary", "").strip():
                operations_with_summary += 1

            if isinstance(details.get("description"), str) and details.get("description", "").strip():
                operations_with_description += 1
                if len(details["description"].strip()) >= 10:
                    operations_with_good_description += 1

            if isinstance(details.get("operationId"), str) and details.get("operationId", "").strip():
                operations_with_operation_id += 1

            if isinstance(details.get("tags"), list) and len(details.get("tags", [])) > 0:
                operations_with_tags += 1

            if method_lower in {"put", "patch"}:
                applicable_request_body_ops += 1
                if "requestBody" in details:
                    request_body_compliant_ops += 1

            elif method_lower == "post":
                path_segments = [segment for segment in path.strip("/").split("/") if segment]
                last_segment = path_segments[-1].lower() if path_segments else ""

                is_action_post = (
                    not last_segment.startswith("{")
                    and last_segment in action_post_segments
                )

                if not is_action_post:
                    applicable_request_body_ops += 1
                    if "requestBody" in details:
                        request_body_compliant_ops += 1

            responses = details.get("responses", {})

            has_2xx = False
            has_error = False

            if isinstance(responses, dict):
                for status_code, response_details in responses.items():
                    code = str(status_code)

                    total_responses += 1

                    if code.startswith("2"):
                        has_2xx = True

                    if code.startswith("4") or code.startswith("5") or code == "default":
                        has_error = True

                    if isinstance(response_details, dict):
                        if isinstance(response_details.get("description"), str) and response_details.get("description", "").strip():
                            responses_with_description += 1

            if has_2xx:
                operations_with_2xx += 1

            if has_error:
                operations_with_error_response += 1

    def safe_ratio(numerator, denominator):
        if denominator == 0:
            return 100.0
        return (numerator / denominator) * 100.0

    r_summary = safe_ratio(operations_with_summary, total_operations)
    r_description = safe_ratio(operations_with_description, total_operations)
    r_response_desc = safe_ratio(responses_with_description, total_responses)
    r_desc_adequacy = safe_ratio(operations_with_good_description, operations_with_description)

    r_operation_id = safe_ratio(operations_with_operation_id, total_operations)
    r_tags = safe_ratio(operations_with_tags, total_operations)

    r_2xx = safe_ratio(operations_with_2xx, total_operations)
    r_error = safe_ratio(operations_with_error_response, total_operations)
    r_request_body = safe_ratio(request_body_compliant_ops, applicable_request_body_ops)

    r_verb_rule = safe_ratio(paths_without_discouraged_verbs, total_paths)
    r_underscore_rule = safe_ratio(paths_without_underscores, total_paths)

    c_doc = 0.20 * r_summary + 0.35 * r_description + 0.30 * r_response_desc + 0.15 * r_desc_adequacy
    c_ops = 0.55 * r_operation_id + 0.45 * r_tags
    c_resp = 0.40 * r_2xx + 0.40 * r_error + 0.20 * r_request_body
    c_rest = 0.60 * r_verb_rule + 0.40 * r_underscore_rule

    apri_score = round(0.30 * c_doc + 0.20 * c_ops + 0.35 * c_resp + 0.15 * c_rest, 2)

    # Critical ratio caps
    if r_2xx == 0:
        apri_score = min(apri_score, 70.0)

    if r_error == 0:
        apri_score = min(apri_score, 75.0)
    elif r_error < 50:
        apri_score = min(apri_score, 85.0)

    apri_score = round(apri_score, 2)

    if apri_score >= 90:
        grade = "Excellent"
    elif apri_score >= 80:
        grade = "Good"
    elif apri_score >= 70:
        grade = "Acceptable"
    elif apri_score >= 50:
        grade = "Weak"
    else:
        grade = "Poor"

    return {
        "apri_score": apri_score,
        "publishable": apri_score >= 70,
        "grade": grade,
        "category_scores": {
            "documentation": round(c_doc, 2),
            "operational_clarity": round(c_ops, 2),
            "response_readiness": round(c_resp, 2),
            "rest_design_quality": round(c_rest, 2)
        },
        "ratios": {
            "summary": round(r_summary, 2),
            "description": round(r_description, 2),
            "response_description": round(r_response_desc, 2),
            "description_adequacy": round(r_desc_adequacy, 2),
            "operation_id": round(r_operation_id, 2),
            "tags": round(r_tags, 2),
            "success_response": round(r_2xx, 2),
            "error_response": round(r_error, 2),
            "request_body": round(r_request_body, 2),
            "verb_rule": round(r_verb_rule, 2),
            "underscore_rule": round(r_underscore_rule, 2)
        }
    }