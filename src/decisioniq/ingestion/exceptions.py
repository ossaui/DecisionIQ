
class IngestionError(Exception):
    """Base exception for data ingestion errors."""


class UnsupportedFormatError(IngestionError):
    """Raised when a file format is unsupported."""


class EmptyDatasetError(IngestionError):
    """Raised when a dataset contains no records."""


class FileSizeLimitError(IngestionError):
    """Raised when a file exceeds the size limit."""


class DataReadError(IngestionError):
    """Raised when a dataset cannot be read."""
