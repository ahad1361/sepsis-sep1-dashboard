"""Data acquisition and processing for SEP-1 CMS hospital quality data."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# ── CMS Provider Data Catalog API (stable dataset ID across quarterly refreshes) ──
CMS_API_BASE = "https://data.cms.gov/provider-data/api/1/datastore/query/yv7e-xc69/0"
PAGE_SIZE = 1000  # this endpoint rejects limit > 1000

# ── Fallback CSV URLs (resource UUIDs rotate quarterly; update if 404) ────────
CMS_TIMELY_CARE_URL = (
    "https://data.cms.gov/provider-data/sites/default/files/resources/"
    "0437b5494ac61507ad90f2af6b8085a7_1777413965/Timely_and_Effective_Care-Hospital.csv"
)
CMS_HOSPITAL_INFO_URL = (
    "https://data.cms.gov/provider-data/sites/default/files/resources/"
    "893c372430d9d71a1c52737d01239d47_1777413958/Hospital_General_Information.csv"
)

# Lat/lon centroids for all US states and territories used as coordinate fallback
STATE_CENTROIDS: dict[str, tuple[float, float]] = {
    "AL": (32.7794, -86.8287), "AK": (64.0685, -153.3696),
    "AZ": (34.2744, -111.6602), "AR": (34.8938, -92.4426),
    "CA": (37.1841, -119.4696), "CO": (38.9972, -105.5478),
    "CT": (41.6219, -72.7273), "DE": (38.9896, -75.5050),
    "FL": (28.6305, -82.4497), "GA": (32.6415, -83.4426),
    "HI": (20.2927, -156.3737), "ID": (44.3509, -114.6130),
    "IL": (40.0417, -89.1965), "IN": (39.8942, -86.2816),
    "IA": (42.0751, -93.4960), "KS": (38.4937, -98.3804),
    "KY": (37.5347, -85.3021), "LA": (31.0689, -91.9968),
    "ME": (45.3695, -69.2428), "MD": (39.0550, -76.7909),
    "MA": (42.2596, -71.8083), "MI": (44.3467, -85.4102),
    "MN": (46.2807, -94.3053), "MS": (32.7364, -89.6678),
    "MO": (38.3566, -92.4580), "MT": (47.0527, -109.6333),
    "NE": (41.5378, -99.7951), "NV": (39.3289, -116.6312),
    "NH": (43.6805, -71.5811), "NJ": (40.1907, -74.6728),
    "NM": (34.4071, -106.1126), "NY": (42.9538, -75.5268),
    "NC": (35.5557, -79.3877), "ND": (47.4501, -100.4659),
    "OH": (40.2862, -82.7937), "OK": (35.5889, -97.4943),
    "OR": (43.9336, -120.5583), "PA": (40.8781, -77.7996),
    "RI": (41.6762, -71.5562), "SC": (33.9169, -80.8964),
    "SD": (44.4443, -100.2263), "TN": (35.8580, -86.3505),
    "TX": (31.4757, -99.3312), "UT": (39.3210, -111.0937),
    "VT": (44.0687, -72.6658), "VA": (37.5215, -78.8537),
    "WA": (47.3826, -120.4472), "WV": (38.6409, -80.6227),
    "WI": (44.6243, -89.9941), "WY": (42.9957, -107.5512),
    "DC": (38.9072, -77.0369), "PR": (18.2208, -66.5901),
    "GU": (13.4443, 144.7937), "VI": (18.3358, -64.8963),
}

_COLUMN_MAP = {
    # CSV title-case names
    "Facility ID": "facility_id",
    "Facility Name": "facility_name",
    "Address": "address",
    "City/Town": "city",
    "City": "city",
    "State": "state",
    "ZIP Code": "zip_code",
    "County/Parish": "county",
    "Phone Number": "phone",
    "Telephone Number": "phone",
    "Measure ID": "measure_id",
    "Measure Name": "measure_name",
    "Condition": "condition",
    "Compared to National": "compared_to_national",
    "Denominator": "denominator",
    "Sample": "denominator",
    "Score": "score",
    "Footnote": "footnote",
    "Start Date": "start_date",
    "End Date": "end_date",
    "Location": "location",
    "Lat": "lat",
    "Lng": "lng",
    "Long": "lng",
    "Longitude": "lng",
    "Latitude": "lat",
    # API snake_case names that differ from our target schema
    "citytown": "city",
    "countyparish": "county",
    "telephone_number": "phone",
    "_condition": "condition",
    "sample": "denominator",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename CMS CSV title-case columns to snake_case."""
    return df.rename(columns={k: v for k, v in _COLUMN_MAP.items() if k in df.columns})


