
from __future__ import annotations
 
from pathlib import Path
from typing import Dict, List
 
import pandas as pd
import geopandas as gpd
 
from app.data_download import download_datasets
from app.map_merge import (
    clean_datasets,
    merge_cleaned_datasets,
    add_iso_a3_clean,
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
 
        # Step 6 — Add cleaned ISO key for reliable merging
        self.world = add_iso_a3_clean(self.world)
 
        # Step 7 — Merge map with panel
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
 
    def get_available_years(self, indicator: str) -> List[int]:
        if indicator not in self.panel_df.columns:
            return []
 
        years = (
            self.panel_df.loc[
                self.panel_df[indicator].notna(),
                "Year"
            ]
            .unique()
        )
 
        return sorted(years)
 
    def get_geodata(self, indicator: str, year: int) -> gpd.GeoDataFrame:
        # Always start from the full world map so every country is drawn,
        # even those with no data for the selected year (they appear as grey).
        world = self.world.copy()
 
        if indicator not in self.panel_df.columns:
            return world
 
        # Pull only the rows for this year from the panel
        year_df = self.panel_df[self.panel_df["Year"] == year][["Code", indicator]].copy()
 
        # Left-join onto the world map so countries with no data stay as NaN
        merged = world.merge(year_df, how="left", left_on="ISO_A3_CLEAN", right_on="Code")
 
        return gpd.GeoDataFrame(merged, geometry="geometry", crs=world.crs)
    
if __name__ == "__main__":
    env = EnvironmentalData()
 
    print("Available indicators:")
    print(env.get_available_indicators())
 
    print("\nGeo panel preview:")
    print(env.get_geo_data().head())