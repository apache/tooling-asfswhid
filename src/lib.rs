// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

use pyo3::exceptions::{PyOSError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::path::PathBuf;
use swhid::error::SwhidError;

#[cfg(feature = "gitoxide")]
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Error helpers
// ---------------------------------------------------------------------------

fn swhid_err(e: SwhidError) -> PyErr {
    match &e {
        SwhidError::Io(_) => PyOSError::new_err(e.to_string()),
        _ => PyValueError::new_err(e.to_string()),
    }
}

// ---------------------------------------------------------------------------
// ObjectType enum
// ---------------------------------------------------------------------------

/// SWHID object type: cnt, dir, rev, rel, snp
#[pyclass(name = "ObjectType", eq, eq_int)]
#[derive(Clone, Debug, PartialEq)]
pub enum PyObjectType {
    Content = 0,
    Directory = 1,
    Revision = 2,
    Release = 3,
    Snapshot = 4,
}

#[pymethods]
impl PyObjectType {
    /// Return the three-letter tag (e.g. "cnt", "dir").
    fn tag(&self) -> &'static str {
        match self {
            PyObjectType::Content => "cnt",
            PyObjectType::Directory => "dir",
            PyObjectType::Revision => "rev",
            PyObjectType::Release => "rel",
            PyObjectType::Snapshot => "snp",
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "ObjectType.{}",
            match self {
                PyObjectType::Content => "Content",
                PyObjectType::Directory => "Directory",
                PyObjectType::Revision => "Revision",
                PyObjectType::Release => "Release",
                PyObjectType::Snapshot => "Snapshot",
            }
        )
    }
}

impl From<swhid::ObjectType> for PyObjectType {
    fn from(ot: swhid::ObjectType) -> Self {
        match ot {
            swhid::ObjectType::Content => PyObjectType::Content,
            swhid::ObjectType::Directory => PyObjectType::Directory,
            swhid::ObjectType::Revision => PyObjectType::Revision,
            swhid::ObjectType::Release => PyObjectType::Release,
            swhid::ObjectType::Snapshot => PyObjectType::Snapshot,
        }
    }
}

impl From<PyObjectType> for swhid::ObjectType {
    fn from(ot: PyObjectType) -> Self {
        match ot {
            PyObjectType::Content => swhid::ObjectType::Content,
            PyObjectType::Directory => swhid::ObjectType::Directory,
            PyObjectType::Revision => swhid::ObjectType::Revision,
            PyObjectType::Release => swhid::ObjectType::Release,
            PyObjectType::Snapshot => swhid::ObjectType::Snapshot,
        }
    }
}

// ---------------------------------------------------------------------------
// Swhid – core identifier
// ---------------------------------------------------------------------------

/// A parsed SWHID core identifier (``swh:1:<type>:<hex>``).
#[pyclass(name = "Swhid")]
#[derive(Clone, Debug)]
pub struct PySwhid {
    inner: swhid::Swhid,
}

#[pymethods]
impl PySwhid {
    /// Parse a SWHID string such as ``"swh:1:cnt:abc123..."``.
    #[new]
    fn new(swhid_str: &str) -> PyResult<Self> {
        let inner: swhid::Swhid = swhid_str
            .parse()
            .map_err(|e: SwhidError| PyValueError::new_err(e.to_string()))?;
        Ok(PySwhid { inner })
    }

    /// The object type.
    #[getter]
    fn object_type(&self) -> PyObjectType {
        self.inner.object_type().into()
    }

    /// The 40-character lowercase hex digest.
    #[getter]
    fn digest_hex(&self) -> String {
        self.inner.digest_hex()
    }

    /// The raw 20-byte digest.
    fn digest_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, self.inner.digest_bytes())
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("Swhid('{}')", self.inner)
    }

    fn __eq__(&self, other: &PySwhid) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut h = DefaultHasher::new();
        self.inner.to_string().hash(&mut h);
        h.finish()
    }
}

// ---------------------------------------------------------------------------
// QualifiedSwhid
// ---------------------------------------------------------------------------

/// A SWHID with optional qualifiers (origin, visit, anchor, path, lines, bytes).
#[pyclass(name = "QualifiedSwhid")]
#[derive(Clone, Debug)]
pub struct PyQualifiedSwhid {
    inner: swhid::QualifiedSwhid,
}

