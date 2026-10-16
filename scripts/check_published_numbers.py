"""
check_published_numbers.py

Recomputes every number shown on the dashboard (docs/index.html) and in
README.md from the dbt marts in dev.duckdb, and reports any mismatch.

Run after `dbt build`:
    python scripts/check_published_numbers.py

Exit code 0 = every published number matches the pipeline.
"""

import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "docs" / "index.html").read_text()
README = (ROOT / "README.md").read_text()
DB = duckdb.connect(str(ROOT / "dev.duckdb"), read_only=True)

REAL_TYPES = ("F", "H", "T", "O", "U")
failures = []
checked = 0


def check(name, published, actual, tolerance=0):
    global checked
    checked += 1
    ok = abs(float(published) - float(actual)) <= tolerance
    if not ok:
        failures.append(f"{name}: published {published}, pipeline {actual}")
    return ok


def js_array(name):
    body = re.search(rf"const {name} = \[(.*?)\];", HTML, re.S).group(1)
    body = re.sub(r"//[^\n]*", "", body)
    return [x.strip().strip("'\"") for x in body.split(",") if x.strip()]


def money(text):
    return int(text.replace("$", "").replace(",", ""))


# ── 1. Monthly series behind the charts ──────────────────────────────────────
months = js_array("ALL_MONTHS")
flat = [float(v) for v in js_array("ALL_F")]
house = [float(v) for v in js_array("ALL_H")]
volume = [int(v) for v in js_array("ALL_VOL")]
assert len(months) == len(flat) == len(house) == len(volume), "array lengths differ"

file_months = [f"{2022 + i // 12}-{i % 12 + 1:02d}" for i in range(len(months))]

medians = {
    (fm, dt): float(med)
    for fm, dt, med in DB.sql(
        "select file_month, dwelling_type, median_weekly_rent from rents_by_month"
    ).fetchall()
}
counts = dict(
    DB.sql(
        f"select file_month, sum(lodgement_count) from rents_by_month "
        f"where dwelling_type in {REAL_TYPES} group by 1"
    ).fetchall()
)

available = [fm for fm in file_months if (fm, "F") in medians]
skipped = len(file_months) - len(available)
for i, fm in enumerate(file_months):
    if fm not in available:
        continue
    check(f"flat median {fm}", flat[i], medians[(fm, "F")], tolerance=0.5)
    check(f"house median {fm}", house[i], medians[(fm, "H")], tolerance=0.5)
    check(f"bond count {fm}", volume[i], counts[fm])

# ── 2. Headline cards: values and % changes ──────────────────────────────────
card_flat = money(re.search(r'id="kpiFlatRent">(\$[\d,]+)<', HTML).group(1))
card_house = money(re.search(r'id="kpiHouseRent">(\$[\d,]+)<', HTML).group(1))
check("flat card = latest month", card_flat, flat[-1])
check("house card = latest month", card_house, house[-1])

def pct(new, old):
    return round((new / old - 1) * 100, 1)

kpi_data = re.search(r"const KPI_DATA = \{(.*?)\n\};", HTML, re.S).group(1)
for label, base_month in (("1y", "Sep 25"), ("2y", "Oct 24"), ("all", "Jan 22")):
    block = re.search(rf"'{label}': \{{(.*?)\}}", kpi_data, re.S).group(1)
    for series, key in ((flat, "flatChange"), (house, "houseChange")):
        shown = float(re.search(rf"{key}: '\+([\d.]+)%", block).group(1))
        check(f"{key} {label}", shown, pct(series[-1], series[months.index(base_month)]))

# ── 3. Totals and peaks ──────────────────────────────────────────────────────
staging_rows = DB.sql("select count(*) from stg_bond_lodgements").fetchone()[0]
readme_total = int(re.search(r"Total bonds lodged: \*\*([\d,]+) records", README).group(1).replace(",", ""))
check("README total records", readme_total, staging_rows)
readme_records = int(re.search(r"\*\*Records:\*\* ([\d,]+)", README).group(1).replace(",", ""))
check("README records line", readme_records, staging_rows)
footer_m = float(re.search(r"· ([\d.]+)M records ·", HTML).group(1))
check("footer records (millions)", footer_m, round(staging_rows / 1e6, 2))
intro_m = float(re.search(r"Sep 2026, ([\d.]+)M records\)", README).group(1))
check("README intro records (millions)", intro_m, round(staging_rows / 1e6, 2))

if not skipped:
    peak_all = max(volume)
    m = re.search(r"Peak single month: \*\*(\w+ \d{4})\*\* \(([\d,]+) bonds", README)
    check("README all-time peak count", int(m.group(2).replace(",", "")), peak_all)
    if months[volume.index(peak_all)] != m.group(1)[:3] + " " + m.group(1)[-2:]:
        failures.append(f"README all-time peak month: published {m.group(1)}, pipeline {months[volume.index(peak_all)]}")
    window = volume[months.index("Oct 25"):]
    peak_1y = max(window)
    m = re.search(r"Peak month in window: (\w+ \d{4}) \(([\d,]+) bonds", README)
    check("README 12-month peak count", int(m.group(2).replace(",", "")), peak_1y)

# ── 4. All-time medians in README ────────────────────────────────────────────
alltime = dict(
    DB.sql(
        "select dwelling_type, quantile_cont(weekly_rent, 0.5) from int_lodgements_flagged "
        "where rent_flag is null and postcode_flag is null and dwelling_type in ('F','H') group by 1"
    ).fetchall()
)
m = re.search(r"All-time median flat rent: \*\*\$(\d+)/wk\*\* · All-time median house rent: \*\*\$(\d+)/wk", README)
check("README all-time flat median", m.group(1), alltime["F"], tolerance=0.5)
check("README all-time house median", m.group(2), alltime["H"], tolerance=0.5)

# ── 5. Postcode table ────────────────────────────────────────────────────────
rows = re.findall(r"\['[^']*\((\d{4})\)', '\$(\d+)'\]", HTML)
top = DB.sql(
    f"select postcode, median_weekly_rent from rents_by_postcode "
    f"where dwelling_type = 'F' and lodgement_count >= 30 "
    f"order by median_weekly_rent desc, lodgement_count desc limit {len(rows)}"
).fetchall()
for rank, ((pc, val), (real_pc, real_val)) in enumerate(zip(rows, top), start=1):
    if int(pc) != int(real_pc):
        failures.append(f"postcode table rank {rank}: published {pc}, pipeline {real_pc}")
    checked += 1
    check(f"postcode {pc} median", val, real_val)
readme_cbd = int(re.search(r"Sydney CBD \(2000\) at \*\*\$(\d+)/wk", README).group(1))
check("README priciest postcode", readme_cbd, top[0][1])

# ── Report ───────────────────────────────────────────────────────────────────
print(f"Checked {checked} published numbers.")
if skipped:
    print(f"NOTE: {skipped} months not in this database were skipped (partial data).")
if failures:
    print(f"\n{len(failures)} MISMATCH(ES):")
    for f in failures:
        print("  ✗", f)
    sys.exit(1)
print("All published numbers match the pipeline. ✓")
