
import os
import getpass
from pathlib import Path

import earthaccess

# ---------------------------------------
# CONFIGURATION
# ---------------------------------------

OUTPUT_DIR = Path("raw_nc4")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATASET = "M2TMNXOCN"
VERSION = "5.12.4"

START_YEAR = 1997
END_YEAR = 2026

# ---------------------------------------
# EARTHDATA AUTHENTICATION
# ---------------------------------------

token = getpass.getpass("Enter your NASA Earthdata token: ")

os.environ.pop("EARTHDATA_USERNAME", None)
os.environ.pop("EARTHDATA_PASSWORD", None)
os.environ["EARTHDATA_TOKEN"] = token

auth = earthaccess.login(strategy="environment")

if not auth.authenticated:
    raise RuntimeError("Earthdata authentication failed.")

print("\nEarthdata authentication successful!")

# ---------------------------------------
# SEARCH AND DOWNLOAD
# ---------------------------------------

for year in range(START_YEAR, END_YEAR + 1):

    start_date = f"{year}-01-01"

    end_date = (
        "2026-09-30"
        if year == 2026
        else f"{year}-12-31"
    )

    print("\n" + "=" * 50)
    print(f"YEAR: {year}")
    print(f"Period: {start_date} to {end_date}")
    print("=" * 50)

    try:
        results = earthaccess.search_data(
            short_name=DATASET,
            version=VERSION,
            temporal=(start_date, end_date)
        )

        print(f"Granules found: {len(results)}")

        if not results:
            print("No granules found for this year.")
            continue

        downloaded = earthaccess.download(
            results,
            local_path=str(OUTPUT_DIR),
            threads=2
        )

        print(f"Download results: {len(downloaded)}")

    except Exception as error:
        print(f"ERROR in {year}: {error}")
        print("Continuing to the next year...")

print("\nDownload process completed.")
print(f"Files are stored in: {OUTPUT_DIR.resolve()}")

