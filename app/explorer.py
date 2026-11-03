"""County Explorer: compare a county's Medicare spending with the counties most like it.

Run locally from the project folder:
    streamlit run app/explorer.py

Data comes from app/data/*.parquet, written by notebooks/05_export_app_data.ipynb.

The county, year, and number of similar counties are kept in the URL, so any view can be
shared or linked, e.g. ?county=Los+Angeles%2C+CA&year=2022&k=5
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "data"
SITE_URL = "https://gstenberg.org/medicare/"
REPO_URL = "https://github.com/Stenberg1/medicare-county-spending"
DEFAULT_FIPS = "13201"  # Miller County, GA (the outlier discussed in the write-up)

# Matching variables: z-scores computed within each year in notebook 05. Spending is never used.
ZCOLS = ["z_income", "z_poverty", "z_age", "z_dual", "z_ma", "z_rucc"]

CATEGORIES = {  # column -> label, in display order
    "snf": "Skilled nursing facility",
    "ip": "Inpatient hospital",
    "op": "Outpatient hospital",
    "physician": "Physician visits",
    "procedures": "Procedures",
    "tests": "Tests",
    "imaging": "Imaging",
    "hh": "Home health",
    "hospice": "Hospice",
    "other": "All other services",
}

# Colors and type, shared with the website charts (notebooks/plot_style.py).
COUNTY = "#2a78d6"   # the selected county
PEERS = "#eb6834"    # similar counties, as a group
US = "#898781"       # national average
PEER_BAR = "#cfcdc6" # individual similar counties in the ranked chart
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

st.set_page_config(page_title="County Explorer | Medicare Spending", page_icon="🗺️", layout="centered")


# ------------------------------------------------------------------ data
@st.cache_data
def load():
    counties = duckdb.sql(f"SELECT * FROM '{DATA / 'counties.parquet'}'").df()
    national = duckdb.sql(f"SELECT * FROM '{DATA / 'national.parquet'}'").df().set_index("year")
    return counties, national


def find_peers(year_df, fips, k):
    """The k matchable counties closest to `fips` on the six z-scores (Euclidean distance)."""
    pool = year_df[year_df["matchable"]]
    target = pool.loc[pool["fips"] == fips, ZCOLS].to_numpy()[0]
    dist = np.sqrt(((pool[ZCOLS].to_numpy() - target) ** 2).sum(axis=1))
    return pool.assign(distance=dist).query("fips != @fips").nsmallest(k, "distance")


def money(x):
    return "n/a" if pd.isna(x) else f"${x:,.0f}"


def md_money(x):
    """money() for st.markdown text. Two plain "$" in one block render as a LaTeX formula, so escape them."""
    return money(x).replace("$", "\\$")


def base_layout(fig, height):
    fig.update_layout(
        height=height, margin=dict(l=10, r=20, t=40, b=10),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=INK_2),
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", title=None),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED), automargin=True)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED), automargin=True)
    return fig


def show(fig):
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})


counties, national = load()

# ------------------------------------------------------------------ header and controls
st.title("County Explorer")
st.markdown(
    "Pick a county to compare its Medicare spending per beneficiary with the counties most like it "
    f"in income, poverty, age, Medicaid enrollment, Medicare Advantage use, and rurality. "
    f"Part of [Medicare Spending Across US Counties]({SITE_URL})."
)

years = sorted(counties["year"].unique().tolist(), reverse=True)
c1, c2, c3 = st.columns([3, 1, 1])
with c2:
    year = st.selectbox("Year", years, index=0, key="year", bind="query-params")

year_df = counties[counties["year"] == year].sort_values(["state", "name"]).reset_index(drop=True)
names = dict(zip(year_df["fips"], year_df["name"]))
options = year_df["fips"].tolist()

with c1:
    fips = st.selectbox(
        "County", options, index=options.index(DEFAULT_FIPS) if DEFAULT_FIPS in options else 0,
        format_func=lambda f: names[f], key="county", bind="query-params",
        help="Type to search. Counties with fewer than 500 Original Medicare beneficiaries are not included.",
    )
with c3:
    k = st.selectbox("Similar counties", [5, 10, 15, 20], index=1, key="k", bind="query-params")

me = year_df.set_index("fips").loc[fips]
us = national.loc[year]

desc = f"{me['rucc_desc']}. " if pd.notna(me["rucc_desc"]) else ""
st.caption(f"{desc}{int(me['benes']):,} Original Medicare beneficiaries in {year}.")

if not me["matchable"]:
    labels = {"median_income": "median income", "poverty_rate": "poverty rate", "avg_age": "average age",
              "dual_pct": "dual-eligible share", "ma_rate": "Medicare Advantage share", "rucc": "rural-urban code"}
    missing = ", ".join(v for c, v in labels.items() if pd.isna(me[c]))
    st.warning(
        f"{me['name']} has no {missing} in {year}, so it can't be matched to similar counties. "
        "(Rural-urban codes come from 2023, so they are missing for Connecticut's old counties before 2022 and "
        "for Valdez-Cordova, AK before its 2019 split.) "
        f"It spent {md_money(me['spend_pc_std'])} per beneficiary, compared with {md_money(us['spend_pc_std'])} nationally."
    )
    st.stop()

peers = find_peers(year_df, fips, k)
peer_median = peers["spend_pc_std"].median()
gap = me["spend_pc_std"] / peer_median - 1

# ------------------------------------------------------------------ headline numbers
m1, m2, m3 = st.columns(3)
m1.metric(f"{me['name']}", money(me["spend_pc_std"]), border=True,
          help="Standardized Medicare spending per Original Medicare beneficiary. Removes geographic price differences.")
m2.metric(f"{k} similar counties (median)", money(peer_median),
          delta=f"{gap:+.0%} difference", delta_color="off", delta_arrow="off", border=True)
m3.metric("US average", money(us["spend_pc_std"]),
          delta=f"{me['spend_pc_std'] / us['spend_pc_std'] - 1:+.0%} difference", delta_color="off",
          delta_arrow="off", border=True)

group = pd.concat([peers, year_df[year_df["fips"] == fips]])
rank = int((group["spend_pc_std"] > me["spend_pc_std"]).sum()) + 1
direction = "more" if gap > 0 else "less"


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


rank_text = ("the highest" if rank == 1 else "the lowest" if rank == len(group)
             else f"the {ordinal(rank)} highest")
st.markdown(
    f"**{me['name']} spends {abs(gap):.0%} {direction} per beneficiary than the median of its {k} most similar "
    f"counties**, and is {rank_text} of the {len(group)} counties in this group."
)

# ------------------------------------------------------------------ chart 1: ranked bars
st.subheader("Compared with similar counties")
ranked = group.sort_values("spend_pc_std")
is_me = ranked["fips"] == fips
fig = go.Figure(go.Bar(
    y=ranked["name"], x=ranked["spend_pc_std"], orientation="h",
    marker_color=np.where(is_me, COUNTY, PEER_BAR),
    text=[money(v) for v in ranked["spend_pc_std"]], textposition="outside", cliponaxis=False,
    textfont=dict(color=INK_2, size=12),
    hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
))
fig.add_vline(x=peer_median, line=dict(color=PEERS, width=2))
fig.add_annotation(x=peer_median, y=1, yref="paper", yanchor="bottom", text="Similar-county median",
                   showarrow=False, font=dict(color=INK_2, size=12), xanchor="left", xshift=4)
fig.update_xaxes(tickprefix="$", tickformat=",.0f", range=[0, ranked["spend_pc_std"].max() * 1.15])  # room for labels
fig.update_yaxes(showgrid=False, tickfont=dict(color=INK_2))
fig.update_layout(bargap=0.25)
show(base_layout(fig, height=110 + 26 * len(ranked)))

# ------------------------------------------------------------------ chart 2: by type of service
st.subheader("Where the difference comes from")
cats = list(CATEGORIES)
by_cat = pd.DataFrame({
    "label": [CATEGORIES[c] for c in cats],
    "county": [me[c] for c in cats],
    "peers": [peers[c].median() for c in cats],
})
by_cat["gap"] = by_cat["county"] - by_cat["peers"]
biggest = by_cat.loc[by_cat["gap"].abs().idxmax()]
st.markdown(
    f"The largest gap is in **{biggest['label'].lower()}**: {md_money(biggest['county'])} per beneficiary in "
    f"{me['name']} vs. {md_money(biggest['peers'])} for the median similar county."
)
fig = go.Figure()
for col, name, color in [("peers", f"Similar counties (median)", PEERS), ("county", me["name"], COUNTY)]:
    fig.add_bar(y=by_cat["label"], x=by_cat[col], name=name, orientation="h", marker_color=color,
                hovertemplate=name + "<br>%{y}: $%{x:,.0f}<extra></extra>")
fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08, legend_traceorder="reversed")
fig.update_xaxes(tickprefix="$", tickformat=",.0f")
fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK_2))
show(base_layout(fig, height=520))
st.caption("Standardized dollars per beneficiary. Medians are taken separately for each type of service, "
           "so they do not add up to the total median. Suppressed small values count as missing.")

# ------------------------------------------------------------------ chart 3: over time
st.subheader("Over time")
peer_fips = set(peers["fips"])
hist = counties[counties["fips"].isin(peer_fips | {fips})]
trend = pd.DataFrame({
    me["name"]: hist[hist["fips"] == fips].set_index("year")["spend_pc_std"],
    "Similar counties (median)": hist[hist["fips"].isin(peer_fips)].groupby("year")["spend_pc_std"].median(),
    "US average": national["spend_pc_std"],
}).sort_index()
fig = go.Figure()
for name, color in [("US average", US), ("Similar counties (median)", PEERS), (me["name"], COUNTY)]:
    s = trend[name].dropna()
    fig.add_scatter(x=s.index, y=s.values, name=name, mode="lines+markers",
                    line=dict(color=color, width=2.5 if name == me["name"] else 2),
                    marker=dict(size=7, line=dict(width=1.5, color=SURFACE)),
                    hovertemplate=name + ": $%{y:,.0f}<extra></extra>")
fig.add_vline(x=year, line=dict(color=AXIS, width=1))
fig.update_layout(hovermode="x unified", legend_traceorder="reversed")
fig.update_xaxes(dtick=1, range=[min(years) - 0.4, max(years) + 0.4], showgrid=False)
fig.update_yaxes(tickprefix="$", tickformat=",.0f")
show(base_layout(fig, height=400))
st.caption(f"The comparison group is the {k} counties most similar in {year} (vertical line), "
           "followed across all years. Nominal dollars.")

# ------------------------------------------------------------------ table
st.subheader("The similar counties")
table = pd.concat([year_df[year_df["fips"] == fips].assign(distance=0.0), peers])
table = table.assign(county=np.where(table["fips"] == fips, table["name"] + " (selected)", table["name"]),
                     spend_pc_std=table["spend_pc_std"].round(), median_income=table["median_income"].round())
st.dataframe(
    table[["county", "spend_pc_std", "median_income", "poverty_rate", "avg_age", "dual_pct", "ma_rate",
           "rucc", "distance"]],
    hide_index=True,
    height=35 * (len(table) + 1) + 3,  # 35 px per row plus header: shows every row without scrolling
    column_config={
        "county": st.column_config.TextColumn("County"),
        "spend_pc_std": st.column_config.NumberColumn("Spending per beneficiary ($)", format="localized"),
        "median_income": st.column_config.NumberColumn("Median income ($)", format="localized"),
        "poverty_rate": st.column_config.NumberColumn("Poverty %", format="%.1f"),
        "avg_age": st.column_config.NumberColumn("Avg. age", format="%.0f"),
        "dual_pct": st.column_config.NumberColumn("Dual-eligible %", format="%.1f"),
        "ma_rate": st.column_config.NumberColumn("Medicare Advantage %", format="%.1f"),
        "rucc": st.column_config.NumberColumn("Rural-urban code", format="%d",
                                              help="1 = largest metro areas, 9 = most rural"),
        "distance": st.column_config.NumberColumn("Distance", format="%.2f",
                                                  help="Lower = more similar. Euclidean distance across six z-scores."),
    },
)

with st.expander("How similar counties are chosen"):
    st.markdown(f"""
Counties are matched on six characteristics, **never on spending**, so the comparison asks:
*among counties like this one, does it spend more or less?*

1. Median household income (Census SAIPE)
2. Poverty rate (Census SAIPE)
3. Average age of Medicare beneficiaries
4. Share of beneficiaries also enrolled in Medicaid (dual-eligible)
5. Share of Medicare enrollees in Medicare Advantage
6. USDA Rural-Urban Continuum Code (1 = largest metro areas, 9 = most rural)

Each characteristic is converted to a z-score **within the selected year** (how many standard deviations a county is
from that year's average), so counties are compared only with other counties in the same year and dollar amounts
are not distorted by inflation. The similar counties are the ones with the smallest Euclidean distance across the
six z-scores, with each characteristic weighted equally.

Spending is standardized by CMS to remove geographic differences in Medicare payment rates. It is not adjusted for
how healthy beneficiaries are. Counties with fewer than 500 Original Medicare beneficiaries are excluded because
their averages are noisy.
""")

st.divider()
st.caption(
    f"Data: CMS Medicare Geographic Variation file (2014 to 2024), Census SAIPE, USDA Rural-Urban Continuum Codes 2023. "
    f"[Project write-up]({SITE_URL}) · [Code on GitHub]({REPO_URL})"
)
