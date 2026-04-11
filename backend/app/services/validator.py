def validate_openapi_structure(data: dict):
    issues = []

    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    valid_path_level_fields = {"parameters", "summary", "description", "servers"}

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
    else:
        if not isinstance(data["openapi"], str) or not data["openapi"].strip():
            issues.append({
                "type": "structure",
                "severity": "error",
                "message": "'openapi' must be a non-empty string"
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
            elif not isinstance(data["info"]["title"], str) or not data["info"]["title"].strip():
                issues.append({
                    "type": "structure",
                    "severity": "error",
                    "message": "'info.title' must be a non-empty string"
                })

            if "version" not in data["info"]:
                issues.append({
                    "type": "structure",
                    "severity": "error",
                    "message": "Missing 'info.version' field"
                })
            elif not isinstance(data["info"]["version"], str) or not data["info"]["version"].strip():
                issues.append({
                    "type": "structure",
                    "severity": "error",
                    "message": "'info.version' must be a non-empty string"
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

                # Path must start with "/"
                if not isinstance(path, str) or not path.startswith("/"):
                    issues.append({
                        "type": "structure",
                        "severity": "error",
                        "message": f"Invalid path '{path}'. Paths must start with '/'"
                    })

                if not isinstance(methods, dict) or len(methods) == 0:
                    issues.append({
                        "type": "structure",
                        "severity": "error",
                        "message": f"Path '{path}' has no methods defined"
                    })
                    continue

                for method, details in methods.items():

                    # Skip valid path-level OpenAPI fields
                    if method in valid_path_level_fields:
                        continue

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
                    else:
                        responses = details["responses"]

                        if not isinstance(responses, dict):
                            issues.append({
                                "type": "structure",
                                "severity": "error",
                                "message": f"'responses' in {method.upper()} {path} must be an object"
                            })

                        elif len(responses) == 0:
                            issues.append({
                                "type": "structure",
                                "severity": "error",
                                "message": f"'responses' in {method.upper()} {path} must not be empty"
                            })
                        else:
                            for status_code, response_details in responses.items():
                                if not isinstance(response_details, dict):
                                    issues.append({
                                        "type": "structure",
                                        "severity": "error",
                                        "message": f"Response '{status_code}' in {method.upper()} {path} must be an object"
                                    })

    return issues