import os
import copy
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "generated")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_yaml(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)
    print(f"Created: {filename}")


def save_raw(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created: {filename}")


def make_valid_base():
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Users API",
            "version": "1.0.0"
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get users",
                    "description": "Retrieve all users from the system",
                    "operationId": "getUsers",
                    "tags": ["Users"],
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        },
                        "400": {
                            "description": "Bad request"
                        }
                    }
                }
            }
        }
    }


# =========================
# VALID FILES
# =========================

save_yaml("valid_full_openapi.yaml", make_valid_base())

case = make_valid_base()
case["paths"]["/trace-test"] = {
    "trace": {
        "summary": "Trace request",
        "description": "Trace request details for debugging",
        "operationId": "traceRequest",
        "tags": ["Trace"],
        "responses": {
            "200": {"description": "Trace successful"},
            "500": {"description": "Server error"}
        }
    }
}
save_yaml("valid_trace_method.yaml", case)

case = make_valid_base()
case["paths"]["/users"] = {
    "summary": "Users path",
    "description": "Operations related to users",
    "servers": [{"url": "http://localhost:8000"}],
    "parameters": [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "schema": {"type": "integer"}
        }
    ],
    "get": {
        "summary": "Get users",
        "description": "Retrieve all users from the system",
        "operationId": "getUsers",
        "tags": ["Users"],
        "responses": {
            "200": {"description": "Successful response"},
            "400": {"description": "Bad request"}
        }
    }
}
save_yaml("valid_path_level_fields.yaml", case)

case = make_valid_base()
case["paths"]["/user-profiles"] = {
    "get": {
        "summary": "Get profiles",
        "description": "Retrieve all user profiles from the system",
        "operationId": "getUserProfiles",
        "tags": ["Profiles"],
        "responses": {
            "200": {"description": "Successful response"},
            "404": {"description": "Profiles not found"}
        }
    }
}
save_yaml("valid_hyphenated_path.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["post"] = {
    "summary": "Create user",
    "description": "Create a new user in the system",
    "operationId": "createUser",
    "tags": ["Users"],
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object"
                }
            }
        }
    },
    "responses": {
        "201": {"description": "Created"},
        "400": {"description": "Bad request"}
    }
}
save_yaml("valid_post_with_requestbody.yaml", case)

# =========================
# STRUCTURE TESTS
# =========================

save_raw("broken_root_not_object.yaml", "- just\n- a\n- list\n")

case = make_valid_base()
del case["openapi"]
save_yaml("broken_missing_openapi.yaml", case)

case = make_valid_base()
case["openapi"] = 3
save_yaml("broken_openapi_wrong_type.yaml", case)

case = make_valid_base()
case["openapi"] = ""
save_yaml("broken_openapi_empty.yaml", case)

case = make_valid_base()
del case["info"]
save_yaml("broken_missing_info.yaml", case)

case = make_valid_base()
case["info"] = "not-an-object"
save_yaml("broken_info_wrong_type.yaml", case)

case = make_valid_base()
del case["info"]["title"]
save_yaml("broken_missing_info_title.yaml", case)

case = make_valid_base()
case["info"]["title"] = ""
save_yaml("broken_empty_info_title.yaml", case)

case = make_valid_base()
case["info"]["title"] = 123
save_yaml("broken_info_title_wrong_type.yaml", case)

case = make_valid_base()
del case["info"]["version"]
save_yaml("broken_missing_info_version.yaml", case)

case = make_valid_base()
case["info"]["version"] = ""
save_yaml("broken_empty_info_version.yaml", case)

case = make_valid_base()
case["info"]["version"] = 1
save_yaml("broken_info_version_wrong_type.yaml", case)

case = make_valid_base()
del case["paths"]
save_yaml("broken_missing_paths.yaml", case)

case = make_valid_base()
case["paths"] = []
save_yaml("broken_paths_wrong_type.yaml", case)

case = make_valid_base()
case["paths"] = {}
save_yaml("broken_empty_paths.yaml", case)

case = make_valid_base()
users_get = copy.deepcopy(case["paths"]["/users"])
case["paths"] = {
    "users": users_get
}
save_yaml("broken_invalid_path_no_slash.yaml", case)

case = make_valid_base()
case["paths"]["/users"] = {}
save_yaml("broken_path_no_methods.yaml", case)