#[pymethods]
impl PyQualifiedSwhid {
    /// Parse a qualified SWHID string.
    #[new]
    fn new(s: &str) -> PyResult<Self> {
        let inner: swhid::QualifiedSwhid = s
            .parse()
            .map_err(|e: SwhidError| PyValueError::new_err(e.to_string()))?;
        Ok(PyQualifiedSwhid { inner })
    }

    /// The core SWHID (without qualifiers).
    #[getter]
    fn core(&self) -> PySwhid {
        PySwhid {
            inner: self.inner.core().clone(),
        }
    }

    /// Return a new QualifiedSwhid with origin set.
    fn with_origin(&self, url: &str) -> PyResult<Self> {
        let q = self.inner.clone().with_origin(url);
        Ok(PyQualifiedSwhid { inner: q })
    }

    /// Return a new QualifiedSwhid with path set.
    fn with_path(&self, path: &str) -> PyResult<Self> {
        let q = self.inner.clone().with_path(path);
        Ok(PyQualifiedSwhid { inner: q })
    }

    /// Return a new QualifiedSwhid with lines set.
    #[pyo3(signature = (start, end=None))]
    fn with_lines(&self, start: u64, end: Option<u64>) -> PyResult<Self> {
        let range = swhid::LineRange { start, end };
        let q = self.inner.clone().with_lines(range);
        Ok(PyQualifiedSwhid { inner: q })
    }

    /// Return a new QualifiedSwhid with bytes set.
    #[pyo3(signature = (start, end=None))]
    fn with_bytes(&self, start: u64, end: Option<u64>) -> PyResult<Self> {
        let range = swhid::ByteRange { start, end };
        let q = self.inner.clone().with_bytes(range);
        Ok(PyQualifiedSwhid { inner: q })
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("QualifiedSwhid('{}')", self.inner)
    }
}

// ---------------------------------------------------------------------------
// Free functions – content & directory hashing
// ---------------------------------------------------------------------------

/// Compute the SWHID for raw byte content (file data).
#[pyfunction]
fn content_id(data: &[u8]) -> PySwhid {
    let inner = swhid::Content::from_bytes(data).swhid();
    PySwhid { inner }
}

/// Compute the SWHID for a file on disk.
#[pyfunction]
fn content_id_from_file(path: &str) -> PyResult<PySwhid> {
    let data =
        std::fs::read(path).map_err(|e| PyOSError::new_err(format!("cannot read {path}: {e}")))?;
    Ok(content_id(&data))
}

/// Compute the SWHID for a directory tree.
#[pyfunction]
#[pyo3(signature = (root, follow_symlinks=false, exclude_suffixes=None))]
fn directory_id(
    root: &str,
    follow_symlinks: bool,
    exclude_suffixes: Option<Vec<String>>,
) -> PyResult<PySwhid> {
    let path = PathBuf::from(root);
    let walk_opts = swhid::WalkOptions {
        follow_symlinks,
        exclude_suffixes: exclude_suffixes.unwrap_or_default(),
    };
    let inner = swhid::DiskDirectoryBuilder::new(&path)
        .with_options(walk_opts)
        .swhid()
        .map_err(swhid_err)?;
    Ok(PySwhid { inner })
}

/// Verify that a file or directory matches an expected SWHID.
#[pyfunction]
fn verify(path: &str, expected: &str) -> PyResult<bool> {
    let expected_swhid: swhid::Swhid = expected
        .parse()
        .map_err(|e: SwhidError| PyValueError::new_err(e.to_string()))?;

    let p = PathBuf::from(path);
    let computed = if p.is_dir() {
        swhid::DiskDirectoryBuilder::new(&p)
            .swhid()
            .map_err(swhid_err)?
    } else {
        let data = std::fs::read(&p)
            .map_err(|e| PyOSError::new_err(format!("cannot read {path}: {e}")))?;
        swhid::Content::from_bytes(data).swhid()
    };

    Ok(computed == expected_swhid)
}

// ---------------------------------------------------------------------------
// Git VCS functions (gitoxide backend – MIT/Apache-2.0)
// ---------------------------------------------------------------------------

