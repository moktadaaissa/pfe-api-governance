def compute_apri(data: dict, structure_issues: list, best_practice_issues: list) -> dict:
    if len(structure_issues) > 0:
        return {
            "apri_score": 0.0,
            "publishable": False,
            "grade": "Rejected",
            "category_scores": {
                "documentation": 0.0,
                "operational_clarity": 0.0,
                "response_readiness": 0.0,
                "rest_governance_quality": 0.0
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
                "underscore_rule": 0.0,
                "method_alignment": 0.0
            }
        }

    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    valid_path_level_fields = {"parameters", "summary", "description", "servers"}

    discouraged_verbs = {
        "get", "create", "update", "delete", "set", "add", "remove",
        "approve", "reject", "block", "close", "activate", "deactivate"
    }

    action_post_segments = {
        "activate", "deactivate", "cancel", "approve", "reject",
        "suspend", "unsuspend", "lock", "unlock",
        "reset-password", "resend", "verify", "block", "close"
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

    method_alignment_total = 0
    method_alignment_ok = 0

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

            # Method-path alignment
            method_alignment_total += 1

            path_segments = [segment for segment in path.strip("/").split("/") if segment]
            last_segment = path_segments[-1].lower() if path_segments else ""

            is_action_path = (
                last_segment
                and not last_segment.startswith("{")
                and last_segment in action_post_segments
            )

            aligned = True

            if method_lower == "get" and is_action_path:
                aligned = False

            if method_lower in {"put", "patch", "delete"} and is_action_path:
                aligned = False

            if method_lower == "post":
                # POST is acceptable for creation and action triggers,
                # so only mark misalignment as false in clearly odd cases later if needed.
                aligned = True

            if aligned:
                method_alignment_ok += 1

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
    r_method_alignment = safe_ratio(method_alignment_ok, method_alignment_total)

    # Rubric-based scoring (fixed points out of 100)
    documentation_score = (
        8 * (r_summary / 100) +
        7 * (r_description / 100) +
        5 * (r_desc_adequacy / 100) +
        5 * (r_response_desc / 100)
    )

    operational_score = (
        7 * (r_operation_id / 100) +
        8 * (r_tags / 100)
    )

    response_score = (
        10 * (r_2xx / 100) +
        12 * (r_error / 100) +
        8 * (r_request_body / 100)
    )

    rest_score = (
        15 * (r_verb_rule / 100) +
        5 * (r_underscore_rule / 100) +
        10 * (r_method_alignment / 100)
    )

    apri_score = round(
        documentation_score + operational_score + response_score + rest_score,
        2
    )
    # --- Governance penalty adjustment ---

    penalty = 0

    for issue in best_practice_issues:
        rule_id = issue.get("rule_id")

        if rule_id in {"missing_error_response", "missing_request_body", "discouraged_verb_in_path"}:
            penalty += 2.5   # major issue

        else:
            penalty += 1.0   # minor issue

    apri_score = max(round(apri_score - penalty, 2), 0)

    # Severity mapping
    major_rule_ids = {
        "missing_error_response",
        "missing_request_body",
        "discouraged_verb_in_path"
    }

    minor_rule_ids = {
        "missing_summary",
        "short_description",
        "missing_tags",
        "underscore_in_path",
        "missing_description",
        "missing_operation_id",
        "invalid_operation_id",
        "empty_tags",
        "missing_success_response",
        "missing_response_description"
    }

    major_issues = 0
    minor_issues = 0

    for issue in best_practice_issues:
        rule_id = issue.get("rule_id")
        if rule_id in major_rule_ids:
            major_issues += 1
        elif rule_id in minor_rule_ids:
            minor_issues += 1
        else:
            minor_issues += 1

    # Grade depends on score + severity
    if apri_score >= 90 and major_issues == 0 and minor_issues == 0:
        grade = "Excellent"
    elif apri_score >= 80 :
        grade = "Good"
    elif apri_score >= 70:
        grade = "Acceptable"
    elif apri_score >= 50:
        grade = "Weak"
    else:
        grade = "Poor"

    # Publishability depends on governance, not score alone
    publishable = major_issues == 0 and len(structure_issues) == 0

    return {
        "apri_score": apri_score,
        "publishable": publishable,
        "grade": grade,
        "category_scores": {
            "documentation": round(documentation_score, 2),
            "operational_clarity": round(operational_score, 2),
            "response_readiness": round(response_score, 2),
            "rest_governance_quality": round(rest_score, 2)
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
            "underscore_rule": round(r_underscore_rule, 2),
            "method_alignment": round(r_method_alignment, 2)
        }
    }