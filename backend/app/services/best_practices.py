def validate_best_practices(data: dict):
    issues = []

    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    valid_path_level_fields = {"parameters", "summary", "description", "servers"}
    discouraged_verbs = {"get", "create", "update", "delete", "set", "add", "remove"}

    # Action-style POST endpoints (no requestBody required)
    action_post_segments = {
        "activate", "deactivate", "cancel", "approve", "reject",
        "suspend", "unsuspend", "lock", "unlock",
        "reset-password", "resend", "verify", "block", "close"
    }

    def add_issue(rule_id, message):
        issues.append({
            "type": "best_practice",
            "severity": "warning",
            "rule_id": rule_id,
            "message": message
        })

    paths = data.get("paths", {})

    if not isinstance(paths, dict):
        return issues

    for path, methods in paths.items():
        if not isinstance(path, str):
            continue

        # =========================
        # PATH NAMING RULES
        # =========================
        path_parts = [
            part for part in path.strip("/").split("/")
            if part and not part.startswith("{")
        ]

        last_segment = path.strip("/").split("/")[-1].lower() \
                       if path.strip("/") else ""
        last_segment_is_action = last_segment in action_post_segments

        has_discouraged_verb = False
        for part in path_parts:
            clean_part = part.lower()

            # Skip last segment if it is a known action endpoint
            if clean_part == last_segment and last_segment_is_action:
                continue

            for verb in discouraged_verbs:
                # Only flag camelCase verb prefixes (e.g. getUsers, createAccount)
                # not resource names that happen to start with a verb (e.g. /sets, /blocks)
                if clean_part == verb:
                    has_discouraged_verb = True
                    break
                if (clean_part.startswith(verb) and
                        len(clean_part) > len(verb) and
                        clean_part[len(verb)].isupper()):
                    has_discouraged_verb = True
                    break

            if has_discouraged_verb:
                add_issue(
                    "discouraged_verb_in_path",
                    f"Path '{path}' should avoid verbs like '{part}' and prefer resource nouns"
                )
                has_discouraged_verb = False

            if "_" in clean_part:
                add_issue(
                    "underscore_in_path",
                    f"Path '{path}' should prefer hyphens '-' over underscores '_'"
                )

        if not isinstance(methods, dict):
            continue

        for method, details in methods.items():

            # Ignore path-level OpenAPI fields
            if method in valid_path_level_fields:
                continue

            # Ignore invalid methods
            if method.lower() not in valid_methods:
                continue

            if not isinstance(details, dict):
                continue

            method_lower = method.lower()

            # =========================
            # SUMMARY
            # =========================
            if not isinstance(details.get("summary"), str) or not details.get("summary", "").strip():
                add_issue(
                    "missing_summary",
                    f"{method.upper()} {path} is missing a non-empty 'summary'"
                )

            # =========================
            # DESCRIPTION
            # =========================
            if not isinstance(details.get("description"), str) or not details.get("description", "").strip():
                add_issue(
                    "missing_description",
                    f"{method.upper()} {path} is missing a non-empty 'description'"
                )
            else:
                if len(details["description"].strip()) < 10:
                    add_issue(
                        "short_description",
                        f"{method.upper()} {path} has a very short 'description'"
                    )

            # =========================
            # OPERATION ID
            # =========================
            if "operationId" not in details:
                add_issue(
                    "missing_operation_id",
                    f"{method.upper()} {path} is missing 'operationId'"
                )
            elif not isinstance(details["operationId"], str) or not details["operationId"].strip():
                add_issue(
                    "invalid_operation_id",
                    f"{method.upper()} {path} has an invalid or empty 'operationId'"
                )

            # =========================
            # TAGS
            # =========================
            if "tags" not in details:
                add_issue(
                    "missing_tags",
                    f"{method.upper()} {path} is missing 'tags'"
                )
            elif not isinstance(details["tags"], list) or len(details["tags"]) == 0:
                add_issue(
                    "empty_tags",
                    f"{method.upper()} {path} should define at least one tag"
                )

            # =========================
            # REQUEST BODY (IMPROVED)
            # =========================
            if method_lower in {"put", "patch"}:
                if "requestBody" not in details:
                    add_issue(
                        "missing_request_body",
                        f"{method.upper()} {path} should define a 'requestBody'"
                    )

            elif method_lower == "post":
                path_segments = [segment for segment in path.strip("/").split("/") if segment]
                last_segment = path_segments[-1].lower() if path_segments else ""

                is_action_post = (
                    not last_segment.startswith("{")
                    and last_segment in action_post_segments
                )

                if not is_action_post and "requestBody" not in details:
                    add_issue(
                        "missing_request_body",
                        f"{method.upper()} {path} should define a 'requestBody'"
                    )

            # =========================
            # RESPONSES
            # =========================
            responses = details.get("responses", {})
            has_success_response = False
            has_error_response = False

            if isinstance(responses, dict):
                for status_code, response_details in responses.items():
                    code = str(status_code)

                    if code.startswith("2"):
                        has_success_response = True

                    if code.startswith("4") or code.startswith("5") or code == "default":
                        has_error_response = True

                    if isinstance(response_details, dict):
                        if not isinstance(response_details.get("description"), str) or not response_details.get("description", "").strip():
                            add_issue(
                                "missing_response_description",
                                f"Response {status_code} in {method.upper()} {path} is missing a non-empty 'description'"
                            )

            if not has_success_response:
                add_issue(
                    "missing_success_response",
                    f"{method.upper()} {path} should define at least one 2xx success response"
                )

            if not has_error_response:
                add_issue(
                    "missing_error_response",
                    f"{method.upper()} {path} should define at least one 4xx/5xx or default error response"
                )

    return issues