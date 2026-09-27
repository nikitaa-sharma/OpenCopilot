"""
Unit tests for repository file filter and classification utility.
"""

from app.services.repository_file_filter import (
    classify_file,
    detect_language,
    is_relevant_for_ingestion,
    should_ignore_path,
)


def test_classify_source_files():
    assert classify_file("src/main.py") == "source"
    assert classify_file("components/Button.tsx") == "source"
    assert classify_file("lib/utils.ts") == "source"
    assert classify_file("index.js") == "source"
    assert classify_file("App.jsx") == "source"
    assert classify_file("pkg/server.go") == "source"
    assert classify_file("src/main.rs") == "source"
    assert classify_file("src/Main.java") == "source"
    assert classify_file("app/Main.kt") == "source"
    assert classify_file("native/calc.cpp") == "source"
    assert classify_file("native/calc.h") == "source"
    assert classify_file("lib/script.rb") == "source"
    assert classify_file("app/index.php") == "source"
    assert classify_file("lib/main.dart") == "source"


def test_classify_test_files():
    assert classify_file("tests/test_routing.py") == "test"
    assert classify_file("test_models.py") == "test"
    assert classify_file("src/auth_test.py") == "test"
    assert classify_file("components/Button.test.tsx") == "test"
    assert classify_file("lib/utils.spec.ts") == "test"
    assert classify_file("__tests__/App.test.js") == "test"


def test_classify_documentation_files():
    assert classify_file("README.md") == "documentation"
    assert classify_file("docs/index.mdx") == "documentation"
    assert classify_file("docs/guide.rst") == "documentation"
    assert classify_file("LICENSE.txt") == "documentation"


def test_classify_configuration_files():
    assert classify_file("pyproject.toml") == "configuration"
    assert classify_file("package.json") == "configuration"
    assert classify_file("docker-compose.yml") == "configuration"
    assert classify_file(".github/workflows/ci.yaml") == "configuration"
    assert classify_file("styles/main.css") == "configuration"
    assert classify_file("index.html") == "configuration"
    assert classify_file("Dockerfile") == "configuration"


def test_classify_ignored_directories():
    assert classify_file(".git/config") == "generated_or_ignored"
    assert classify_file("node_modules/react/index.js") == "generated_or_ignored"
    assert classify_file("__pycache__/app.cpython-310.pyc") == "generated_or_ignored"
    assert classify_file(".venv/lib/site-packages/fastapi/main.py") == "generated_or_ignored"
    assert classify_file("dist/bundle.js") == "generated_or_ignored"
    assert classify_file(".next/server/pages/index.js") == "generated_or_ignored"
    assert classify_file("build/main.o") == "generated_or_ignored"


def test_classify_lock_files():
    assert classify_file("package-lock.json") == "generated_or_ignored"
    assert classify_file("poetry.lock") == "generated_or_ignored"
    assert classify_file("yarn.lock") == "generated_or_ignored"
    assert classify_file("pnpm-lock.yaml") == "generated_or_ignored"


def test_classify_binary_and_compiled_files():
    assert classify_file("assets/logo.png") == "binary_or_unsupported"
    assert classify_file("public/favicon.ico") == "binary_or_unsupported"
    assert classify_file("video.mp4") == "binary_or_unsupported"
    assert classify_file("archive.zip") == "binary_or_unsupported"
    assert classify_file("assets/bundle.min.js") == "binary_or_unsupported"
    assert classify_file("program.exe") == "binary_or_unsupported"
    assert classify_file("lib.so") == "binary_or_unsupported"
    assert classify_file("MyClass.class") == "binary_or_unsupported"


def test_detect_language():
    assert detect_language("app/main.py") == "Python"
    assert detect_language("src/index.ts") == "TypeScript"
    assert detect_language("src/App.tsx") == "TypeScript React"
    assert detect_language("src/index.js") == "JavaScript"
    assert detect_language("src/Component.jsx") == "JavaScript React"
    assert detect_language("main.go") == "Go"
    assert detect_language("src/lib.rs") == "Rust"
    assert detect_language("Main.java") == "Java"
    assert detect_language("Dockerfile") == "Dockerfile"
    assert detect_language("styles.css") == "CSS"
    assert detect_language("unknown.xyz") is None


def test_should_ignore_path():
    assert should_ignore_path(".git/refs/heads/main") is True
    assert should_ignore_path("node_modules/axios/index.js") is True
    assert should_ignore_path("__pycache__/main.pyc") is True
    assert should_ignore_path("assets/avatar.jpg") is True
    assert should_ignore_path("src/main.py") is False
    assert should_ignore_path("docs/README.md") is False


def test_is_relevant_for_ingestion():
    assert is_relevant_for_ingestion("src/main.py") is True
    assert is_relevant_for_ingestion("tests/test_api.py") is True
    assert is_relevant_for_ingestion("README.md") is True
    assert is_relevant_for_ingestion("pyproject.toml") is True
    assert is_relevant_for_ingestion("node_modules/react/index.js") is False
    assert is_relevant_for_ingestion("logo.png") is False
    assert is_relevant_for_ingestion("dist/bundle.js") is False
