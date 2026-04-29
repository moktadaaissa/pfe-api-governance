import os
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILES_DIR = os.path.join(BASE_DIR, "generated")
API_URL = "http://127.0.0.1:8000/upload-openapi"


def test_file(filepath):
    filename = os.path.basename(filepath)

    with open(filepath, "rb") as f:
        files = {"file": (filename, f)}
        response = requests.post(API_URL, files=files)

    try:
        data = response.json()
    except Exception:
        data = {"detail": response.text}

    return {
        "filename": filename,
        "http_status": response.status_code,
        "response": data
    }


def main():
    if not os.path.exists(TEST_FILES_DIR):
        print("Generated test files folder not found.")
        return

    files = sorted(
        f for f in os.listdir(TEST_FILES_DIR)
        if f.endswith(".yaml") or f.endswith(".yml") or f.endswith(".json")
    )

    if not files:
        print("No test files found.")
        return

    print(f"Found {len(files)} test files.\n")

    for filename in files:
        filepath = os.path.join(TEST_FILES_DIR, filename)
        result = test_file(filepath)
        response_data = result["response"]

        status = response_data.get("status", "N/A")
        decision = response_data.get("governance_decision", "N/A")
        apri_score = response_data.get("apri_score", "N/A")
        grade = response_data.get("grade", "N/A")
        publishable = response_data.get("publishable", "N/A")

        issue_summary = response_data.get("issue_summary", {})
        structure_errors = issue_summary.get("structure_errors", "N/A")
        best_practice_warnings = issue_summary.get("best_practice_warnings", "N/A")
        total_issues = issue_summary.get("total_issues", "N/A")

        simulation = response_data.get("simulation", {})
        sim_score = simulation.get("simulated_score", "N/A")
        sim_improvement = simulation.get("score_improvement", "N/A")
        sim_applied_changes = len(simulation.get("applied_changes", []))
        sim_message = simulation.get("message", "")

        duplicates = response_data.get("duplicates", {})
        duplicate_status = duplicates.get("status", "N/A")
        duplicate_count = duplicates.get("count", 0)

        print(f"File: {filename}")
        print(f"HTTP Status: {result['http_status']}")
        print(f"App Status: {status}")
        print(f"Governance Decision: {decision}")
        print(f"APRI Score: {apri_score}")
        print(f"Grade: {grade}")
        print(f"Publishable: {publishable}")
        print(f"Structure Errors: {structure_errors}")
        print(f"Best Practice Warnings: {best_practice_warnings}")
        print(f"Total Issues: {total_issues}")
        print(f"Simulated Score: {sim_score}")
        print(f"Score Improvement: {sim_improvement}")
        print(f"Applied Simulation Changes: {sim_applied_changes}")
        print(f"Simulation Note: {sim_message}")
        print(f"Duplicate Status: {duplicate_status}")
        print(f"Duplicate Count: {duplicate_count}")
        print("-" * 60)


if __name__ == "__main__":
    main()