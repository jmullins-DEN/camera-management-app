CAMERA MANAGEMENT APP — SESSION HANDOFF (2026-06-21)

Paste this whole email into the next session to pick up exactly where we left off.

=====================================================================
WHAT THIS IS
=====================================================================
We are building an in-house replacement for Infinity's CAMERA MANAGEMENT
module only (Phase A: mirror + nicer data entry + planned write-back to
Infinity). Reason: Infinity's form driver-pickers read raw item order and
CANNOT be alphabetized via API or any UI button. We own the rendering, so
our app sorts drivers A-Z permanently and adds trend/face-to-face logic
Infinity doesn't have.

=====================================================================
WHERE THE CODE LIVES
=====================================================================
- GitHub repo:  github.com/jmullins-DEN/camera-management-app  (public)
- Hosting:      Cloudflare Pages, static / no build (same model as
                training-schedule-manager). Johnny is connecting the repo
                in Cloudflare -> expected URL camera-management-app.pages.dev
                Pages settings: Framework=None, Build command=blank,
                Output dir=/ (root).
- Container path: /home/johnny/workspace/camera-app/
- Files:
    index.html      -> the ENTIRE app (one file, vanilla JS)
    seed.js/seed.json -> real data mirrored from Infinity
    build_seed.py --all -> re-pull from Infinity anytime
    logo.jpg        -> Synergy "logo cube" (from Drive), shown in sidebar
- Every git push auto-redeploys. Push with the GitHub token (user jmullins-DEN).

=====================================================================
DESIGN / BRAND (locked)
=====================================================================
- Primary  #1477e1 (blue) - buttons, links, active states
- Accent   #febe10 (gold) - sidebar left "spine", "Management" in brand,
           active-nav bar, coaching pills, top-3 behavior box outlines
- Logo: Synergy cube, sidebar brand. (Per-customer logos are separate, set
        on the Customers screen.)

=====================================================================
BUSINESS RULES (locked this session)
=====================================================================
- ENTRY BEHAVIORS — exactly these 12, nothing else:
    Camera Obstruction, Driver Distraction-Phone, Driver Distraction-Cab,
    Drowsy Driving, Following Distance, Hard Brake, Near Miss,
    Sign Violation, Traffic Light Violation, Speeding, U-Turn, Seat Belt
- COACHING NEEDED — exactly 4 types:
    Coaching Notes, Critical Event, Blocked Camera, Unidentified Driver
    (Johnny is cleaning all Infinity boards to match these + the 12 behaviors.)
- TREND RULE (per customer): "N events of the same behavior in M days will be
  considered a trend and a face-to-face engagement will be NEEDED."
    * Default N=3, M=30. Days=0 turns trend tracking OFF for that customer.
    * Driver Distraction-Phone + Driver Distraction-Cab TREND TOGETHER as one
      group (TREND_GROUPS in code). All other behaviors trend on their own.

=====================================================================
THE SCREENS (current state)
=====================================================================
1) CUSTOMERS
   - Columns: Logo | Customer | Event Entry (link) | Driver field | Drivers |
     Events | Trend rule. (View button removed; Event Entry moved up front.)
   - Logo: click cell -> modal, enter a website -> fetches 2 candidates
     (Clearbit logo + hi-res favicon) -> click one to APPROVE. Paste-URL fallback.
   - Trend rule: solid clickable chip ("3 in 30d" / "Off") -> modal with the
     editable sentence (two number fields). 0 days = off.

2) EVENT ENTRY (was "Enter")
   - Pick customer (its logo shows up top), then log an event.
   - Driver field: type-to-search, ALWAYS A-Z picker (the whole point).
   - "+ New driver" button: adds driver to that customer's roster immediately
     (tagged "pending"), auto-selects. Queued with board type/folder/attr so
     write-back lands correctly (reference board -> new roster item; label
     board -> new label option).
   - Live trend banner as you pick driver/behavior/date.
   - RED face-to-face alert appears directly UNDER the Coaching-needed dropdown
     when the entry crosses threshold.
   - Right panel: shows ONLY the selected driver's events, grouped by behavior,
     within the trend-day window (not all drivers).

3) EVENTS BY BEHAVIOR (was Events by Driver)
   - Filters: Customer | Driver (defaults All) | Date range.
   - One BOX per behavior with a count. Click a box -> expands to list:
     Driver, Date, Coaching needed (+ Customer when All customers).
   - Top-3 behaviors (most events) outlined in gold accent.

=====================================================================
OPEN ITEMS / NEXT STEPS (in priority order)
=====================================================================
A) INFINITY WRITE-BACK — STILL UNTESTED, GATED ON JOHNNY'S GO.
   Everything currently queues LOCALLY (browser only). Next action: run the
   POST-create test = create one throwaway roster item on the Customer
   Template Board, confirm it persists, then delete it (also tests delete).
   This single test unblocks BOTH new-driver and event write-back.
   NOTE: a static Pages site has no Infinity token in the browser, so real
   write-back almost certainly needs a small backend (Cloudflare Worker + D1
   holding the token). Known API facts from this session:
     - item sort_order is READ-ONLY on writes (PUT returns 200 but ignores it)
     - NO "sort permanently" button exists in Infinity (confirmed in docs)
     - VIEW settings ARE writable via PUT (200 + persists)
     - POST-create persistence = the one thing still unproven.

B) 5 BOARDS DON'T AUTO-MAP CLEANLY (need per-board field override):
   Apex Waste, Mission Wrecker, Alandon Tow, Apple Towing, Andrew Distribution.
   Other 17 of 22 mapped fine.

C) PERSISTENCE: currently browser-only; needs D1 backend for cross-device +
   shared data. Same backend that would hold the Infinity token (see A).

D) Confirm behaviors standardized in Infinity once Johnny finishes cleanup,
   so history/Events views line up with the 12.

=====================================================================
KEY INFINITY IDs
=====================================================================
- Customer Template Board (MASTER / clone source): nUkActgZYPm  (DEN workspace)
    Camera Management folder EJRUGb9Nxv5
    Driver Roster x6rn5yQLjst (the spine; each driver = item, "Driver Name" label)
- Allstar Towing & Recovery (REFERENCE board, our test): di85P7h2apV
- Fiore & Sons (LABEL board, both-ways test): 8gejhhHJj4e
- Workspaces: DEN 59792, Fedex Accounts 56408
- Seed currently covers 22 boards, 1,263 drivers, 548 mirrored events.

Driver "both ways": our app always shows ONE canonical name in the A-Z picker.
On write-back the mapper checks driver_field_type:
  reference board -> write the roster item_id
  label board     -> write the label string

=====================================================================
IMMEDIATE FIRST MOVE NEXT SESSION
=====================================================================
1. Confirm Cloudflare Pages is live (camera-management-app.pages.dev).
2. Decide: run the Infinity write-back POST-create test? (yes/no)
3. If yes -> likely stand up the Worker+D1 backend so write-back + persistence
   are real, then fix the 5 unmapped boards.
