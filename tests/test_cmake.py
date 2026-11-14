"""End-to-end test of UsesCertifier.cmake on a small C++ project."""
import shutil
import subprocess

import pytest

from uses_certifier.cli import main
from uses_certifier.config import CERTIFICATE as CERT

from conftest import RULES

CMAKE = shutil.which("cmake")
CERTIFIER = shutil.which("uses-certifier")
COMPILER = shutil.which("c++") or shutil.which("g++")
pytestmark = pytest.mark.skipif(
    not (CMAKE and CERTIFIER and COMPILER),
    reason="needs cmake, a C++ compiler and uses-certifier on the PATH")

TOP = """\
cmake_minimum_required(VERSION 3.19)
project(demo CXX)
include({module})
uses_certifier_check()
add_subdirectory(lib)
add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE greet)
"""
LIB = "add_library(greet STATIC greet.cpp)\n"
GREET = """\
int greet(int times)
{
    return times * 2;
}
"""
MAIN = """\
int greet(int times);

int main()
{
    return greet(0);
}
"""


@pytest.fixture
def cpp_project(project, tmp_path_factory):
    """A certified C++ project with a library in a subdirectory, and the
    folder where it is built."""
    module = subprocess.check_output([CERTIFIER, "cmake-module"], text=True)
    root = project({
        ".uses-certifier.yaml": "min_level: gold\n",
        "CMakeLists.txt": TOP.format(module=module.strip()),
        "main.cpp": MAIN, "lib/CMakeLists.txt": LIB,
        "lib/greet.cpp": GREET})
    assert main(["certify", str(root), "--rules", str(RULES),
                 "--certificate", str(root / CERT)]) == 0
    build = tmp_path_factory.mktemp("build")
    subprocess.run([CMAKE, "-S", root, "-B", build], check=True,
                   capture_output=True)
    return root, build


def build(folder):
    """Build the project; (return code, output)."""
    done = subprocess.run([CMAKE, "--build", folder], capture_output=True,
                          text=True)
    return done.returncode, done.stdout + done.stderr


def test_certified_code_builds(cpp_project):
    _, folder = cpp_project
    code, output = build(folder)
    assert code == 0, output
    assert "Certification check OK" in output


def test_changed_code_stops_the_build(cpp_project):
    root, folder = cpp_project
    (root / "lib" / "greet.cpp").write_text(GREET.replace("2", "3"))
    code, output = build(folder)
    assert code != 0
    assert "INVALID      lib/greet.cpp:greet" in output
    assert not list(folder.rglob("*greet.a"))


def test_authorized_code_builds_and_is_reported(cpp_project):
    root, folder = cpp_project
    (root / "lib" / "greet.cpp").write_text(GREET.replace("2", "3"))
    assert main(["authorize", str(root / CERT), "--reason", "hotfix",
                 "--by", "Ann"]) == 0
    code, output = build(folder)
    assert code == 0, output
    assert "AUTHORIZED   invalid lib/greet.cpp:greet: hotfix" in output
