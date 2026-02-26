from pathlib import Path
import requests
from typing import Dict


DATASETS: Dict[str, str] = {
    "forest_area_change": "https://ourworldindata.org/grapher/annual-change-forest-area.csv",
    "annual_deforestation": "https://ourworldindata.org/grapher/annual-deforestation.csv",
    "land_protected": "https://ourworldindata.org/grapher/share-of-land-area-protected.csv",
    "land_degraded": "https://ourworldindata.org/grapher/share-of-land-degraded.csv",
    "mountain_ecosystems": "https://ourworldindata.org/grapher/mountain-ecosystems-protected.csv",
    "world_map": "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip",
}


def download_datasets(download_dir: str = "downloads") -> None:
    """
    Download all required datasets into the specified directory.

    Parameters
    ----------
    download_dir : str
        Directory where datasets will be stored.

    Raises
    ------
    requests.HTTPError
        If a dataset cannot be downloaded.
    """

    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    for name, url in DATASETS.items():
        file_extension = ".zip" if url.endswith(".zip") else ".csv"
        file_path = download_path / f"{name}{file_extension}"

        # Skip download if file already exists (idempotency!)
        if file_path.exists():
            continue

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(file_path, "wb") as file:
            file.write(response.content)