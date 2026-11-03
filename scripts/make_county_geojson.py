"""Build data/counties_2023.geojson from the Census 2023 cartographic boundary file.

Why: Plotly's sample county map predates Connecticut's 2022 switch to planning
regions, so CT would be blank on a 2022-2024 map. The 2023 Census file has them.

Usage (one time; needs `pip install pyshp`):
    curl -LO https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip
    unzip cb_2023_us_county_20m.zip -d cb_2023
    python scripts/make_county_geojson.py cb_2023/cb_2023_us_county_20m data/counties_2023.geojson
"""
import json
import sys

import shapefile  # the pyshp package


def round_coords(c):
    """Round coordinates to 4 decimals (about 10 meters) to keep the file small."""
    if isinstance(c[0], (list, tuple)):
        return [round_coords(x) for x in c]
    return [round(c[0], 4), round(c[1], 4)]


def main(src, out):
    reader = shapefile.Reader(src)
    features = []
    for sr in reader.iterShapeRecords():
        rec = sr.record.as_dict()
        geom = sr.shape.__geo_interface__
        features.append({
            "type": "Feature",
            "id": rec["GEOID"],  # 5-digit county FIPS, matches our fips column
            "properties": {"name": rec["NAME"], "state": rec["STUSPS"]},
            "geometry": {"type": geom["type"], "coordinates": round_coords(geom["coordinates"])},
        })
    with open(out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))
    print(f"Wrote {len(features)} counties to {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
