# Engineering log

## 2026-10-24: pin Chart.js with Subresource Integrity

The dashboard loads Chart.js 4.4.1 from cdnjs. Without an `integrity` attribute, a
tampered CDN file would run on the dashboard page. Added `integrity`, `crossorigin="anonymous"`
and `referrerpolicy="no-referrer"` to the script tag in `docs/index.html`.

How the hash was produced and checked:

- `curl -s https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js | openssl dgst -sha384 -binary | openssl base64 -A`
  gave `bs/nf9FbdNouRbMiFcrcZfLXYPKiPaGVGplVbv7dLGECccEXDW+S3zjqSKR5ZEaD`.
- The file's sha512 matches the value cdnjs publishes at
  `https://api.cdnjs.com/libraries/Chart.js/4.4.1?fields=sri`.
- Loading the file in Node reports version 4.4.1 and the same 50 exports as the official
  npm build (`npm pack chart.js@4.4.1`, `dist/chart.umd.js`). The two files are not
  byte-identical: cdnjs serves its own minified copy.
- In a browser, the dashboard renders with the hash in place and the script is blocked
  when the hash is deliberately wrong.

Upgrading Chart.js means recomputing the hash. Vendoring the file into `docs/` would remove
the CDN dependency entirely.

## 2026-10-24: correct the data licence to CC BY

The README said the bond data is under the "NSW Government open data licence", which has no
source. The Data.NSW record for Rental Bond Lodgement (publisher: Fair Trading) states
"Creative Commons Attribution" (https://data.nsw.gov.au/data/dataset/rental-bond-lodgement).
The nsw.gov.au download page states no licence, and the NSW website default is CC BY 4.0
(https://www.nsw.gov.au/nsw-government/about-website/copyright). The dataset record gives no
version, so the docs say "CC BY" without one.

CC BY needs attribution, a licence link and a note of changes. The README, `docs/project-brief.md`
and the dashboard footer now credit NSW Fair Trading and the State of NSW, name CC BY, and
say the medians are an aggregation made here, not official statistics.

## 2026-10-24: dashboard accessibility, landmark, description and favicon

Baseline on the live dashboard (Lighthouse 13.5.0 and axe-core 4.14.0, 2026-10-24 11:19 to 11:20 AEDT,
measured with the scripts in `scripts/measure/` of the `ad-site` repo): accessibility 87, best practices 96,
SEO 90; axe reported 3 violations (`color-contrast` on 12 elements, `landmark-one-main`, `region` on 12 elements).

Changes in `docs/index.html`:

- `--muted-light` was only used for text and measured 2.53:1 on white; it is now `#6B7280` (4.83:1).
- Green change figures used `#16A34A` (3.29:1); text now uses a new `--green-text: #15803D` (5.02:1). The chart
  line, legend swatch and green token keep `#16A34A`, since graphics need 3:1.
- Chart axis labels use the same `#6B7280` grey.
- Content between `<header>` and `<footer>` is wrapped in `<main>`.
- Added a meta description and a favicon (`docs/favicon.svg`, matching the header logo mark). The only console
  error was the missing favicon.

Result, measured on local copies of `docs/` served over HTTP (like for like, before and after), 3 Lighthouse
runs each, median:

| | Accessibility | Best practices | SEO | Performance (mobile / desktop) | axe violations |
|---|---|---|---|---|---|
| Before | 87 | 96 | 90 | 98 / 100 | 3 |
| After | 100 | 100 | 100 | 98 / 100 | 0 |

Commands (from a directory with the scripts and pinned tools installed):

```bash
BASE=http://127.0.0.1:3601 PAGES="/" TAG=after node run-axe.mjs
BASE=http://127.0.0.1:3601 PAGES="/" TAG=after- bash run-lighthouse.sh
BASE=http://127.0.0.1:3602 PAGES="/" TAG=beforelocal- bash run-lighthouse.sh   # unchanged docs/index.html from main
python3 summarize-lighthouse.py
```

Full-page screenshots before and after have identical dimensions (750x3190 on a 375 px phone viewport,
1440x988 on desktop), so the layout did not move; about 1 to 2 percent of pixels changed, all in text and
axis labels. Local performance is not comparable with the live CDN numbers, so the live dashboard should be
re-measured after merging.

## 2026-10-24: CI maintenance (action versions and runner)

A CI run on `main` carried two annotations. A warning said `actions/checkout@v4`, `actions/cache@v4` and
`actions/setup-python@v5` target Node.js 20, which GitHub is retiring and was already forcing onto Node 24.
A notice said the `ubuntu-latest` label moves to Ubuntu 26 from 19 October 2026.

Changes to `.github/workflows/dbt.yml`:

- `actions/checkout` v4 to v7, `actions/setup-python` v5 to v7, `actions/cache` v4 to v6 (the latest releases
  at the time; inputs unchanged).
- `runs-on: ubuntu-latest` to `ubuntu-24.04`, so the operating system only changes when it is changed here.
  Moving to Ubuntu 26 later should be a deliberate change that CI proves.

Added `.github/dependabot.yml` so GitHub Actions versions are proposed weekly instead of piling up.
Python dependencies are pinned in `requirements.txt` on purpose and are not covered by it.
