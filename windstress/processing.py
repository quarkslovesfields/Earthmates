
from pathlib import Path
import re

import numpy as np
import pandas as pd
import xarray as xr


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data" / "raw_nc4"

LAT_MIN = -5.0
LAT_MAX = 5.0

LON_MIN = 120.0
LON_MAX = 240.0

REQUIRED_VARIABLES = ["TAUXWTR", "TAUYWTR"]


# --------------------------------------------------
# FIND THE MONTHLY NETCDF FILE
# --------------------------------------------------

def find_monthly_file(year, month):

    # Expected filename contains YYYYMM, e.g.:
    # MERRA2_400.tavgM_2d_ocn_Nx.199701.nc4

    month_string = f"{year}{month:02d}"

    matches = sorted(
    DATA_DIR.rglob(f"*{month_string}*.nc4")
    )

    if not matches:
        raise FileNotFoundError(
            f"No MERRA-2 file found for {year}-{month:02d}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple files found for {year}-{month:02d}: "
            f"{matches}"
        )

    return matches[0]


# --------------------------------------------------
# LOAD AND PROCESS WIND STRESS
# --------------------------------------------------

def load_wind_stress(start_month, end_month):

    """
    Load MERRA-2 monthly ocean wind stress.

    Parameters
    ----------
    start_month : str
        Starting month in YYYY-MM format.

    end_month : str
        Ending month in YYYY-MM format.

    Returns
    -------
    xarray.Dataset
        TAUXWTR, TAUYWTR, and wind stress magnitude.
    """

    # Validate the requested months
    try:
        start = pd.Period(start_month, freq="M")
        end = pd.Period(end_month, freq="M")

    except Exception as exc:
        raise ValueError(
            "Dates must use YYYY-MM format."
        ) from exc

    if start > end:
        raise ValueError(
            "Starting month cannot be later than ending month."
        )

    months = pd.period_range(start, end, freq="M")

    monthly_data = []

    missing_files = []

    # ----------------------------------------------
    # READ EACH REQUESTED MONTH
    # ----------------------------------------------

    for period in months:

        year = period.year
        month = period.month

        try:
            filepath = find_monthly_file(year, month)

        except FileNotFoundError:
            missing_files.append(str(period))
            continue

        print(f"Reading: {filepath.name}")

        with xr.open_dataset(filepath) as source:

            # Check required variables
            missing_variables = [
                variable
                for variable in REQUIRED_VARIABLES
                if variable not in source.data_vars
            ]

            if missing_variables:
                raise KeyError(
                    f"{filepath.name} is missing variables: "
                    f"{missing_variables}"
                )

            # Check coordinates
            if "lat" not in source.coords or "lon" not in source.coords:
                raise ValueError(
                    f"Latitude/longitude coordinates not found "
                    f"in {filepath.name}."
                )

            # Normalize longitude to 0-360
            data = source[
                REQUIRED_VARIABLES
            ].assign_coords(
                lon=source.lon % 360
            ).sortby("lon")

            # Ensure latitude is ascending
            data = data.sortby("lat")

            # Extract the equatorial Pacific
            regional_data = data.sel(
                lat=slice(LAT_MIN, LAT_MAX),
                lon=slice(LON_MIN, LON_MAX)
            ).load()

            if regional_data.sizes.get("lat", 0) == 0:
                raise ValueError(
                    f"No latitude points found in {filepath.name}."
                )

            if regional_data.sizes.get("lon", 0) == 0:
                raise ValueError(
                    f"No longitude points found in {filepath.name}."
                )

            monthly_data.append(regional_data)

    # ----------------------------------------------
    # CHECK MISSING MONTHS
    # ----------------------------------------------

    if missing_files:

        raise FileNotFoundError(
            "The following monthly datasets are missing:\n"
            + ", ".join(missing_files)
        )

    if not monthly_data:
        raise ValueError("No monthly datasets were loaded.")

    # ----------------------------------------------
    # COMBINE MONTHLY DATA
    # ----------------------------------------------

    combined = xr.concat(
        monthly_data,
        dim="time"
    ).sortby("time")

    # ----------------------------------------------
    # CALCULATE RESULTANT WIND STRESS
    # ----------------------------------------------

    combined["WIND_STRESS_MAGNITUDE"] = np.sqrt(
        combined["TAUXWTR"] ** 2
        + combined["TAUYWTR"] ** 2
    )

    combined["WIND_STRESS_MAGNITUDE"].attrs = {
        "long_name": "Resultant surface wind stress magnitude",
        "units": "N m-2"
    }

    # ----------------------------------------------
    # RETURN DATA
    # ----------------------------------------------

    return combined

# ------------------------------
# PLOT THE DATA
# ------------------------------


import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


def plot_wind_stress_map(data):
    """
    Generate a spatial map of mean wind stress magnitude.
    """

    # Calculate the temporal mean
    mean_stress = data["WIND_STRESS_MAGNITUDE"].mean(dim="time")

    # Extract coordinates
    lon = data["lon"].values
    lat = data["lat"].values

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot spatial distribution
    mesh = ax.pcolormesh(
        lon,
        lat,
        mean_stress.values,
        shading="auto",
        cmap="viridis"
    )

    # Add colorbar
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("Wind Stress Magnitude (N/m²)")

    # Labels and title
    ax.set_title("Mean Surface Wind Stress Magnitude")
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")

    ax.set_xlim(120, 240)
    ax.set_ylim(-5, 5)

    ax.grid(alpha=0.3)

    fig.tight_layout()

    return fig

# ----------------------------
# TIME-SERIES PLOTTING
# ----------------------------


def plot_wind_stress_timeseries(data):
    """
    Generate a time-series plot of spatially averaged
    wind stress magnitude.
    """

    # Calculate spatial mean for each month
    monthly_mean = data["WIND_STRESS_MAGNITUDE"].mean(
        dim=["lat", "lon"]
    )

    # Extract time and values
    time = data["time"].values
    values = monthly_mean.values

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 5))

    # Plot time series
    ax.plot(
        time,
        values,
        marker="o",
        linewidth=1.5
    )

    # Labels and title
    ax.set_title("Monthly Mean Surface Wind Stress")
    ax.set_xlabel("Time")
    ax.set_ylabel("Wind Stress Magnitude (N/m²)")

    ax.grid(alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

