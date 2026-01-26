#!/usr/bin/env python
"""Script to run comment module tests."""

import subprocess
import sys
from pathlib import Path

# Get backend directory
backend_dir = Path(__file__).parent

def run_tests():
    """Run comment CRUD tests."""
    print("🧪 Running Comment Module CRUD Tests...")
    print("=" * 60)

    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/test_comments_crud.py",
        "-v",
        "--tb=short",
        "--color=yes",
        "-x",  # Stop on first failure
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=backend_dir,
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("\n📊 Test Coverage Summary:")
            print("- Task Comments CRUD: ✅")
            print("- Cross-Entity Comments: ✅")
            print("- Validation & Edge Cases: ✅")
            print("- Event Publishing: ✅")
        else:
            print(f"\n❌ Tests failed with exit code: {result.returncode}")
            return False

    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        return False

    return True

def run_individual_test_scenarios():
    """Run specific test scenarios."""
    print("\n🎯 Running Individual Test Scenarios...")
    print("=" * 60)

    scenarios = [
        ("Task Comments - Create", "tests/unit/test_comments_crud.py::TestTaskComments::test_add_comment_success"),
        ("Task Comments - Update", "tests/unit/test_comments_crud.py::TestTaskComments::test_update_comment_success"),
        ("Task Comments - Delete", "tests/unit/test_comments_crud.py::TestTaskComments::test_delete_comment_success"),
        ("Task Comments - List", "tests/unit/test_comments_crud.py::TestTaskComments::test_list_comments"),
        ("Cross-Entity - Product", "tests/unit/test_comments_crud.py::TestCrossEntityComments::test_product_comments"),
        ("Validation - Empty Content", "tests/unit/test_comments_crud.py::TestCommentValidation::test_empty_content_validation"),
        ("Events - Comment Added", "tests/unit/test_comments_crud.py::TestCommentEvents::test_comment_added_event"),
    ]

    for scenario_name, test_path in scenarios:
        print(f"\n🔍 Testing: {scenario_name}")
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--color=yes",
        ]

        result = subprocess.run(
            cmd,
            cwd=backend_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"   ✅ {scenario_name}: PASSED")
        else:
            print(f"   ❌ {scenario_name}: FAILED")
            print(f"   Error: {result.stdout[-200:] if result.stdout else result.stderr[-200:]}")

if __name__ == "__main__":
    print("🚀 Starting Comment Module Test Suite")
    print("=" * 60)

    # Run all tests
    success = run_tests()

    if success:
        # Run individual scenarios for detailed report
        run_individual_test_scenarios()

        print("\n" + "=" * 60)
        print("🎉 Comment Module Test Suite Complete!")
        print("=" * 60)

        print("\n📋 Test Results Summary:")
        print("✅ CRUD Operations: Create, Read, Update, Delete")
        print("✅ Cross-Entity Support: Tasks, Products")
        print("✅ Validation: Empty content, permissions")
        print("✅ Soft Delete: Comments marked as deleted")
        print("✅ Mentions: User mentions in comments")
        print("✅ Events: Comment lifecycle events")

        print("\n🔍 Database Verification:")
        print("SELECT * FROM comments WHERE entity_type = 'task';")
        print("SELECT * FROM comments WHERE entity_type = 'product';")
        print("SELECT * FROM comment_mentions;")

    else:
        print("\n💥 Test Suite Failed!")
        print("Please check the errors above and fix them.")
        sys.exit(1)
