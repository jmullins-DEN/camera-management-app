# Camera Management

In-house replacement for Infinity's Camera Management module (Phase A: mirror + data entry +
local queue; write-back to Infinity activates once the create-API test passes).

Single-file app, same deploy model as `training-app`:
- `index.html` — the whole app (3 screens)
- `seed.js` — data mirrored from Infinity (`window.SEED`), loaded by index.html under `file://`
- `seed.json` — same data, pretty-printed (source of truth for the build)
- `build_seed.py` — re-pull from Infinity → regenerates seed.js + seed.json

## Screens
1. **Customers** — every camera board, driver field type, driver/event counts, per-customer
   **trend-days** setting (used later for reporting), and a click-to-set **logo** per customer.
2. **Data Entry** — pick a customer (logo shows), log an event. Driver picker is **always A–Z and
   type-to-search** (the whole point — fixes Infinity's unsortable dropdown). Saves to the browser
   and tags each entry `new` until write-back is live.
3. **Events by Driver** — grouped A–Z by driver; filter by customer + date range; optional
   **sort by event type**; columns are driver, event type (behavior) and coaching needed.

State lives in `localStorage` (`cam_settings` = logos + trend days, `cam_local` = queued events).

## Refresh the mirror
```
python3 build_seed.py --all      # all 22 camera boards
python3 build_seed.py            # just Allstar + Fiore (fast smoke test)
```

## Deploy (on PC, mirrors training-schedule-manager)
1. Clone the repo, open `index.html` in a browser to view.
2. Cloudflare → Workers & Pages → Create → Pages → Connect to Git → this repo.
   Build command: *none* · Output dir: `/`. Push = auto-redeploy.

## Known seed-mapping gaps (need per-board attribute overrides before go-live)
- **Apex Waste** — camera fields didn't map (folder/field names differ). 
- **Mission Wrecker** — driver field matched a free-text field (no roster items pulled).
- **Alandon Tow** — driver field matched a checkbox.
- **Apple Towing** — board structured differently / empty; nothing mapped.
- **Andrew Distribution** — 248 driver labels (legacy/dupes), no events pulled.

Everything else (Panhandle, PCS, All City, Fiore, PEP MOVE, Aero Flex, Express Tow, Garmat, KAS,
NextDriv, Starkey, Vargas, Five Aces, Wicked, Deep River, Allstar) mapped cleanly.
