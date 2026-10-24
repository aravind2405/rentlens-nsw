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
