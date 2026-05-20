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
Tests for asfswhid – Python bindings for swhid-rs.

Run with:  pytest tests/
"""

import os
import tempfile
import textwrap

import pytest

from asfswhid import (
    ObjectType,
    Swhid,
    QualifiedSwhid,
    content_id,
    content_id_from_file,
    directory_id,
    verify,
)


# ---------------------------------------------------------------------------
# ObjectType
# ---------------------------------------------------------------------------

class TestObjectType:
    def test_tags(self):
        assert ObjectType.Content.tag() == "cnt"
        assert ObjectType.Directory.tag() == "dir"
        assert ObjectType.Revision.tag() == "rev"
        assert ObjectType.Release.tag() == "rel"
        assert ObjectType.Snapshot.tag() == "snp"


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------

class TestContentId:
    def test_empty_content(self):
        """Empty content should produce a valid cnt SWHID."""
        s = content_id(b"")
        assert str(s).startswith("swh:1:cnt:")
        assert s.object_type == ObjectType.Content
        assert len(s.digest_hex) == 40

    def test_hello_world(self):
        """Known test vector: 'Hello, World!' should be deterministic."""
        s = content_id(b"Hello, World!")
        # This must match `git hash-object` for "Hello, World!"
        # $ printf "Hello, World!" | git hash-object --stdin
        assert s.digest_hex == "b45ef6fec89518d314f546fd6c3025367b721684"
        assert str(s) == "swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684"

    def test_digest_bytes(self):
        s = content_id(b"test")
        raw = s.digest_bytes()
        assert isinstance(raw, bytes)
        assert len(raw) == 20
        assert raw.hex() == s.digest_hex

    def test_from_file(self, tmp_path):
        """content_id_from_file should match content_id on the same data."""
        p = tmp_path / "hello.txt"
        p.write_bytes(b"Hello, World!")
        assert content_id_from_file(str(p)) == content_id(b"Hello, World!")

    def test_from_file_missing(self):
        with pytest.raises(OSError, match="cannot read"):
            content_id_from_file("/nonexistent/path/file.txt")


# ---------------------------------------------------------------------------
# Directory hashing
# ---------------------------------------------------------------------------

class TestDirectoryId:
    def test_empty_dir(self, tmp_path):
        s = directory_id(str(tmp_path))
        assert str(s).startswith("swh:1:dir:")
        assert s.object_type == ObjectType.Directory

    def test_deterministic(self, tmp_path):
        """Same tree content should always produce the same SWHID."""
        (tmp_path / "a.txt").write_bytes(b"aaa")
        (tmp_path / "b.txt").write_bytes(b"bbb")
        s1 = directory_id(str(tmp_path))
        s2 = directory_id(str(tmp_path))
        assert s1 == s2

    def test_exclude_suffixes(self, tmp_path):
        """Excluding files should change the directory SWHID."""
        (tmp_path / "main.py").write_bytes(b"code")
        (tmp_path / "main.pyc").write_bytes(b"compiled")
        with_pyc = directory_id(str(tmp_path))
        without_pyc = directory_id(str(tmp_path), exclude_suffixes=[".pyc"])
        assert with_pyc != without_pyc

    def test_nonexistent_dir(self):
        with pytest.raises(OSError):
            directory_id("/nonexistent/path")


# ---------------------------------------------------------------------------
# Swhid parsing
# ---------------------------------------------------------------------------

class TestSwhidParsing:
    VALID = "swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684"

    def test_roundtrip(self):
        s = Swhid(self.VALID)
        assert str(s) == self.VALID

    def test_object_type(self):
        assert Swhid(self.VALID).object_type == ObjectType.Content

    def test_invalid_scheme(self):
        with pytest.raises(ValueError):
            Swhid("XXX:1:cnt:" + "a" * 40)

    def test_invalid_version(self):
        with pytest.raises(ValueError):
            Swhid("swh:9:cnt:" + "a" * 40)

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            Swhid("swh:1:xxx:" + "a" * 40)

    def test_short_digest(self):
        with pytest.raises(ValueError):
            Swhid("swh:1:cnt:abc")

    def test_hash_and_eq(self):
        s1 = Swhid(self.VALID)
        s2 = Swhid(self.VALID)
        assert s1 == s2
        assert hash(s1) == hash(s2)
        assert s1 != Swhid("swh:1:cnt:" + "0" * 40)

    def test_repr(self):
        s = Swhid(self.VALID)
        assert "Swhid(" in repr(s)
        assert self.VALID in repr(s)


# ---------------------------------------------------------------------------
# QualifiedSwhid
# ---------------------------------------------------------------------------

class TestQualifiedSwhid:
    CORE = "swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684"

    def test_parse_with_origin(self):
        qs = QualifiedSwhid(f"{self.CORE};origin=https://github.com/user/repo")
        assert qs.core == Swhid(self.CORE)

    def test_builder(self):
        qs = QualifiedSwhid(self.CORE)
        qs2 = qs.with_origin("https://github.com/user/repo")
        result = str(qs2)
        assert "origin=" in result

    def test_with_path(self):
        qs = QualifiedSwhid(self.CORE).with_path("/src/main.rs")
        assert "path=" in str(qs)

    def test_with_lines(self):
        qs = QualifiedSwhid(self.CORE).with_lines(10, 20)
        assert "lines=" in str(qs)

    def test_with_bytes(self):
        qs = QualifiedSwhid(self.CORE).with_bytes(100, 200)
        assert "bytes=" in str(qs)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

class TestVerify:
    def test_file_match(self, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_bytes(b"Hello, World!")
        expected = str(content_id(b"Hello, World!"))
        assert verify(str(p), expected) is True

    def test_file_mismatch(self, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_bytes(b"different content")
        wrong = "swh:1:cnt:" + "0" * 40
        assert verify(str(p), wrong) is False

    def test_dir_match(self, tmp_path):
        (tmp_path / "f.txt").write_bytes(b"data")
        expected = str(directory_id(str(tmp_path)))
        assert verify(str(tmp_path), expected) is True

    def test_invalid_swhid(self, tmp_path):
        p = tmp_path / "f.txt"
        p.write_bytes(b"data")
        with pytest.raises(ValueError):
            verify(str(p), "not-a-swhid")


# ---------------------------------------------------------------------------
# Cross-format archive comparison (the ATR use-case)
# ---------------------------------------------------------------------------

class TestCrossFormatComparison:
    """
    Demonstrate the key ATR use-case: two archives of the same content
    should produce the same directory SWHID, regardless of format.
    """

    def test_same_content_same_swhid(self, tmp_path):
        """Two directories with identical files must have the same dir SWHID."""
        for name in ("dir_a", "dir_b"):
            d = tmp_path / name
            d.mkdir()
            (d / "README.md").write_bytes(b"# Hello\n")
            (d / "LICENSE").write_bytes(b"MIT\n")
            sub = d / "src"
            sub.mkdir()
            (sub / "main.py").write_bytes(b"print('hi')\n")

        assert directory_id(str(tmp_path / "dir_a")) == directory_id(
            str(tmp_path / "dir_b")
        )

    def test_different_content_different_swhid(self, tmp_path):
        d1 = tmp_path / "d1"
        d1.mkdir()
        (d1 / "f.txt").write_bytes(b"version 1")

        d2 = tmp_path / "d2"
        d2.mkdir()
        (d2 / "f.txt").write_bytes(b"version 2")

        assert directory_id(str(d1)) != directory_id(str(d2))
