"""
run_test_scenario.py — a small helper for the Week 2 extension.

Runs the existing pipeline against any test scenario folder under
test_scenarios/, without touching the real input/ or output/ folders
used for the main assignment.

This works with ZERO changes to pipeline.py, extract.py, or validate.py
because run_pipeline() already accepts input_folder/output_folder as
parameters — that flexibility, built in during Week 2, is exactly what
makes this extension possible without rewriting anything.

Usage:
    python run_test_scenario.py T01_new_branch
"""

import sys
import os
from pipeline import run_pipeline

TEST_SCENARIOS_FOLDER = "test_scenarios"


def run_scenario(scenario_name):
    scenario_folder = os.path.join(TEST_SCENARIOS_FOLDER, scenario_name)
    input_folder = os.path.join(scenario_folder, "input")
    output_folder = os.path.join(scenario_folder, "output")

    if not os.path.isdir(input_folder):
        print(f"No input folder found at '{input_folder}'.")
        print(f"Expected structure: {scenario_folder}/input/ and {scenario_folder}/output/")
        return

    print(f"=== Running scenario: {scenario_name} ===")
    run_pipeline(input_folder=input_folder, output_folder=output_folder)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_test_scenario.py <scenario_folder_name>")
        print("Example: python run_test_scenario.py T01_new_branch")
        sys.exit(1)

    run_scenario(sys.argv[1])
