#!/usr/bin/env python3
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
example_usage.py — Demonstrates asfswhid with expected outputs.

Run after building:
    maturin develop
    python example_usage.py

You can also verify every content hash with git:
    echo -n "Hello, World!" | git hash-object --stdin
    # b45ef6fec89518d314f546fd6c3025367b721684
"""

import os
import tempfile

from asfswhid import (
    ObjectType,
    Swhid,
    QualifiedSwhid,
    content_id,
    content_id_from_file,
    directory_id,
    verify,
)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# ── 1. Content hashing ────────────────────────────────────────

section("1. Content hashing (Git blob compatible)")

s = content_id(b"Hello, World!")
print(f"  content_id(b'Hello, World!')")
print(f"  → {s}")
print(f"  Expected: swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
print(f"  Match: {s.digest_hex == 'b45ef6fec89518d314f546fd6c3025367b721684'}")
print()

# Verify: echo -n "Hello, World!" | git hash-object --stdin
# Output: b45ef6fec89518d314f546fd6c3025367b721684

s2 = content_id(b"")
print(f"  content_id(b'')  # empty file")
print(f"  → {s2}")
print(f"  Expected: swh:1:cnt:e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
print(f"  Match: {s2.digest_hex == 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'}")


# ── 2. Inspecting a Swhid object ──────────────────────────────

section("2. Inspecting a Swhid object")

print(f"  s.object_type    → {s.object_type}")
print(f"  s.object_type.tag() → '{s.object_type.tag()}'")
print(f"  s.digest_hex     → '{s.digest_hex}'")
print(f"  s.digest_bytes() → {s.digest_bytes()!r}  (20 bytes)")
print(f"  str(s)           → '{s}'")
print(f"  repr(s)          → {s!r}")


# ── 3. Parsing a SWHID string ─────────────────────────────────

section("3. Parsing a SWHID string")

parsed = Swhid("swh:1:dir:dfb19777ce2789a860ae2121a13cc1bd622d6af5")
print(f"  Swhid('swh:1:dir:dfb19777...')")
print(f"  → object_type: {parsed.object_type}")
print(f"  → digest_hex:  {parsed.digest_hex}")
print()

print("  Invalid strings raise ValueError:")
try:
    Swhid("not-a-swhid")
except ValueError as e:
    print(f"  Swhid('not-a-swhid') → ValueError: {e}")


# ── 4. Hashing a file on disk ─────────────────────────────────

section("4. Hashing a file on disk")

with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
    f.write(b"Hello, World!")
    tmp_file = f.name

s3 = content_id_from_file(tmp_file)
print(f"  Wrote b'Hello, World!' to {tmp_file}")
print(f"  content_id_from_file('{tmp_file}')")
print(f"  → {s3}")
print(f"  Matches content_id(b'Hello, World!'): {s3 == s}")
os.unlink(tmp_file)


# ── 5. Directory hashing ──────────────────────────────────────

section("5. Directory hashing (Merkle tree, format-agnostic)")

with tempfile.TemporaryDirectory() as d:
    # Create the same tree structure as our git test above
    os.makedirs(os.path.join(d, "src"))
    with open(os.path.join(d, "README.md"), "wb") as f:
        f.write(b"# Hello")
    with open(os.path.join(d, "LICENSE"), "wb") as f:
        f.write(b"MIT")
    with open(os.path.join(d, "src", "main.py"), "wb") as f:
        f.write(b"print('hi')")

    ds = directory_id(d)
    print(f"  Tree structure:")
    print(f"    README.md  → b'# Hello'")
    print(f"    LICENSE    → b'MIT'")
    print(f"    src/main.py → b\"print('hi')\"")
    print(f"  directory_id('{d}')")
    print(f"  → {ds}")
    print(f"  Expected: swh:1:dir:dfb19777ce2789a860ae2121a13cc1bd622d6af5")
    print(f"  Match: {ds.digest_hex == 'dfb19777ce2789a860ae2121a13cc1bd622d6af5'}")
    print()

    # Verify: git rev-parse HEAD^{tree} on same content → dfb19777...

    # The key insight: two directories with identical content
    # produce the same SWHID, regardless of timestamps, paths, etc.
    with tempfile.TemporaryDirectory() as d2:
        os.makedirs(os.path.join(d2, "src"))
        with open(os.path.join(d2, "README.md"), "wb") as f:
            f.write(b"# Hello")
        with open(os.path.join(d2, "LICENSE"), "wb") as f:
            f.write(b"MIT")
        with open(os.path.join(d2, "src", "main.py"), "wb") as f:
            f.write(b"print('hi')")

        ds2 = directory_id(d2)
        print(f"  Same content in different directory:")
        print(f"  directory_id('{d2}')")
        print(f"  → {ds2}")
        print(f"  Identical to first: {ds == ds2}")
        print()
        print(f"  ✓ This is the ATR use-case: unpack .tar.gz and .zip of the")
        print(f"    same release → directory_id() matches → content is identical")


# ── 6. Exclude suffixes ───────────────────────────────────────

section("6. Excluding files from directory hash")

with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "main.py"), "wb") as f:
        f.write(b"print('hi')")
    with open(os.path.join(d, "main.pyc"), "wb") as f:
        f.write(b"\x00\x00\x00\x00compiled")

    full = directory_id(d)
    no_pyc = directory_id(d, exclude_suffixes=[".pyc"])
    print(f"  directory with main.py + main.pyc:")
    print(f"    full hash:          {full}")
    print(f"    excluding .pyc:     {no_pyc}")
    print(f"    Different (expected): {full != no_pyc}")


# ── 7. Verify ─────────────────────────────────────────────────

section("7. Verify a file against an expected SWHID")

with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
    f.write(b"Hello, World!")
    tmp_file = f.name

expected = "swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684"
result = verify(tmp_file, expected)
print(f"  verify('{tmp_file}', '{expected}')")
print(f"  → {result}")
print()

wrong = "swh:1:cnt:" + "0" * 40
result2 = verify(tmp_file, wrong)
print(f"  verify('{tmp_file}', 'swh:1:cnt:0000...')")
print(f"  → {result2}")
os.unlink(tmp_file)


# ── 8. Qualified SWHIDs ───────────────────────────────────────

section("8. Qualified SWHIDs (with origin, path, lines)")

q = QualifiedSwhid("swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
print(f"  Base: {q}")
print()

q2 = q.with_origin("https://github.com/apache/commons-codec")
print(f"  .with_origin('https://github.com/apache/commons-codec')")
print(f"  → {q2}")
print()

q3 = q2.with_path("/src/main/java/Example.java").with_lines(10, 20)
print(f"  .with_path('/src/main/java/Example.java').with_lines(10, 20)")
print(f"  → {q3}")
print()

print(f"  Core SWHID extracted back:")
print(f"  q3.core → {q3.core}")


# ── 9. Equality and hashing ───────────────────────────────────

section("9. Equality, hashing, use in sets/dicts")

a = content_id(b"Hello, World!")
b = Swhid("swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
c = content_id(b"different")

print(f"  a == b (same content): {a == b}")
print(f"  a == c (different):    {a == c}")
print(f"  hash(a) == hash(b):    {hash(a) == hash(b)}")
print()

swhid_set = {a, b, c}
print(f"  {{a, b, c}} has {len(swhid_set)} unique elements (a and b deduplicate)")
print()

lookup = {a: "hello.txt", c: "other.txt"}
print(f"  Dict lookup: lookup[b] → '{lookup[b]}'  (b equals a)")


print(f"\n{'=' * 60}")
print(f"  All examples completed successfully!")
print(f"{'=' * 60}\n")
