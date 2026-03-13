COLORSCALES = {
    "annual_deforestation": "YlOrRd",
    "land_degraded":        "YlOrRd",
    "land_protected":       "Greens",
    "mountain_ecosystems":  "Greens",
    "forest_area_change":   "RdYlGn",
}
DEFAULT_COLORSCALE = "Blues"

# Builds the Plotly chart figure (histograms or top/bottom rankings) for the selected indicator to be used in the Streamlit app

import pandas as pd
import plotly.express as px


DISPLAY_TITLES = {
    "land_protected": "Share of Protected Land",
    "annual_deforestation": "Annual Deforestation",
    "mountain_ecosystems": "Protected Mountain Biodiversity",
    "forest_area_change": "Change in Forest Area",
    "land_degraded": "Share of Degraded Land",
}

UNITS = {
    "land_protected": "%",
    "land_degraded": "%",
    "mountain_ecosystems": "%",
    "annual_deforestation": "ha",
    "forest_area_change": "ha",
}

# Convert internal indicator key into a nice label
def nice_label(indicator_key: str) -> str:
    return DISPLAY_TITLES.get(indicator_key, indicator_key.replace("_", " ").title())

# Return the unit for a given indicator (or empty string if not defined)
def get_unit(indicator_key: str) -> str:
    return UNITS.get(indicator_key, "")

# Shared chart styling
def apply_chart_layout(fig):
    fig.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="black",
        dragmode=False,
    )
    return fig

