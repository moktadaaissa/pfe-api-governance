import os
import yaml

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")


def save_yaml(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, sort_keys=False)
    print(f"Generated: {filename}")


def generate_tests():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Safe-only: everything missing
    save_yaml("sim_safe_only_all_missing.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Simulation Safe Only", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {},
                        "400": {}
                    }
                }
            }
        }
    })

    # 2. Partial safe fixes
    save_yaml("sim_safe_only_partial_missing.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Partial Safe", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {
                        "200": {"description": "OK"},
                        "400": {}
                    }
                }
            }
        }
    })

    # 3. Response description only
    save_yaml("sim_response_description_only.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Response Only", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "description": "Returns all users.",
                    "operationId": "listUsers",
                    "tags": ["Users"],
                    "responses": {
                        "200": {},
                        "400": {}
                    }
                }
            }
        }
    })

    # 4. Unsafe: verb in path
    save_yaml("sim_unsafe_only_verb_path.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Unsafe Verb Path", "version": "1.0.0"},
        "paths": {
            "/users/create": {
                "post": {
                    "summary": "Create user",
                    "description": "Creates user",
                    "operationId": "createUser",
                    "tags": ["Users"],
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Error"}
                    }
                }
            }
        }
    })

    # 5. Missing request body
    save_yaml("sim_unsafe_missing_request_body.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Missing Body", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "summary": "Create user",
                    "description": "Creates user",
                    "operationId": "createUser",
                    "tags": ["Users"],
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Error"}
                    }
                }
            }
        }
    })

    # 6. Mixed safe + unsafe
    save_yaml("sim_mixed_safe_and_unsafe.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Mixed Case", "version": "1.0.0"},
        "paths": {
            "/users/create": {
                "post": {
                    "responses": {
                        "201": {}
                    }
                }
            }
        }
    })

    # 7. GET action path
    save_yaml("sim_mixed_get_action_path.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "GET Action Path", "version": "1.0.0"},
        "paths": {
            "/users/activate": {
                "get": {
                    "responses": {
                        "200": {},
                        "400": {}
                    }
                }
            }
        }
    })

    # 8. No safe fix (good docs, bad design)
    save_yaml("sim_no_safe_fix_bad_design.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "No Safe Fix", "version": "1.0.0"},
        "paths": {
            "/orders/delete": {
                "delete": {
                    "summary": "Delete order",
                    "description": "Deletes order",
                    "operationId": "deleteOrder",
                    "tags": ["Orders"],
                    "responses": {
                        "200": {"description": "Deleted"},
                        "404": {"description": "Not found"}
                    }
                }
            }
        }
    })

    # 9. Perfect case
    save_yaml("sim_perfect.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Perfect API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "description": "Returns users",
                    "operationId": "listUsers",
                    "tags": ["Users"],
                    "responses": {
                        "200": {"description": "Success"},
                        "400": {"description": "Error"}
                    }
                }
            }
        }
    })

    # 10. Short description edge
    save_yaml("sim_short_description.yaml", {
        "openapi": "3.0.3",
        "info": {"title": "Short Description", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "Users",
                    "description": "Fetch.",
                    "operationId": "listUsers",
                    "tags": ["Users"],
                    "responses": {
                        "200": {"description": "OK"},
                        "400": {"description": "Error"}
                    }
                }
            }
        }
    })


if __name__ == "__main__":
    generate_tests()