/// Compute the revision SWHID for a Git commit.
///
/// Args:
///     repo_path: Path to the Git repository.
///     commit: Optional commit hash (hex string). If omitted, uses HEAD.
///
/// Returns:
///     A ``Swhid`` object of type ``rev``.
#[cfg(feature = "gitoxide")]
#[pyfunction]
#[pyo3(signature = (repo_path, commit=None))]
fn revision_id(repo_path: &str, commit: Option<&str>, py: Python<'_>) -> PyResult<PySwhid> {
    let p = repo_path.to_string();
    let c = commit.map(|s| s.to_string());
    py.allow_threads(|| {
        let repo = swhid::git_gix::open_repo(std::path::Path::new(&p)).map_err(swhid_err)?;
        let oid = match &c {
            Some(hex) => gix::ObjectId::from_hex(hex.as_bytes())
                .map_err(|e| PyValueError::new_err(format!("Invalid commit hash: {e}")))?,
            None => swhid::git_gix::get_head_commit(&repo).map_err(swhid_err)?,
        };
        let inner =
            swhid::git_gix::revision_swhid(&repo, &oid, &mut HashMap::new()).map_err(swhid_err)?;
        Ok(PySwhid { inner })
    })
}

/// Compute the release SWHID for a Git tag.
///
/// Args:
///     repo_path: Path to the Git repository.
///     tag: Tag name (e.g. ``"v1.0.0"``).
///
/// Returns:
///     A ``Swhid`` object of type ``rel``.
#[cfg(feature = "gitoxide")]
#[pyfunction]
fn release_id(repo_path: &str, tag: &str, py: Python<'_>) -> PyResult<PySwhid> {
    let p = repo_path.to_string();
    let t = format!("refs/tags/{tag}");
    py.allow_threads(|| {
        let repo = swhid::git_gix::open_repo(std::path::Path::new(&p)).map_err(swhid_err)?;
        let reference = repo
            .find_reference(&t)
            .map_err(|e| PyValueError::new_err(format!("Tag not found: {e}")))?;
        let tag_oid = reference
            .target()
            .try_id()
            .ok_or_else(|| PyValueError::new_err("Tag is a symbolic reference, not a direct one"))?
            .to_owned();
        let inner = swhid::git_gix::release_swhid(&repo, &tag_oid).map_err(swhid_err)?;
        Ok(PySwhid { inner })
    })
}

/// Compute the snapshot SWHID for a Git repository.
///
/// Args:
///     repo_path: Path to the Git repository.
///
/// Returns:
///     A ``Swhid`` object of type ``snp``.
#[cfg(feature = "gitoxide")]
#[pyfunction]
fn snapshot_id(repo_path: &str, py: Python<'_>) -> PyResult<PySwhid> {
    let p = repo_path.to_string();
    py.allow_threads(|| {
        let repo = swhid::git_gix::open_repo(std::path::Path::new(&p)).map_err(swhid_err)?;
        let inner = swhid::git_gix::snapshot_swhid(&repo).map_err(swhid_err)?;
        Ok(PySwhid { inner })
    })
}

// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

/// Python bindings for the ``swhid-rs`` SWHID v1.2 reference implementation.
///
/// Provides content-addressed identifiers (SWHIDs) compatible with the
/// Software Heritage archive and ISO/IEC 18670:2025.
#[pymodule]
fn asfswhid(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyObjectType>()?;
    m.add_class::<PySwhid>()?;
    m.add_class::<PyQualifiedSwhid>()?;
    m.add_function(wrap_pyfunction!(content_id, m)?)?;
    m.add_function(wrap_pyfunction!(content_id_from_file, m)?)?;
    m.add_function(wrap_pyfunction!(directory_id, m)?)?;
    m.add_function(wrap_pyfunction!(verify, m)?)?;
    #[cfg(feature = "gitoxide")]
    {
        m.add_function(wrap_pyfunction!(revision_id, m)?)?;
        m.add_function(wrap_pyfunction!(release_id, m)?)?;
        m.add_function(wrap_pyfunction!(snapshot_id, m)?)?;
    }
    Ok(())
}