case = make_valid_base()
case["paths"]["/users"] = "not-an-object"
save_yaml("broken_path_methods_wrong_type.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["fetch"] = copy.deepcopy(case["paths"]["/users"]["get"])
del case["paths"]["/users"]["get"]
save_yaml("broken_invalid_http_method.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"] = "not-an-object"
save_yaml("broken_operation_wrong_type.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["responses"]
save_yaml("broken_missing_responses.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"] = "not-an-object"
save_yaml("broken_responses_wrong_type.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"] = {}
save_yaml("broken_empty_responses.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"]["200"] = "OK"
save_yaml("broken_response_item_wrong_type.yaml", case)

case = {
    "openapi": "",
    "info": {"title": "", "version": ""},
    "paths": {
        "users": {
            "fetch": {
                "responses": "bad"
            }
        }
    }
}
save_yaml("broken_multiple_structure_errors.yaml", case)

# =========================
# BEST PRACTICES TESTS
# =========================

case = make_valid_base()
del case["paths"]["/users"]["get"]["summary"]
save_yaml("warning_missing_summary.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["summary"] = ""
save_yaml("warning_empty_summary.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["description"]
save_yaml("warning_missing_description.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["description"] = ""
save_yaml("warning_empty_description.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["description"] = "Too short"
save_yaml("warning_short_description.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["operationId"]
save_yaml("warning_missing_operationId.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["operationId"] = ""
save_yaml("warning_empty_operationId.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["tags"]
save_yaml("warning_missing_tags.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["tags"] = []
save_yaml("warning_empty_tags.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["responses"]["200"]["description"]
save_yaml("warning_missing_response_description_200.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"]["200"]["description"] = ""
save_yaml("warning_empty_response_description_200.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["responses"]["400"]["description"]
save_yaml("warning_missing_response_description_400.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"]["400"]["description"] = ""
save_yaml("warning_empty_response_description_400.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"] = {
    "200": {"description": "Successful response"}
}
save_yaml("warning_no_error_response.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"] = {
    "400": {"description": "Bad request"}
}
save_yaml("warning_no_success_response.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["get"]["responses"] = {
    "200": {"description": "Successful response"},
    "default": {"description": "Unexpected error"}
}
save_yaml("valid_default_error_response.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["post"] = {
    "summary": "Create user",
    "description": "Create a new user in the system",
    "operationId": "createUser",
    "tags": ["Users"],
    "responses": {
        "201": {"description": "Created"},
        "400": {"description": "Bad request"}
    }
}
save_yaml("warning_post_without_requestbody.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["put"] = {
    "summary": "Update user",
    "description": "Update an existing user in the system",
    "operationId": "updateUser",
    "tags": ["Users"],
    "responses": {
        "200": {"description": "Updated"},
        "400": {"description": "Bad request"}
    }
}
save_yaml("warning_put_without_requestbody.yaml", case)

case = make_valid_base()
case["paths"]["/users"]["patch"] = {
    "summary": "Patch user",
    "description": "Patch an existing user in the system",
    "operationId": "patchUser",
    "tags": ["Users"],
    "responses": {
        "200": {"description": "Patched"},
        "400": {"description": "Bad request"}
    }
}
save_yaml("warning_patch_without_requestbody.yaml", case)

case = make_valid_base()
case["paths"] = {
    "/create": {
        "post": {
            "summary": "Create user",
            "description": "Create a new user in the system",
            "operationId": "createUser",
            "tags": ["Users"],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            },
            "responses": {
                "201": {"description": "Created"},
                "400": {"description": "Bad request"}
            }
        }
    }
}
save_yaml("warning_path_with_discouraged_verb.yaml", case)

case = make_valid_base()
case["paths"] = {
    "/user_profiles": {
        "get": {
            "summary": "Get profiles",
            "description": "Retrieve all user profiles from the system",
            "operationId": "getUserProfiles",
            "tags": ["Profiles"],
            "responses": {
                "200": {"description": "Successful response"},
                "400": {"description": "Bad request"}
            }
        }
    }
}
save_yaml("warning_path_with_underscore.yaml", case)

case = make_valid_base()
case["paths"] = {
    "/users/{id}/delete": {
        "post": {
            "summary": "Delete user",
            "description": "Delete a user from the system",
            "operationId": "deleteUser",
            "tags": ["Users"],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            },
            "responses": {
                "200": {"description": "Deleted"},
                "400": {"description": "Bad request"}
            }
        }
    }
}
save_yaml("warning_nested_path_with_verb.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["summary"]
del case["paths"]["/users"]["get"]["description"]
del case["paths"]["/users"]["get"]["operationId"]
del case["paths"]["/users"]["get"]["tags"]
case["paths"]["/users"]["get"]["responses"] = {
    "200": {}
}
save_yaml("warning_multiple_best_practices.yaml", case)

# =========================
# MIXED TESTS
# =========================

case = make_valid_base()
del case["paths"]["/users"]["get"]["summary"]
case["paths"]["/users"]["get"]["responses"] = {}
save_yaml("mixed_structure_and_best_practice.yaml", case)

case = make_valid_base()
del case["paths"]["/users"]["get"]["summary"]
del case["paths"]["/users"]["get"]["description"]
del case["paths"]["/users"]["get"]["operationId"]
del case["paths"]["/users"]["get"]["tags"]
case["paths"]["/users"]["get"]["responses"] = {
    "200": {}
}
save_yaml("valid_structure_many_warnings.yaml", case)

print("\\nAll test files generated successfully.")