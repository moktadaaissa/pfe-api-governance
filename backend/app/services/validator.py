import re as _re


def _extract_path_params(path: str) -> set:
    return set(_re.findall(r'\{(\w+)\}', path))


def _collect_declared_path_params(params_list) -> set:
    if not isinstance(params_list, list):
        return set()
    return {
        p["name"]
        for p in params_list
        if isinstance(p, dict) and p.get("in") == "path" and p.get("name")
    }


def _check_wso2_compatibility(data: dict) -> list:
    """Check hard rules that cause WSO2 AM 4.x import rejection (error code 900754)."""
    issues = []

    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    valid_path_level_fields = {"parameters", "summary", "description", "servers"}

    if not isinstance(data, dict):
        return issues

    paths = data.get("paths", {})
    if not isinstance(paths, dict):
        paths = {}

    components = data.get("components", {})
    components_schemas = (
        components.get("schemas", {}) if isinstance(components, dict) else {}
    )
    if not isinstance(components_schemas, dict):
        components_schemas = {}

    # Rules 1 & 4: every declared in:path parameter must have required: true
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        path_level_params = methods.get("parameters", [])
        if not isinstance(path_level_params, list):
            path_level_params = []

        for p in path_level_params:
            if isinstance(p, dict) and p.get("in") == "path" and p.get("name"):
                if p.get("required") is not True:
                    issues.append({
                        "type": "structure",
                        "severity": "error",
                        "message": (
                            f"Path parameter '{p['name']}' in '{path}' (path-level parameters) "
                            f"must have 'required: true' (WSO2 compatibility)"
                        )
                    })

        for method, details in methods.items():
            if method in valid_path_level_fields or method.lower() not in valid_methods:
                continue
            if not isinstance(details, dict):
                continue
            op_params = details.get("parameters", [])
            if not isinstance(op_params, list):
                op_params = []
            for p in op_params:
                if isinstance(p, dict) and p.get("in") == "path" and p.get("name"):
                    if p.get("required") is not True:
                        issues.append({
                            "type": "structure",
                            "severity": "error",
                            "message": (
                                f"Path parameter '{p['name']}' in {method.upper()} '{path}' "
                                f"must have 'required: true' (WSO2 compatibility)"
                            )
                        })

    # Rules 2 & 3: walk the full document for array-without-items and unresolved $refs
    seen_refs: set = set()

    def _walk(obj, path=""):
        if isinstance(obj, dict):
            ref = obj.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                schema_name = ref[len("#/components/schemas/"):]
                if schema_name not in components_schemas and ref not in seen_refs:
                    seen_refs.add(ref)
                    issues.append({
                        "type": "structure",
                        "severity": "error",
                        "message": (
                            f"$ref '{ref}' does not resolve to an existing schema in "
                            f"components.schemas (WSO2 compatibility)"
                        )
                    })

            if obj.get("type") == "array" and "items" not in obj:
                loc = f" at '{path}'" if path else ""
                issues.append({
                    "type": "structure",
                    "severity": "error",
                    "message": (
                        f"Schema{loc} has 'type: array' but is missing the 'items' field "
                        f"(WSO2 compatibility)"
                    )
                })

            for k, v in obj.items():
                _walk(v, f"{path}.{k}" if path else k)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(data)

    return issues


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
            elif not str(data["info"]["version"]).strip():
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

                # Check that every {param} in the path URL is declared in parameters
                url_params = _extract_path_params(path)
                if url_params:
                    path_level_declared = _collect_declared_path_params(methods.get("parameters"))

                    for method, details in methods.items():
                        if method in valid_path_level_fields or method.lower() not in valid_methods:
                            continue
                        if not isinstance(details, dict):
                            continue

                        op_declared = _collect_declared_path_params(details.get("parameters"))
                        all_declared = path_level_declared | op_declared

                        for param in url_params:
                            if param not in all_declared:
                                issues.append({
                                    "type": "structure",
                                    "severity": "error",
                                    "message": (
                                        f"Path parameter '{{{param}}}' in '{path}' is used in the URL "
                                        f"but not declared in parameters for {method.upper()} {path}. "
                                        f"Add it under 'parameters' with 'in: path'."
                                    )
                                })

    issues += _check_wso2_compatibility(data)
    return issues