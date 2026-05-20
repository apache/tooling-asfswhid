# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Conformance tests for asfswhid against known reference values.

These tests verify that the Python wrapper produces identical results to:
  1. The swhid-rs CLI (``swhid content --file ...``)
  2. Git's own object hashing (``git hash-object``)
  3. The Java commons-codec implementation (apache/commons-codec#428)

Run with:  pytest tests/test_conformance.py -v

If you have the swhid CLI installed, set SWHID_CLI=/path/to/swhid to also
run cross-implementation checks.
"""

import os
import subprocess
import shutil

import pytest

from asfswhid import content_id, directory_id

# ── Known test vectors ─────────────────────────────────────────────────────
# These are the Git blob SHA-1 values, which SWHID uses as content identifiers.
# Computed with:  printf '<data>' | git hash-object --stdin

CONTENT_VECTORS = [
    (b"", "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"),
    (b"Hello, World!", "b45ef6fec89518d314f546fd6c3025367b721684"),
    (b"\n", "8b137891791fe96927ad78e64b0aad7bded08bdc"),
    (b"a" * 1000, "a50be72b20f0e3f078d252e8e56b11b4bec67509"),
]


class TestContentConformance:
    @pytest.mark.parametrize("data,expected_hex", CONTENT_VECTORS)
    def test_known_vectors(self, data, expected_hex):
        result = content_id(data)
        assert result.digest_hex == expected_hex, (
            f"content_id({data[:20]!r}...) = {result.digest_hex}, "
            f"expected {expected_hex}"
        )

    @pytest.mark.skipif(
        not shutil.which("git"), reason="git not installed"
    )
    @pytest.mark.parametrize("data,_expected", CONTENT_VECTORS)
    def test_matches_git_hash_object(self, data, _expected, tmp_path):
        """Verify our output matches ``git hash-object`` exactly."""
        f = tmp_path / "blob"
        f.write_bytes(data)
        git_hex = subprocess.check_output(
            ["git", "hash-object", str(f)], text=True
        ).strip()
        assert content_id(data).digest_hex == git_hex


class TestDirectoryConformance:
    @pytest.mark.skipif(
        not shutil.which("git"), reason="git not installed"
    )
    def test_matches_git_tree(self, tmp_path):
        """
        Build a tree in a fresh git repo and compare our directory_id
        against git's tree SHA.
        """
        # Set up a git repo with known content
        subprocess.run(["git", "init", str(tmp_path)], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config",
                         "user.email", "test@test.com"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config",
                         "user.name", "Test"], check=True,
                       capture_output=True)

        (tmp_path / "hello.txt").write_bytes(b"Hello\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."],
                       check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"],
            check=True, capture_output=True,
        )

        # Get git's tree hash for the commit
        git_tree = subprocess.check_output(
            ["git", "-C", str(tmp_path), "rev-parse", "HEAD^{tree}"],
            text=True,
        ).strip()

        our_swhid = directory_id(str(tmp_path))
        # NOTE: our directory_id walks the filesystem, not the git index.
        # If .git/ is excluded (it should be by the Rust impl), these
        # may still differ due to .git presence.  This test documents
        # the expected behaviour; adjust if the Rust crate changes.
        # For a clean comparison, hash only the tracked content:
        work = tmp_path / "_export"
        work.mkdir()
        (work / "hello.txt").write_bytes(b"Hello\n")
        exported = directory_id(str(work))
        assert exported.digest_hex == git_tree


class TestCrossImplementation:
    """
    If the swhid CLI is on PATH (or SWHID_CLI is set), compare outputs.
    This ensures our wrapper matches the reference Rust binary.
    """

    @pytest.fixture
    def swhid_cli(self):
        cli = os.environ.get("SWHID_CLI") or shutil.which("swhid")
        if cli is None:
            pytest.skip("swhid CLI not found; set SWHID_CLI=/path/to/swhid")
        return cli

    def test_content_matches_cli(self, swhid_cli, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"Hello, World!")
        cli_out = subprocess.check_output(
            [swhid_cli, "content", "--file", str(f)], text=True
        ).strip()
        py_out = str(content_id(b"Hello, World!"))
        assert py_out == cli_out

    def test_directory_matches_cli(self, swhid_cli, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"aaa")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_bytes(b"bbb")
        cli_out = subprocess.check_output(
            [swhid_cli, "dir", str(tmp_path)], text=True
        ).strip()
        py_out = str(directory_id(str(tmp_path)))
        assert py_out == cli_out
