def validate_best_practices(data: dict):
    issues = []

    paths = data.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():

            # Skip anything invalid structurally
            if not isinstance(details, dict):
                continue

            # Rule 1: summary
            if "summary" not in details:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": f"{method.upper()} {path} is missing 'summary'"
                })

            # Rule 2: description
            if "description" not in details:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": f"{method.upper()} {path} is missing 'description'"
                })

            # Rule 3: response descriptions
            responses = details.get("responses", {})
            has_error_response = False

            if isinstance(responses, dict):
                for status_code, response_details in responses.items():
                    if str(status_code).startswith("4") or str(status_code).startswith("5"):
                        has_error_response = True

                    if isinstance(response_details, dict):
                        if "description" not in response_details:
                            issues.append({
                                "type": "best_practice",
                                "severity": "warning",
                                "message": f"Response {status_code} in {method.upper()} {path} is missing 'description'"
                            })

            # Rule 4: operationId
            if "operationId" not in details:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": f"{method.upper()} {path} is missing 'operationId'"
                })

            # Rule 5: tags
            if "tags" not in details:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": f"{method.upper()} {path} is missing 'tags'"
                })

            # Rule 6: at least one 4xx or 5xx response
            if not has_error_response:
                issues.append({
                    "type": "best_practice",
                    "severity": "warning",
                    "message": f"{method.upper()} {path} should define at least one 4xx or 5xx response"
                })

    return issues