# Build & Integration Notes

## Where REFERENCE.md diverged from the actual API

The `swhid-rs` REFERENCE.md describes the intended architecture but several
details don't match the 0.2.2 crate as published. These were all resolved
during the initial build, documented here for future reference.

1. **`SwhidError` path** — REFERENCE.md implies `swhid::SwhidError`. The
   actual path is `swhid::error::SwhidError` (not re-exported at crate root).

2. **Directory hashing** — REFERENCE.md shows `Directory::new(root: &Path)`.
   In practice, `Directory::new()` takes `Vec<Entry>` (pre-built entries).
   The path-based entry point is `DiskDirectoryBuilder::new(&path)`, which
   provides `.with_options(walk_opts)` and `.swhid()`.

3. **`LineRange` / `ByteRange` fields are `u64`** — REFERENCE.md shows `u32`.
   The actual structs use `u64` for both `start` and `end`.

4. **`with_lines()` / `with_bytes()` take structs** — REFERENCE.md shows
   `with_lines(10, Some(20))`. The actual API is
   `with_lines(LineRange { start, end })`.

Things that matched REFERENCE.md without issue: `Content::from_bytes().swhid()`,
`Swhid` parsing via `FromStr`, `QualifiedSwhid` builder pattern (`.with_origin()`,
`.with_path()`), `WalkOptions` struct fields (`follow_symlinks`, `exclude_suffixes`),
and `ObjectType` enum variants.

## Conformance test expectations

Dave mentioned needing conformance tests that match both the Rust reference
and the Java commons-codec implementation. The test suite includes:

- `test_conformance.py::TestContentConformance` — checks against known
  `git hash-object` values (works out of the box, all passing)
- `test_conformance.py::TestCrossImplementation` — compares against the
  `swhid` CLI binary (set `SWHID_CLI` env var)
- Future: add vectors from the Java implementation once
  `apache/commons-codec#428` merges and publishes test vectors

## Git feature

The `swhid-rs` crate has an optional `git` feature for computing revision,
release, and snapshot SWHIDs from Git repos (uses `libgit2`). The current
wrapper doesn't expose these yet — it focuses on `content` and `directory`
which are the primary ATR use-cases. Adding git support later means:

1. Add `git = ["swhid/git"]` feature in `Cargo.toml` (already there)
2. Add `#[cfg(feature = "git")]` functions in `lib.rs`
3. Note: `libgit2` (via `git2` crate) adds significant build complexity,
   especially on Windows. Consider whether ATR actually needs this or if
   shelling out to `git` is sufficient.

## Wheel distribution

The CI workflow builds manylinux/macOS/Windows wheels via `maturin-action`.
For PyPI publishing, add a release job triggered by tags. The maturin docs
have a good template: https://www.maturin.rs/distribution

## Licensing

- This wrapper: Apache-2.0 (matches ATR)
- swhid-rs: MIT (compatible)
- PyO3: Apache-2.0 OR MIT (compatible)
- No GPL dependencies anywhere in the chain ✓