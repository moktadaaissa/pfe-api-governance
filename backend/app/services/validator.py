def validate_openapi_structure(data: dict):
    issues = []

    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head"}

    # Check root structure
    if not isinstance(data, dict):
        issues.append({
            "type": "structure",
            "severity": "error",
            "message": "Invalid OpenAPI document format"
        })
        return issues

    # Check required top-level fields
    if "openapi" not in data:
        issues.append({
            "type": "structure",
            "severity": "error",
            "message": "Missing 'openapi' field"
        })

    if "info" not in data:
        issues.append({
            "type": "structure",
            "severity": "error",
            "message": "Missing 'info' section"
        })
    else:
        if not isinstance(data["info"], dict):
            issues.append({
                "type": "structure",
                "severity": "error",
                "message": "'info' must be an object"
            })
        else:
            if "title" not in data["info"]:
                issues.append({
                    "type": "structure",
                    "severity": "error",
                    "message": "Missing 'info.title' field"
                })

            if "version" not in data["info"]:
                issues.append({
                    "type": "structure",
                    "severity": "error",
                    "message": "Missing 'info.version' field"
                })

    # Check paths
    if "paths" not in data:
        issues.append({
            "type": "structure",
            "severity": "error",
            "message": "Missing 'paths' section"
        })
    else:
        paths = data["paths"]

        if not isinstance(paths, dict):
            issues.append({
                "type": "structure",
                "severity": "error",
                "message": "'paths' must be an object"
            })
        elif len(paths) == 0:
            issues.append({
                "type": "structure",
                "severity": "error",
                "message": "'paths' must not be empty"
            })
        else:
            for path, methods in paths.items():

                if not isinstance(methods, dict) or len(methods) == 0:
                    issues.append({
                        "type": "structure",
                        "severity": "error",
                        "message": f"Path '{path}' has no methods defined"
                    })
                    continue

                for method, details in methods.items():

                    # Check valid HTTP method
                    if method.lower() not in valid_methods:
                        issues.append({
                            "type": "structure",
                            "severity": "error",
                            "message": f"Invalid HTTP method '{method}' in path '{path}'"
                        })
                        continue

                    # Check operation object
                    if not isinstance(details, dict):
                        issues.append({
                            "type": "structure",
                            "severity": "error",
                            "message": f"Operation '{method}' in '{path}' must be an object"
                        })
                        continue

                    # Check responses
                    if "responses" not in details:
                        issues.append({
                            "type": "structure",
                            "severity": "error",
                            "message": f"{method.upper()} {path} is missing 'responses'"
                        })

    return issues