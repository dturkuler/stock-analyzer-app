#!/usr/bin/env python3
"""
Master Test Runner Script for stock-analyzer-app
Location: tests/run_tests.py

Runs all unit & integration test suites under tests/ directory.
Usage:
    python3 tests/run_tests.py
"""

import os
import sys
import unittest
import time

# Ensure project root is in sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)


def run_all_tests():
    print("=" * 70)
    print("🧪 Stock Analyzer Platform — Automated Test Suite Runner")
    print("=" * 70)
    print(f"📂 Tests Directory : {TESTS_DIR}")
    print(f"🏠 Project Root    : {PROJECT_ROOT}")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=TESTS_DIR, pattern="test_*.py")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("📊 TEST SUITE SUMMARY REPORT")
    print("=" * 70)
    print(f"⏱️ Total Execution Time : {elapsed:.2f} seconds")
    print(f"🧪 Total Tests Run      : {result.testsRun}")
    print(f"✅ Passed               : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures             : {len(result.failures)}")
    print(f"💥 Errors               : {len(result.errors)}")
    print("=" * 70)

    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("🔴 FEW TESTS FAILED OR ENCOUNTERED ERRORS.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
