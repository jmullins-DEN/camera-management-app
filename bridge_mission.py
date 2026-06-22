#!/usr/bin/env python3
"""One-off: rebuild ONLY Mission Wrecker's events in seed.json as a 30-day
bridge from the OLD board.

Mission is migrating to the new board (7W2SQKrNcXQ) starting today, with drivers
assigned going forward. Until the new board accumulates 30 days of its own
driver-tagged events, the trend is carried by the OLD board
("z old - Mission Wrecker", MfEUxnTRUV9), whose recent events ARE driver-tagged.

Mission events = new board (90d, as-is) + old board (last 30 days, driver-tagged,
coaching remapped). The old-board archive (2022-2025) is dropped. The old-board
slice naturally expires as the 30-day window rolls forward.

Touches only the Mission board entry. Other boards untouched.
"""
import json, sys, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'bin'))
import infinity as inf
from build_seed import pick_attr, pick_label_attr
from repull_events import (cursor_items, label_map, resolve_events,
                           OLD_MISSION, MISSION_COACH_REMAP)

HERE = pathlib.Path(__file__).parent
TODAY = datetime.date(2026, 6, 22)
CUT90 = (TODAY - datetime.timedelta(days=90)).isoformat()   # new board window
CUT30 = (TODAY - datetime.timedelta(days=30)).isoformat()   # old board bridge
NEW_BOARD = '7W2SQKrNcXQ'

def main():
    seed = json.loads((HERE / 'seed.json').read_text())
    b = next(x for x in seed['boards'] if x['board'] == NEW_BOARD)

    # --- new board events (90-day window), as the other boards are pulled ---
    attrs = inf.attributes(inf.WS.get(b['ws'], b['ws']), b['board'])
    bmap = label_map(attrs, b['attr'].get('behavior'))
    cmap = label_map(attrs, b['attr'].get('coaching'))
    idname = {d['id']: d['name'] for d in b.get('drivers', [])}
    attr = dict(b['attr']); attr['driver_attr'] = b['driver_attr']
    items = cursor_items(b['ws'], b['board'], b['camera_folder'])
    new_evs = resolve_events(items, attr, idname, bmap, cmap, since=CUT90)

    # --- old board bridge: last 30 days, driver-tagged, coaching remapped ---
    ws, ob, ofold, odattr, odate = OLD_MISSION
    oattrs = inf.attributes(inf.WS[ws], ob)
    obeh = pick_attr(oattrs, 'behavior')
    ocoach = (pick_label_attr(oattrs, 'coaching', 'needed') or
              pick_label_attr(oattrs, 'action', 'taken') or
              pick_label_attr(oattrs, 'coaching'))
    obmap = label_map(oattrs, obeh.get('id') if obeh else None)
    ocmap = label_map(oattrs, ocoach.get('id') if ocoach else None)
    odlbl = label_map(oattrs, odattr)
    oitems = cursor_items(ws, ob, ofold)
    oattr = {'date': odate, 'behavior': obeh.get('id') if obeh else None,
             'coaching': ocoach.get('id') if ocoach else None,
             'reviewed': None, 'driver_attr': odattr}
    old_evs = resolve_events(oitems, oattr, odlbl, obmap, ocmap, since=CUT30)
    for e in old_evs:
        e['coaching'] = MISSION_COACH_REMAP.get(e['coaching'], e['coaching'])

    seen = {e['item'] for e in new_evs}
    merged = new_evs + [e for e in old_evs if e['item'] not in seen]
    merged.sort(key=lambda e: (e.get('date') or ''), reverse=True)

    old_n = len(b.get('events', []))
    b['events'] = merged
    print(f"Mission: new={len(new_evs)} old30d={len(old_evs)} -> {old_n} -> {len(merged)}", file=sys.stderr)
    tagged = sum(1 for e in merged if e.get('driver'))
    print(f"  driver-tagged: {tagged}/{len(merged)}", file=sys.stderr)

    seed['generated'] = TODAY.isoformat() + ' (Mission 30-day old-board bridge)'
    (HERE / 'seed.json').write_text(json.dumps(seed, indent=2, ensure_ascii=False))
    (HERE / 'seed.js').write_text('window.SEED = ' + json.dumps(seed, ensure_ascii=False) + ';\n')
    print("wrote seed.json + seed.js", file=sys.stderr)

if __name__ == '__main__':
    main()
