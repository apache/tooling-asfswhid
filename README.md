# asfswhid

Python bindings for the [`swhid-rs`](https://github.com/swhid/swhid-rs) SWHID v1.2 reference implementation (ISO/IEC 18670:2025).

Wraps the **Rust reference implementation** via [PyO3](https://pyo3.rs), giving Python code native-speed SWHID computation with full specification compliance.

## Why this exists

The standard Python library for SWHIDs (`swh.model`) is **GPL-3.0 licensed**, which is incompatible with Apache-licensed projects. The alternative [`miniswhid`](https://pypi.org/project/miniswhid/) package covers content and directory hashing but does not support qualified identifiers or VCS integration.

This package wraps the MIT-licensed Rust reference implementation directly, sidestepping the licensing issue while getting the canonical, specification-compliant implementation. It supports the **full SWHID v1.2 specification**:

- **Content** (`cnt`) — file hashing, Git blob compatible
- **Directory** (`dir`) — Merkle tree hashing, format-agnostic archive comparison
- **Revision** (`rev`) — Git commit identification
- **Release** (`rel`) — Git annotated tag identification
- **Snapshot** (`snp`) — full repository state capture
- **Qualified identifiers** — origin, visit, anchor, path, lines, bytes

VCS integration (revision, release, snapshot) uses [gitoxide](https://github.com/GitoxideLabs/gitoxide) (MIT/Apache-2.0) instead of libgit2 (GPL-2.0), keeping the entire dependency chain permissively licensed.

**Context:** [apache/tooling-trusted-releases#1154](https://github.com/apache/tooling-trusted-releases/issues/1154)

## Installation

### From PyPI

```bash
pip install asfswhid
```

### From Git

```bash
pip install git+https://github.com/apache/tooling-asfswhid.git
```

This requires the Rust toolchain to be installed. If you don't have it:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### From source

```bash
git clone https://github.com/apache/tooling-asfswhid.git
cd tooling-asfswhid
uv venv && source .venv/bin/activate
uv pip install maturin
maturin develop          # dev install into current venv
# or
maturin build --release  # build a wheel
uv pip install target/wheels/asfswhid-*.whl
```

## Quick start

```python
from asfswhid import content_id, directory_id, verify, Swhid

# Hash file content (Git blob compatible)
swhid = content_id(b"Hello, World!")
print(swhid)  # swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684

# Hash from a file on disk
swhid = content_id_from_file("README.md")

# Hash a directory tree (Merkle hash, format-agnostic)
dir_swhid = directory_id("/path/to/source")

# Compare two unpacked archives — if content matches, SWHIDs match
assert directory_id("/tmp/release-tar") == directory_id("/tmp/release-zip")

# Verify a file or directory against an expected SWHID
assert verify("README.md", "swh:1:cnt:...")

# Parse and inspect
parsed = Swhid("swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
print(parsed.object_type)   # ObjectType.Content
print(parsed.digest_hex)    # b45ef6fec89518d314f546fd6c3025367b721684
print(parsed.digest_bytes()) # b'\xb4^...' (20 bytes)
```

### VCS integration

Compute revision, release, and snapshot SWHIDs directly from Git repositories:

```python
from asfswhid import revision_id, release_id, snapshot_id

# Revision SWHID for HEAD
rev = revision_id("/path/to/repo")
print(rev)  # swh:1:rev:...

# Revision SWHID for a specific commit
rev = revision_id("/path/to/repo", "a1b2c3d4...")

# Release SWHID for an annotated tag
rel = release_id("/path/to/repo", "v1.0.0")
print(rel)  # swh:1:rel:...

# Snapshot SWHID — captures all branches and tags
snp = snapshot_id("/path/to/repo")
print(snp)  # swh:1:snp:...
```

These functions use [gitoxide](https://github.com/GitoxideLabs/gitoxide) (MIT/Apache-2.0) as the Git backend — no GPL dependencies anywhere in the chain.

## Using asfswhid in your project

### As a dependency

Add to your `requirements.txt`:

```
asfswhid @ git+https://github.com/apache/tooling-asfswhid.git
```

Or pin to a specific release tag:

```
asfswhid @ git+https://github.com/apache/tooling-asfswhid.git@v0.1.1
```

Then install with `uv pip install -r requirements.txt` (or `pip install -r requirements.txt`).

### In pyproject.toml

```toml
[project]
dependencies = [
    "asfswhid @ git+https://github.com/apache/tooling-asfswhid.git",
]
```

Or once published to PyPI:

```toml
[project]
dependencies = [
    "asfswhid>=0.1.0",
]
```

### Calling from your code

#### Hash a release archive after unpacking

```python
import tarfile
import tempfile
from asfswhid import directory_id

with tempfile.TemporaryDirectory() as tmp:
    with tarfile.open("commons-codec-1.17.0-src.tar.gz") as tar:
        tar.extractall(tmp)
    swhid = directory_id(f"{tmp}/commons-codec-1.17.0-src")
    print(f"Source archive SWHID: {swhid}")
```

#### Compare .tar.gz and .zip of the same release

```python
import tarfile
import zipfile
import tempfile
from asfswhid import directory_id

with tempfile.TemporaryDirectory() as tmp:
    # Unpack both formats
    with tarfile.open("release-1.0.0.tar.gz") as tar:
        tar.extractall(f"{tmp}/from_tar")
    with zipfile.ZipFile("release-1.0.0.zip") as zf:
        zf.extractall(f"{tmp}/from_zip")

    tar_swhid = directory_id(f"{tmp}/from_tar/release-1.0.0")
    zip_swhid = directory_id(f"{tmp}/from_zip/release-1.0.0")

    if tar_swhid == zip_swhid:
        print(f"Archives match: {tar_swhid}")
    else:
        print(f"MISMATCH — tar: {tar_swhid}, zip: {zip_swhid}")
```

#### Verify a downloaded file against a known SWHID

```python
from asfswhid import verify

expected = "swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684"
if verify("downloaded-file.txt", expected):
    print("Integrity check passed")
else:
    print("WARNING: file does not match expected SWHID")
```

#### Add origin metadata with qualified SWHIDs

```python
from asfswhid import content_id, QualifiedSwhid

swhid = content_id(open("src/main.py", "rb").read())
qualified = (
    QualifiedSwhid(str(swhid))
    .with_origin("https://github.com/apache/commons-codec")
    .with_path("/src/main/java/Codec.java")
    .with_lines(42, 58)
)
print(qualified)
# swh:1:cnt:...;origin=https://github.com/apache/commons-codec;path=/src/main/java/Codec.java;lines=42-58
```

#### Exclude build artifacts from directory hash

```python
from asfswhid import directory_id

swhid = directory_id(
    "/path/to/project",
    exclude_suffixes=[".pyc", ".o", ".class", ".jar"],
)
```

## Verifying it works

A full `example_usage.py` script is included in the repo. Build and run it:

```bash
maturin develop
python example_usage.py
```

### Content hash test vectors

Every content SWHID is a Git blob hash. You can verify any of these with
`echo -n "<data>" | git hash-object --stdin`:

| Input | Expected SWHID |
|---|---|
| `b""` (empty) | `swh:1:cnt:e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` |
| `b"Hello, World!"` | `swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684` |
| `b"\n"` (newline) | `swh:1:cnt:8b137891791fe96927ad78e64b0aad7bded08bdc` |
| `b"a" * 1000` | `swh:1:cnt:a50be72b20f0e3f078d252e8e56b11b4bec67509` |

### Directory hash test vectors

Directory SWHIDs use Git's tree object Merkle hash. Given this tree:

```
README.md   → b"# Hello"
LICENSE     → b"MIT"
src/main.py → b"print('hi')"
```

The expected SWHID is `swh:1:dir:dfb19777ce2789a860ae2121a13cc1bd622d6af5`.

You can verify by creating the same tree in a git repo and running
`git rev-parse HEAD^{tree}`.

### Expected interactive session

```python
>>> from asfswhid import content_id, directory_id, verify, Swhid, QualifiedSwhid

>>> s = content_id(b"Hello, World!")
>>> s
Swhid('swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684')
>>> str(s)
'swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684'
>>> s.object_type
ObjectType.Content
>>> s.object_type.tag()
'cnt'
>>> s.digest_hex
'b45ef6fec89518d314f546fd6c3025367b721684'
>>> s.digest_bytes()
b'\xb4^\xf6\xfe\xc8\x95\x18\xd3\x14\xf5F\xfdl0%6{r\x16\x84'

>>> content_id(b"") == content_id(b"")
True
>>> content_id(b"a") == content_id(b"b")
False

# Two directories with identical content always match, regardless of path
>>> import tempfile, os
>>> d1 = tempfile.mkdtemp()
>>> d2 = tempfile.mkdtemp()
>>> open(os.path.join(d1, "f.txt"), "wb").write(b"same")
4
>>> open(os.path.join(d2, "f.txt"), "wb").write(b"same")
4
>>> directory_id(d1) == directory_id(d2)
True

# Excluding files changes the hash
>>> open(os.path.join(d1, "junk.pyc"), "wb").write(b"compiled")
8
>>> directory_id(d1) == directory_id(d2)
False
>>> directory_id(d1, exclude_suffixes=[".pyc"]) == directory_id(d2)
True

# Verify
>>> verify(os.path.join(d1, "f.txt"), "swh:1:cnt:" + "0" * 40)
False

# Parse — invalid strings raise ValueError
>>> Swhid("not-a-swhid")
Traceback (most recent call last):
  ...
ValueError: ...

# Qualified SWHIDs
>>> q = QualifiedSwhid("swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
>>> q = q.with_origin("https://github.com/apache/commons-codec")
>>> q = q.with_path("/src/main/java/Example.java")
>>> q = q.with_lines(10, 20)
>>> q.core
Swhid('swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684')

# SWHIDs are hashable — use in sets and dicts
>>> a = content_id(b"Hello, World!")
>>> b = Swhid("swh:1:cnt:b45ef6fec89518d314f546fd6c3025367b721684")
>>> a == b
True
>>> len({a, b})
1

# VCS integration — compute revision and snapshot SWHIDs
>>> from asfswhid import revision_id, snapshot_id
>>> rev = revision_id(".")       # HEAD of current repo
>>> rev.object_type
ObjectType.Revision
>>> rev.object_type.tag()
'rev'
>>> snp = snapshot_id(".")       # all branches + tags
>>> snp.object_type.tag()
'snp'
```

## ATR use-cases

This package supports key use-cases for [Apache Trusted Releases](https://github.com/apache/tooling-trusted-releases):

### Cross-format archive comparison

Many projects release as both `.tar.gz` and `.zip`. The directory SWHID is computed over the content tree, ignoring archive metadata (timestamps, file ordering, compression). If you unpack both and compute `directory_id()` on each, matching SWHIDs prove identical content.

### Git commit ↔ source archive verification

Compute the directory SWHID of an unpacked source archive and compare it against the tree SWHID of the tagged Git commit. If they match, the archive provably corresponds to that commit.

### Revision and snapshot tracking

Compute revision SWHIDs for specific commits and snapshot SWHIDs for the full repository state. These can be stored alongside release artifacts to provide cryptographic proof of which exact repository state produced the release:

```python
from asfswhid import revision_id, snapshot_id

rev = revision_id("/path/to/repo", "v1.0.0-rc1-commit-hash")
snp = snapshot_id("/path/to/repo")
print(f"Release built from revision: {rev}")
print(f"Repository state at release: {snp}")
```

## Conformance testing

The test suite includes conformance checks against:

- **`git hash-object`** — verifies content hashing matches Git exactly
- **`swhid` CLI** — verifies output matches the Rust reference binary (set `SWHID_CLI` env var)
- **Known test vectors** — hard-coded expected values

```bash
uv pip install pytest
maturin develop
pytest tests/ -v

# With cross-implementation checks:
cargo install swhid
SWHID_CLI=swhid pytest tests/test_conformance.py -v
```

## Development

```bash
# Prerequisites: Rust toolchain, Python 3.9+, uv
git clone https://github.com/apache/tooling-asfswhid.git
cd tooling-asfswhid
uv venv && source .venv/bin/activate
uv pip install maturin pytest

# Build + install in dev mode
maturin develop

# Run Python tests
pytest tests/ -v

# Run Rust tests on the forked crate
cargo test --manifest-path swhid-rs/Cargo.toml --features gitoxide

# Build release wheel
maturin build --release

# Lint
cargo fmt --check
cargo clippy -- -D warnings
```

## Architecture

```
tooling-asfswhid/
├── Cargo.toml                  # Bindings crate (path dep on swhid-rs/)
├── pyproject.toml              # Python package metadata (maturin build)
├── example_usage.py            # Runnable demo with expected outputs
├── src/
│   └── lib.rs                  # PyO3 bindings wrapping swhid-rs
├── python/
│   └── asfswhid/
│       ├── __init__.py         # Re-exports from native module
│       └── __init__.pyi        # Type stubs for IDE support
├── swhid-rs/                   # Forked upstream crate (git subtree)
│   ├── Cargo.toml
│   ├── src/
│   ├── tests/
│   └── docs/
├── tests/
│   ├── test_asfswhid.py        # Unit tests
│   └── test_conformance.py     # Cross-implementation conformance tests
└── .github/
    └── workflows/
        ├── ci.yml              # CI: test on push/PR
        └── release.yml         # Build wheels + publish to PyPI on tag
```

The Rust side (`src/lib.rs`) is pure glue — it calls into the `swhid` crate's public API and exposes it via PyO3. No cryptographic or hashing code lives here; that's all in `swhid-rs/`.

The `swhid-rs/` directory contains a copy of the upstream [`swhid/swhid-rs`](https://github.com/swhid/swhid-rs) crate with the gitoxide backend addition. It is consumed via `swhid = { path = "swhid-rs", features = ["gitoxide"] }` in the root `Cargo.toml`.

## Keeping the upstream crate in sync

The `swhid-rs/` directory contains a copy of the upstream [`swhid/swhid-rs`](https://github.com/swhid/swhid-rs) crate with the gitoxide backend addition. To sync with upstream:

```bash
# Clone upstream into a temp directory
git clone https://github.com/swhid/swhid-rs.git /tmp/swhid-rs-upstream
rm -rf /tmp/swhid-rs-upstream/.git /tmp/swhid-rs-upstream/.github

# Replace local copy
rm -rf swhid-rs/
cp -r /tmp/swhid-rs-upstream swhid-rs/

# Verify nothing broke
maturin develop
pytest tests/ -v

# Commit and push
git add swhid-rs/
git commit -m "Sync swhid-rs with upstream main"
git push origin main
```

If the upstream crate publishes a crates.io release with the gitoxide feature, you can drop the subtree entirely and switch to a version dependency:

```toml
# In Cargo.toml, replace:
swhid = { path = "swhid-rs", features = ["gitoxide"] }

# With:
swhid = { version = "0.3", features = ["gitoxide"] }
```

Then remove the `swhid-rs/` directory:

```bash
git rm -r swhid-rs/
git commit -m "Switch to crates.io swhid release, remove subtree"
```

## License

Apache-2.0 (this wrapper). The upstream `swhid-rs` crate is MIT-licensed. VCS integration uses [gitoxide](https://github.com/GitoxideLabs/gitoxide) (MIT/Apache-2.0) — no GPL dependencies.

## References

- [SWHID specification v1.2](https://swhid.org/swhid-specification/v1.2/)
- [ISO/IEC 18670:2025](https://www.iso.org/standard/85543.html) — Software Heritage Identifiers
- [`swhid-rs`](https://github.com/swhid/swhid-rs) — Rust reference implementation
- [ATR issue #1154](https://github.com/apache/tooling-trusted-releases/issues/1154) — SWHID integration proposal
- [`apache/commons-codec#428`](https://github.com/apache/commons-codec/pull/428) — Java implementation
