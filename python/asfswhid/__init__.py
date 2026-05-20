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
asfswhid – Python bindings for the swhid-rs SWHID v1.2 reference implementation.

Wraps the Rust crate ``swhid`` (https://github.com/swhid/swhid-rs) via PyO3,
giving Python code native-speed SWHID computation fully compliant with
ISO/IEC 18670:2025.

Quick start::

    from asfswhid import content_id, directory_id, verify, Swhid

    # Hash file content
    swhid = content_id(b"Hello, World!")
    print(swhid)                        # swh:1:cnt:b45ef6fec...

    # Hash a directory tree (Merkle hash, format-agnostic)
    dir_swhid = directory_id("/path/to/source")

    # Verify a file matches an expected SWHID
    assert verify("README.md", "swh:1:cnt:...")

    # Parse an existing SWHID string
    parsed = Swhid("swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
    print(parsed.object_type)           # ObjectType.Content
    print(parsed.digest_hex)            # b45ef6fec89518d...

VCS integration (requires the ``gitoxide`` feature, enabled by default)::

    from asfswhid import revision_id, release_id, snapshot_id

    rev = revision_id("/path/to/repo")           # HEAD commit
    rev = revision_id("/path/to/repo", "abc123")  # specific commit
    snp = snapshot_id("/path/to/repo")            # all branches + tags
    rel = release_id("/path/to/repo", "v1.0.0")  # annotated tag
"""

from .asfswhid import (  # type: ignore[import]
    ObjectType,
    Swhid,
    QualifiedSwhid,
    content_id,
    content_id_from_file,
    directory_id,
    verify,
)

__all__ = [
    "ObjectType",
    "Swhid",
    "QualifiedSwhid",
    "content_id",
    "content_id_from_file",
    "directory_id",
    "verify",
]

# VCS functions are only available when built with the gitoxide (or git) feature.
# They are enabled by default via pyproject.toml's [tool.maturin] features.
try:
    from .asfswhid import revision_id, release_id, snapshot_id  # type: ignore[import]

    __all__ += ["revision_id", "release_id", "snapshot_id"]
except ImportError:
    pass

__version__ = "0.1.0"