# Build the chart figure for the selected indicator
def build_chart_figure(df_all: pd.DataFrame, selected_indicator: str, selected_year: int):
    # Normalize country name column to "Entity"
    if "Entity" not in df_all.columns:
        name_col = next((c for c in ["ADMIN", "NAME", "name"] if c in df_all.columns), None)
        if name_col:
            df_all = df_all.rename(columns={name_col: "Entity"})

    if df_all is None or df_all.empty:
        return None, "No data available for the graph."

    if selected_indicator not in df_all.columns:
        return None, "No data available for the graph."

    # Work on a copy and force the selected indicator to numeric (invalid values become NaN)
    df_all = df_all.copy()
    df_all[selected_indicator] = pd.to_numeric(df_all[selected_indicator], errors="coerce")

    # 1) Land protected and mountain ecosystems: distribution histogram (10% bins)
    if selected_indicator in ["land_protected", "mountain_ecosystems"]:
        title = f"Distribution of Countries by Range"

        # Keep only valid percentage values (0–100) and stop early if there is nothing to plot
        vals = df_all[selected_indicator].dropna().clip(0, 100)
        if vals.empty:
            return None, "No data available for histogram."

        # Create bins: 0–10, 10–20, ..., 90–100
        bins = list(range(0, 110, 10))

        # Create clean labels for each bin
        labels = [f"[{bins[i]}, {bins[i+1]}]" for i in range(len(bins) - 1)]

        # Bin each value into the labeled ranges and count how many countries fall into each bin
        cats = pd.cut(vals, bins=bins, labels=labels, include_lowest=True)
        counts = cats.value_counts().reindex(labels, fill_value=0)

        # Convert counts to percentages
        pct = (counts / counts.sum() * 100).round(1)

        # Build a table for Plotly
        hist_df = pd.DataFrame({
            "Range": labels,
            "% of countries": pct.values,
            "Countries (count)": counts.values,
        })

        # Color scaling: map bins relative to the maximum value in this year
        bin_mid = pd.Series([5, 15, 25, 35, 45, 55, 65, 75, 85, 95])
        max_val = max(float(vals.max()), 1e-9)
        hist_df["bin_scaled"] = (bin_mid / max_val).clip(0, 1)

        # Create a bar chart
        fig = px.bar(
            hist_df,
            x="Range",
            y="% of countries",
            color="bin_scaled",
            color_continuous_scale=COLORSCALES.get(selected_indicator, DEFAULT_COLORSCALE),
            custom_data=["Range", "% of countries", "Countries (count)"],
        )

        apply_chart_layout(fig)

        # Set axis titles
        fig.update_xaxes(
            title=f"Ranges of {nice_label(selected_indicator)} (%)",
            title_standoff=10,
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
        )
        fig.update_yaxes(
            title="% of countries",
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
        )

        # Customize hover text
        fig.update_traces(
            hovertemplate=(
                "<b>% of countries:</b> %{customdata[1]:.1f}%<br>"
                "Countries (count): %{customdata[2]}<br>"
                "Range: %{customdata[0]}<extra></extra>"
            )
        )
        return fig, title

    # 2) Deforestation: magnitude bins histogram
    if selected_indicator == "annual_deforestation":
        title = f"Distribution of Countries by Range"

        # Keep only non-missing deforestation values
        vals = df_all[selected_indicator].dropna()
        if vals.empty:
            return None, "No data available for histogram."

        # Define magnitude bins (in hectares) and labels for the distribution
        bins = [-0.1, 1_000, 10_000, 100_000, 1_000_000, float("inf")]
        labels = ["0–1k", "1k–10k", "10k–100k", "100k–1M", ">1M"]

        # Assign each country to a bin, count countries per bin, and convert counts to percentages
        cats = pd.cut(vals, bins=bins, labels=labels)
        counts = cats.value_counts().reindex(labels, fill_value=0)
        pct = (counts / counts.sum() * 100).round(1)

        # Build a table for Plotly
        hist_df = pd.DataFrame({
            "Range": labels,
            "% of countries": pct.values,
            "Countries (count)": counts.values,
        })

        # Simple increasing color level for the bins
        hist_df["bin_level"] = list(range(1, len(labels) + 1))

        # Create the bar chart
        fig = px.bar(
            hist_df,
            x="Range",
            y="% of countries",
            color="bin_level",
            color_continuous_scale=COLORSCALES.get(selected_indicator, DEFAULT_COLORSCALE),
            custom_data=["Range", "% of countries", "Countries (count)"],
        )

        apply_chart_layout(fig)

        # Set axis titles
        fig.update_xaxes(
            title=f"Ranges of {nice_label(selected_indicator)} (ha)",
            title_standoff=10,
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
        )
        fig.update_yaxes(
            title="% of countries",
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
        )

        # Customize hover text
        fig.update_traces(
            hovertemplate=(
                "<b>% of countries:</b> %{customdata[1]:.1f}%<br>"
                "Countries (count): %{customdata[2]}<br>"
                "Range: %{customdata[0]}<extra></extra>"
            )
        )
        return fig, title

    # 3) Forest area change: top 5 & bottom 5
    if selected_indicator == "forest_area_change":
        title = f"Top 5 & Bottom 5 Countries"

        # Drop rows with missing values
        tmp = df_all.dropna(subset=[selected_indicator])

        # Take the top 5 and bottom 5 changes
        gains = tmp[tmp[selected_indicator] > 0].nlargest(5, selected_indicator)
        losses = tmp[tmp[selected_indicator] < 0].nsmallest(5, selected_indicator)

        # Combine gains and losses into one table
        plot_df = pd.concat([gains, losses], ignore_index=True)
        if plot_df.empty:
            return None, "No positive/negative values available for this year."

        # Get the unit string
        unit = get_unit(selected_indicator)

        # Label each country as a top 5 or bottom 5, and sort for display
        plot_df["Group"] = plot_df[selected_indicator].apply(lambda x: "Top 5" if x > 0 else "Bottom 5")
        plot_df["value_text"] = plot_df[selected_indicator].apply(lambda v: f"{v:,.0f} {unit}".rstrip())
        plot_df = plot_df.sort_values(selected_indicator, ascending=False)

        # Create the bar chart
        fig = px.bar(
            plot_df,
            x=selected_indicator,
            y="Entity",
            orientation="h",
            color=selected_indicator,
            color_continuous_scale=COLORSCALES.get(selected_indicator, DEFAULT_COLORSCALE),
            category_orders={"Entity": plot_df["Entity"].tolist()},
            custom_data=["Group", "value_text"],
        )

        apply_chart_layout(fig)

        # Set axis titles
        fig.update_xaxes(
            title="Change in Forest Area (ha)",
            zeroline=True,
            tickformat=".2s",
            title_standoff=10,
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
        )
        fig.update_yaxes(
            title="",
            tickfont=dict(color="black"),
            title_font=dict(color="black"),
        )

        # Customize hover text
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b> (%{customdata[0]})<br>"
                "Change in Forest Area: %{customdata[1]}<extra></extra>"
            )
        )
        return fig, title

    # 4) Degraded land: top 5 and bottom 5
    title = f"Top 5 & Bottom 5 Countries"

    # Drop rows with missing values
    tmp = df_all.dropna(subset=[selected_indicator])
    if tmp.empty:
        return None, "No ranking data available."

    # Take the top 5 and bottom 5
    top = tmp.nlargest(5, selected_indicator)
    bottom = tmp.nsmallest(5, selected_indicator)

    # Choose a stable identifier to avoid duplicates (prefer ISO code when available)
    key = "Code" if "Code" in tmp.columns else "Entity"

    # Avoid overlap (same country showing in both top and bottom)
    bottom = bottom[~bottom[key].isin(top[key])]

    # Combine top and bottom into one dataframe
    plot_df = (
        pd.concat([top, bottom], ignore_index=True)
        .drop_duplicates(subset=[key], keep="first")
        .sort_values(selected_indicator, ascending=False)
    )

    # Mark each row as top 5 or bottom 5
    top_keys = set(top[key].tolist())
    plot_df["Group"] = plot_df[key].apply(lambda v: "Top 5" if v in top_keys else "Bottom 5")

    # Get the unit and pre-format values for hover text
    unit = get_unit(selected_indicator)
    plot_df["value_text"] = plot_df[selected_indicator].apply(lambda v: f"{v:.1f}{unit}" if unit else f"{v:.1f}")

    # Build an x-axis label, including the unit in parentheses
    x_label = f"{nice_label(selected_indicator)} ({unit})" if unit else nice_label(selected_indicator)

    # Create the bar chart
    fig = px.bar(
        plot_df,
        x=selected_indicator,
        y="Entity",
        orientation="h",
        color=selected_indicator,
        color_continuous_scale=COLORSCALES.get(selected_indicator, DEFAULT_COLORSCALE),
        category_orders={"Entity": plot_df["Entity"].tolist()},
        custom_data=["Group", "value_text"],
    )

    apply_chart_layout(fig)

    # Set axis titles
    fig.update_xaxes(
        title=x_label,
        tickformat=".2s",
        title_standoff=10,
        tickfont=dict(color="black"),
        title_font=dict(color="black"),
    )
    fig.update_yaxes(
        title="",
        tickfont=dict(color="black"),
        title_font=dict(color="black"),
    )

    # Customize hover text
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b> (%{customdata[0]})<br>"
            f"{nice_label(selected_indicator)}: %{{customdata[1]}}<extra></extra>"
        )
    )
    return fig, title