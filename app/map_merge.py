# Before we can merge the datasets, we need to clean them. This function will be called for each dataset after it is downloaded and before it is merged. It will ensure that the datasets have a consistent format and only contain the necessary columns for merging.
from __future__ import annotations

from functools import reduce

import geopandas as gpd
import pandas as pd

def clean_datasets(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    df = df.copy()

    df = df.dropna(subset=["Code"])
    df["Code"] = df["Code"].astype(str)

    df = df[
        (df["Code"].str.len() == 3) &
        (~df["Code"].str.startswith("OWID_"))
    ]

    indicator_cols = [
        c for c in df.columns
        if c not in ("Entity", "Code", "Year")
    ]

    if len(indicator_cols) != 1:
        raise ValueError(
            f"{dataset_name}: Expected exactly one indicator column."
        )

    indicator = indicator_cols[0]

    df = df[["Entity", "Code", "Year", indicator]]

    df = df.rename(columns={indicator: dataset_name})

    return df


# After cleaning, we can merge the datasets. This function will take a dictionary of cleaned datasets and merge them into a single panel dataset. 

def merge_cleaned_datasets(cleaned_datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Outer-join all cleaned datasets on (Code, Year).
    Keeps all years that exist in any dataset.
    Indicator columns will be NaN when not available for a (Code, Year).
    """
    frames = []
    for name, df in cleaned_datasets.items():
        # keep Entity for readability, but we only need one Entity column in the final table
        base_cols = ["Entity", "Code", "Year", name]
        frames.append(df[base_cols].copy())

    def _merge(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        merged = left.merge(right, on=["Code", "Year"], how="outer", suffixes=("", "_r")) #The merge will be an outer join on (Code, Year) to ensure that we keep all years that exist in any dataset. Indicator columns will be NaN when not available for a (Code, Year).
        # If both sides have Entity, keep left Entity, otherwise fill from right
        if "Entity_r" in merged.columns:
            merged["Entity"] = merged["Entity"].fillna(merged["Entity_r"])
            merged = merged.drop(columns=["Entity_r"])
        return merged
    
    panel = reduce(_merge, frames)
    panel = panel.sort_values(["Code", "Year"]).reset_index(drop=True)
    return panel
    

# Define the final function to merge the map with the panel dataset. This function will take the cleaned panel dataset and the world map dataset and merge them on the country code.
def merge_map_with_panel(
    world: gpd.GeoDataFrame,
    panel_df: pd.DataFrame,
    map_key: str = "ISO_A3",  # After testing, we found that the ISO_A3 column in the world map dataset contains the 3-letter country codes that match the "Code" column in our panel dataset the most, so we will use that as the default map_key for merging.
) -> gpd.GeoDataFrame:

    # Validate required structure (fail fast with a clear error message).
    required_cols = {"Code", "Year"}
    missing_cols = required_cols - set(panel_df.columns)
    if missing_cols:
        raise ValueError(f"panel_df missing required columns: {sorted(missing_cols)}")

    if map_key not in world.columns:
        raise KeyError(f"world does not contain map_key column '{map_key}'")

    # Work on copies to keep function safer to reuse and easier to test.
    world_copy = world.copy()
    panel_copy = panel_df.copy()

    # Normalize join key types to ensure consistent matching during merge.
    world_copy[map_key] = world_copy[map_key].astype(str)
    panel_copy["Code"] = panel_copy["Code"].astype(str)

    # Normalize known Natural Earth placeholder codes or NaN placeholders (e.g. '-99') to ensure they don't interfere with merges.
    world_copy.loc[world_copy[map_key] == "-99", map_key] = pd.NA

    # Merge with the map on the left to preserve geometries.
    merged = world_copy.merge(
        panel_copy,
        how="left",
        left_on=map_key,  # Represents the column "ISO_A3" from the map
        right_on="Code",
    )

    # Ensure the result is a GeoDataFrame with correct geometry.
    return gpd.GeoDataFrame(merged, geometry="geometry", crs=world.crs)


