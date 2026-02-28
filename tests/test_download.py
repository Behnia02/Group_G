from pathlib import Path

from app.data_download import download_datasets


def test_download_creates_files(tmp_path):
    download_datasets(download_dir=str(tmp_path))
    assert any(Path(tmp_path).iterdir())