def fetch_sep1_from_api() -> pd.DataFrame:
    """Fetch all SEP_1 rows from the CMS Provider Data Catalog API.

    Uses server-side filtering and auto-paginates in PAGE_SIZE chunks.
    Falls back to unfiltered pull + local filter if server-side conditions
    are rejected (some CMS endpoints ignore the conditions param).

    Returns:
        Raw DataFrame of SEP_1 records with the same column structure as the CSV.

    Raises:
        RuntimeError: If the API is unreachable or returns no SEP_1 rows.
    """
    def _get_page(offset: int) -> tuple[list[dict], int]:
        # Pass conditions as dict keys containing brackets — requests encodes
        # '=' (the operator value) as %3D which the CMS endpoint requires.
        # Passing a pre-built URL string leaves '=' un-encoded → 400.
        params = {
            "limit": PAGE_SIZE,
            "offset": offset,
            "conditions[0][property]": "measure_id",
            "conditions[0][value]": "SEP_1",
            "conditions[0][operator]": "=",
        }
        try:
            resp = requests.get(CMS_API_BASE, params=params, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"CMS API request failed: {exc}") from exc
        payload = resp.json()
        rows = payload.get("results") or payload.get("data") or []
        total = payload.get("count", 0)
        return rows, total

    all_rows: list[dict] = []
    offset = 0
    rows, total = _get_page(offset)
    if not rows:
        raise RuntimeError("CMS API returned no SEP_1 rows.")
    all_rows.extend(rows)
    logger.info("API: %d total SEP_1 rows reported by server", total)

    while len(rows) == PAGE_SIZE:
        offset += PAGE_SIZE
        rows, _ = _get_page(offset)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    if df.empty:
        raise RuntimeError("No SEP_1 records found in API response.")

    logger.info("API fetched %d SEP_1 rows", len(df))
    return df


def download_file(url: str, local_path: Path, timeout: int = 120) -> bool:
    """Download a remote file, saving it to *local_path*.

    Args:
        url: Source URL.
        local_path: Destination path (parent directory is created if needed).
        timeout: HTTP timeout in seconds.

    Returns:
        True on success, False on any network or HTTP error.
    """
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading %s", url)
        with requests.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=65_536):
                    fh.write(chunk)
        logger.info("Saved → %s", local_path)
        return True
    except requests.RequestException as exc:
        logger.error("Download failed: %s", exc)
        return False


def load_timely_care_data(force_refresh: bool = False) -> pd.DataFrame:
    """Load the CMS 'Timely and Effective Care – Hospital' CSV.

    Downloads from CMS on first call; subsequent calls use the cached file.

    Args:
        force_refresh: Re-download even if a local cache exists.

    Returns:
        Raw DataFrame (all measures, all hospitals).

    Raises:
        RuntimeError: If the file cannot be downloaded and no cache exists.
    """
    local_path = DATA_DIR / "Timely_and_Effective_Care-Hospital.csv"
    if force_refresh or not local_path.exists():
        ok = download_file(CMS_TIMELY_CARE_URL, local_path)
        if not ok:
            if local_path.exists():
                logger.warning("Download failed — using existing cache.")
            else:
                raise RuntimeError(
                    "Cannot download CMS data and no local cache exists.\n"
                    f"Manual download URL: {CMS_TIMELY_CARE_URL}\n"
                    f"Save the file to: {local_path}"
                )
    df = pd.read_csv(local_path, dtype=str, low_memory=False)
    return _normalize_columns(df)


