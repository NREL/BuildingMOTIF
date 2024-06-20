def pytest_addoption(parser):
    parser.addoption(
        "--skip-library-tests",
        action="store_true",
        help="Skip pytest_generate_tests hook for library validity tests",
    )
