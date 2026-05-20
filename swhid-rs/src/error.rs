use thiserror::Error;

use crate::Bytestring;

/// Errors that may occur while parsing SWHIDs or computing hashes.
#[derive(Debug, Error)]
pub enum SwhidError {
    #[error("invalid SWHID format: {0}")]
    InvalidFormat(String),

    #[error("invalid URI scheme (expected `swh`): {0}")]
    InvalidScheme(String),

    #[error("unsupported SWHID version: {0}")]
    InvalidVersion(String),

    #[error("invalid object type: {0}")]
    InvalidObjectType(String),

    #[error("invalid digest (expected 40 hex chars): {0}")]
    InvalidDigest(String),

    #[error("invalid qualifier key: {0}")]
    InvalidQualifierKey(String),

    #[error("invalid qualifier value for `{key}`: {value}")]
    InvalidQualifierValue { key: String, value: String },

    #[error("I/O error: {0}")]
    Io(#[source] std::io::Error),
}

/// Errors that may occur while building a [`Directory`](crate::Directory)
#[derive(Debug, Error)]
pub enum DirectoryError {
    #[error("Duplicate entry name: {}", String::from_utf8_lossy(.0))]
    DuplicateEntryName(Bytestring),
    #[error("Invalid byte {byte} in name: {}", String::from_utf8_lossy(.name))]
    InvalidByteInName { byte: u8, name: Bytestring },
}

/// Errors that may occur while building a [`Snapshot`](crate::Snapshot)
#[derive(Debug, Error)]
pub enum SnapshotError {
    #[error("Duplicate branch name: {}", String::from_utf8_lossy(.0))]
    DuplicateBranchName(Bytestring),
    #[error("Invalid byte {byte} in name: {}", String::from_utf8_lossy(.name))]
    InvalidByteInName { byte: u8, name: Bytestring },
}
