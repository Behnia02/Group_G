
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
import geopandas as gpd

from app.data_download import download_datasets
from app.map_merge import (
    clean_datasets,
    merge_cleaned_datasets,
    merge_map_with_panel,
)


class EnvironmentalData:
    """
    Main class responsible for handling all datasets
    in Project Okavango.
    """

    def __init__(self, download_dir: str = "downloads") -> None:
        """
        Full pipeline:
        1. Download datasets
        2. Load raw datasets
        3. Clean datasets
        4. Build panel dataset
        5. Merge with world map
        """

        self.download_dir: Path = Path(download_dir)

        # Step 1 — Download datasets
        download_datasets(download_dir)

        # Step 2 — Load raw datasets
        self.raw_datasets: Dict[str, pd.DataFrame] = self._load_raw_datasets()

        # Step 3 — Clean datasets
        self.cleaned_datasets: Dict[str, pd.DataFrame] = (
            self._clean_all_datasets()
        )

        # Step 4 — Merge into panel
        self.panel_df: pd.DataFrame = merge_cleaned_datasets(
            self.cleaned_datasets
        )

        # Step 5 — Load world map
        self.world: gpd.GeoDataFrame = self._load_world_map()

        # Step 6 — Merge map with panel
        self.geo_panel: gpd.GeoDataFrame = merge_map_with_panel(
            self.world,
            self.panel_df,
        )

    # -----------------------------
    # Private helpers
    # -----------------------------

    def _load_raw_datasets(self) -> Dict[str, pd.DataFrame]:
        datasets: Dict[str, pd.DataFrame] = {}

        for file in Path(self.download_dir).glob("*.csv"):
            datasets[file.stem] = pd.read_csv(file)

        return datasets

    def _clean_all_datasets(self) -> Dict[str, pd.DataFrame]:
        cleaned: Dict[str, pd.DataFrame] = {}

        for name, df in self.raw_datasets.items():
            cleaned[name] = clean_datasets(df, name)

        return cleaned

    def _load_world_map(self) -> gpd.GeoDataFrame:
        zip_path = Path(self.download_dir) / "world_map.zip"
        return gpd.read_file(zip_path)

    # -----------------------------
    # Public methods (for Streamlit)
    # -----------------------------

    def get_available_indicators(self) -> List[str]:
        return list(self.cleaned_datasets.keys())

    def get_geo_data(self) -> gpd.GeoDataFrame:
        return self.geo_panel

    def filter_by_year(self, year: int) -> gpd.GeoDataFrame:
        return self.geo_panel[self.geo_panel["Year"] == year]

    def get_top_bottom(
        self,
        indicator: str,
        year: int,
        n: int = 5,
    ) -> pd.DataFrame:

        df = self.panel_df[self.panel_df["Year"] == year]

        top = df.nlargest(n, indicator)
        bottom = df.nsmallest(n, indicator)

        return pd.concat([top, bottom])