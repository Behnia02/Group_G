import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from app.map_merge import (
    clean_datasets,
    merge_cleaned_datasets,
    merge_map_with_panel,
)


def test_clean_datasets_basic():
    df = pd.DataFrame({
        "Entity": ["Germany"],
        "Code": ["DEU"],
        "Year": [2020],
        "Indicator": [5.0],
    })

    cleaned = clean_datasets(df, dataset_name="indicator")

    assert "indicator" in cleaned.columns
    assert cleaned.shape[0] == 1
    assert cleaned["Code"].iloc[0] == "DEU"


def test_merge_cleaned_datasets_basic():
    df1 = pd.DataFrame({
        "Entity": ["Germany"],
        "Code": ["DEU"],
        "Year": [2020],
        "value1": [1.0],
    })

    df2 = pd.DataFrame({
        "Entity": ["Germany"],
        "Code": ["DEU"],
        "Year": [2020],
        "value2": [2.0],
    })

    merged = merge_cleaned_datasets({
        "value1": df1,
        "value2": df2,
    })

    assert "value1" in merged.columns
    assert "value2" in merged.columns
    assert merged.shape[0] == 1


def test_merge_map_with_panel_basic():
    world = gpd.GeoDataFrame(
        {
            "ISO_A3_CLEAN": ["DEU"],
            "geometry": [Point(10, 50)],
        },
        crs="EPSG:4326",
    )

    panel = pd.DataFrame({
        "Entity": ["Germany"],
        "Code": ["DEU"],
        "Year": [2020],
        "value": [5.0],
    })

    merged = merge_map_with_panel(world, panel)

    assert isinstance(merged, gpd.GeoDataFrame)
    assert "value" in merged.columns
    assert merged.shape[0] == 1