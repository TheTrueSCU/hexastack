from hexastack_db.domain.analytics import (
    ColumnarExportResult,
    ColumnarProjectionMetadata,
)


def test_columnar_projection_metadata_instantiation():
    meta = ColumnarProjectionMetadata(
        num_rows=1000,
        num_columns=4,
        column_names=("id", "name", "val", "created_at"),
        byte_size=4096,
        execution_time_ms=12.5,
    )
    assert meta.num_rows == 1000
    assert meta.num_columns == 4
    assert meta.column_names == ("id", "name", "val", "created_at")
    assert meta.byte_size == 4096
    assert meta.execution_time_ms == 12.5


def test_columnar_export_result_to_file(tmp_path):
    meta = ColumnarProjectionMetadata(
        num_rows=2,
        num_columns=2,
        column_names=("col_a", "col_b"),
        byte_size=10,
    )
    payload = b"test-bytes-data"
    result = ColumnarExportResult(
        data=payload,
        format="parquet",
        metadata=meta,
    )

    dest = tmp_path / "subdir" / "output.parquet"
    written_path = result.to_file(dest)

    exists = written_path.exists()
    assert exists is True
    assert written_path == dest

    read_back = dest.read_bytes()
    assert read_back == payload