def load_hospital_info(force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """Load CMS Hospital General Information (includes lat/lon coordinates).

    Args:
        force_refresh: Re-download even if a local cache exists.

    Returns:
        DataFrame with hospital info, or None if unavailable.
    """
    local_path = DATA_DIR / "Hospital_General_Information.csv"
    if force_refresh or not local_path.exists():
        ok = download_file(CMS_HOSPITAL_INFO_URL, local_path)
        if not ok:
            logger.warning("Hospital General Information unavailable — map will use state centroids.")
            return None
    try:
        df = pd.read_csv(local_path, dtype=str, low_memory=False)
        return _normalize_columns(df)
    except Exception as exc:
        logger.warning("Could not parse Hospital General Information: %s", exc)
        return None


def _parse_score(val: object) -> Optional[float]:
    """Convert a raw CMS score string to float, returning None for suppressed values."""
    if pd.isna(val):
        return None
    cleaned = str(val).strip().lower()
    if cleaned in {"not available", "n/a", "", "nan", "not applicable"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_coordinates(hospital_info: pd.DataFrame) -> pd.DataFrame:
    """Pull facility_id → (lat, lng) from the hospital info DataFrame."""
    result = hospital_info[["facility_id"]].copy()

    if "lat" in hospital_info.columns and "lng" in hospital_info.columns:
        result["lat"] = pd.to_numeric(hospital_info["lat"], errors="coerce")
        result["lng"] = pd.to_numeric(hospital_info["lng"], errors="coerce")
        return result

    if "location" in hospital_info.columns:
        def _parse_point(loc: object) -> tuple[Optional[float], Optional[float]]:
            if pd.isna(loc):
                return None, None
            s = str(loc)
            # WKT POINT(-lon lat)
            m = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", s)
            if m:
                return float(m.group(2)), float(m.group(1))
            # (lat, lon) tuple notation
            m = re.search(r"\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", s)
            if m:
                return float(m.group(1)), float(m.group(2))
            return None, None

        coords = hospital_info["location"].apply(_parse_point)
        result["lat"] = coords.apply(lambda t: t[0])
        result["lng"] = coords.apply(lambda t: t[1])
        return result

    return result


def _categorize_score(score: Optional[float]) -> str:
    """Map a numeric SEP-1 score to a compliance tier label."""
    if score is None or pd.isna(score):
        return "No Data"
    if score >= 80:
        return "Excellent (≥80%)"
    if score >= 50:
        return "Moderate (50–79%)"
    return "Poor (<50%)"


def process_sep1_data(
    timely_df: pd.DataFrame,
    hospital_info: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Filter the timely care dataset to SEP_1 and enrich with coordinates.

    Args:
        timely_df: Raw CMS timely care DataFrame (all measures).
        hospital_info: Optional hospital info for geocoding.

    Returns:
        Cleaned, geocoded DataFrame of SEP_1 records.

    Raises:
        ValueError: If no SEP_1 records are found.
    """
    measure_col = timely_df.get("measure_id", pd.Series(dtype=str))
    mask = measure_col.str.strip().str.upper() == "SEP_1"
    df = timely_df[mask].copy()

    if df.empty:
        raise ValueError(
            "No SEP_1 records found. "
            "The CMS measure ID may have changed — check the dataset directly."
        )

    df["score"] = df["score"].apply(_parse_score)
    df["denominator"] = pd.to_numeric(
        df.get("denominator", pd.Series(dtype=str)), errors="coerce"
    )

    if "state" in df.columns:
        df["state"] = df["state"].str.strip().str.upper()
        df = df[df["state"].isin(set(STATE_CENTROIDS.keys()) | {"AS", "MP"})]

    # Attach coordinates from hospital info if available
    if hospital_info is not None:
        coord_df = _extract_coordinates(hospital_info)
        df = df.merge(coord_df, on="facility_id", how="left")

    if "lat" not in df.columns:
        df["lat"] = np.nan
        df["lng"] = np.nan

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")

    # Fill missing coordinates with state centroid + small random jitter
    missing = df["lat"].isna()
    if missing.any() and "state" in df.columns:
        rng = np.random.default_rng(42)
        n = int(missing.sum())
        df.loc[missing, "lat"] = (
            df.loc[missing, "state"].map(lambda s: STATE_CENTROIDS.get(s, (np.nan, np.nan))[0])
            + rng.uniform(-1.2, 1.2, n)
        )
        df.loc[missing, "lng"] = (
            df.loc[missing, "state"].map(lambda s: STATE_CENTROIDS.get(s, (np.nan, np.nan))[1])
            + rng.uniform(-1.2, 1.2, n)
        )

    df["coords_approximated"] = missing
    df["score_category"] = df["score"].apply(_categorize_score)

    return df.reset_index(drop=True)


def get_state_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate mean SEP-1 score and reporting hospital count by state.

    Args:
        df: Hospital-level SEP_1 DataFrame.

    Returns:
        DataFrame with columns: state, avg_score, hospital_count — sorted descending.
    """
    scored = df[df["score"].notna()]
    state_df = (
        scored.groupby("state")
        .agg(avg_score=("score", "mean"), hospital_count=("facility_id", "count"))
        .reset_index()
    )
    state_df["avg_score"] = state_df["avg_score"].round(1)
    return state_df.sort_values("avg_score", ascending=False).reset_index(drop=True)


def get_national_stats(df: pd.DataFrame) -> dict:
    """Compute national-level KPI statistics.

    Args:
        df: Hospital-level SEP_1 DataFrame.

    Returns:
        Dict with keys: national_avg, total_hospitals, reporting_hospitals,
        best_state, worst_state, best_score, worst_score.
    """
    scored = df[df["score"].notna()]
    state_avgs = get_state_averages(df)

    return {
        "national_avg": round(scored["score"].mean(), 1) if not scored.empty else 0.0,
        "total_hospitals": len(df),
        "reporting_hospitals": len(scored),
        "best_state": state_avgs.iloc[0]["state"] if not state_avgs.empty else "N/A",
        "worst_state": state_avgs.iloc[-1]["state"] if not state_avgs.empty else "N/A",
        "best_score": state_avgs.iloc[0]["avg_score"] if not state_avgs.empty else 0.0,
        "worst_score": state_avgs.iloc[-1]["avg_score"] if not state_avgs.empty else 0.0,
    }


def load_sep1_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top-level entry point: fetch, process, and return SEP-1 data.

    Tries the live CMS API first (stable dataset ID, always current).
    Falls back to the local cached CSV if the API is unreachable.

    Returns:
        (hospital_df, state_df) where hospital_df is one row per hospital
        and state_df contains state-level aggregates.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    hospital_info = load_hospital_info()

    # Primary: live CMS API (dataset ID yv7e-xc69 is stable across quarterly refreshes)
    try:
        raw_df = fetch_sep1_from_api()
        raw_df = _normalize_columns(raw_df)
    except Exception as api_exc:
        logger.warning("CMS API unavailable (%s) — falling back to local CSV.", api_exc)
        raw_df = load_timely_care_data()

    hospital_df = process_sep1_data(raw_df, hospital_info)
    state_df = get_state_averages(hospital_df)
    return hospital_df, state_df
