#!/usr/bin/env python3
"""Re-pull camera events for every board already in seed.json, using CURSOR
pagination (has_more/after) instead of the broken page= pagination that
silently capped every board at 50 events.

- General boards: keep a rolling WINDOW_DAYS window (covers the 30-day trend).
- Mission Wrecker: also merge the FULL history from the old board
  "z old - Mission Wrecker" (events stopped on the new board after migration).

Updates seed.json + seed.js in place. Does NOT touch the board list or drivers.
"""
import json, sys, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'bin'))
import infinity as inf
from build_seed import val_for, resolve, pick_attr

HERE = pathlib.Path(__file__).parent
WINDOW_DAYS = 90
TODAY = datetime.date(2026, 6, 22)
CUT = (TODAY - datetime.timedelta(days=WINDOW_DAYS)).isoformat()

OLD_MISSION = ('DEN', 'MfEUxnTRUV9', 'nA8R3U1XKtM',            # ws, board, camera folder
               'b3271170-6d5f-4162-8169-542eba0ebeed',         # driver label attr
               '6028e889-c5a3-4694-be45-175582536ae9')         # Date Event Occurred

def cursor_items(ws, board, folder, expand=True):
    """Walk Infinity's cursor pagination to completion."""
    wid = inf.WS[ws] if ws in inf.WS else ws
    out, after, guard = [], None, 0
    while True:
        params = {'folder_id': folder, 'per_page': 50}
        if expand: params['expand[]'] = 'values'
        if after: params['after'] = after
        r = inf.call('GET', f'/workspaces/{wid}/boards/{board}/items', params=params)
        out += r.get('data', [])
        guard += 1
        if not r.get('has_more') or guard > 200: break
        after = r.get('after')
    return out

def label_map(attrs, attr_id):
    if not attr_id: return {}
    a = next((x for x in attrs if x.get('id') == attr_id), None)
    if not a: return {}
    return {l.get('id'): l.get('name') for l in (a.get('settings', {}) or {}).get('labels', [])}

def resolve_events(items, attr, idname, bmap, cmap, since=None):
    evs = []
    for it in items:
        date = val_for(it, attr.get('date'))
        if since and isinstance(date, str) and date[:10] < since:
            continue
        draw = val_for(it, attr.get('driver_attr'))
        dname = None
        if isinstance(draw, list) and draw: dname = idname.get(draw[0], bmap.get(draw[0]))
        elif isinstance(draw, str): dname = idname.get(draw, draw)
        ev = {
            'driver': dname,
            'date': date,
            'behavior': resolve(val_for(it, attr.get('behavior')), bmap),
            'coaching': resolve(val_for(it, attr.get('coaching')), cmap),
            'reviewed': val_for(it, attr.get('reviewed')),
            'item': it.get('id'),
        }
        if ev['date'] or ev['behavior'] or ev['driver']:
            evs.append(ev)
    return evs

def main():
    seed = json.loads((HERE / 'seed.json').read_text())
    boards = seed['boards']
    for b in boards:
        if not b.get('camera_folder'):
            print(f"skip {b['name']:32} (no camera folder)", file=sys.stderr); continue
        attrs = inf.attributes(inf.WS.get(b['ws'], b['ws']), b['board'])
        bmap = label_map(attrs, b['attr'].get('behavior'))
        cmap = label_map(attrs, b['attr'].get('coaching'))
        idname = {d['id']: d['name'] for d in b.get('drivers', [])}
        attr = dict(b['attr']); attr['driver_attr'] = b['driver_attr']
        items = cursor_items(b['ws'], b['board'], b['camera_folder'])
        evs = resolve_events(items, attr, idname, bmap, cmap, since=CUT)

        # Mission: merge full old-board history (no window — recover what was lost)
        if b['board'] == '7W2SQKrNcXQ':
            ws, ob, ofold, odattr, odate = OLD_MISSION
            oattrs = inf.attributes(inf.WS[ws], ob)
            obeh = pick_attr(oattrs, 'behavior')
            obmap = label_map(oattrs, obeh.get('id') if obeh else None)
            odlbl = label_map(oattrs, odattr)              # old roster label -> names
            oitems = cursor_items(ws, ob, ofold)
            oattr = {'date': odate, 'behavior': obeh.get('id') if obeh else None,
                     'coaching': None, 'reviewed': None, 'driver_attr': odattr}
            oevs = resolve_events(oitems, oattr, odlbl, obmap, {}, since=None)
            seen = {e['item'] for e in evs}
            merged = evs + [e for e in oevs if e['item'] not in seen]
            print(f"  Mission: new={len(evs)} old={len(oevs)} -> merged={len(merged)}", file=sys.stderr)
            evs = merged

        evs.sort(key=lambda e: (e.get('date') or ''), reverse=True)
        old = len(b.get('events', []))
        b['events'] = evs
        print(f"OK  {b['name']:32} events {old:4} -> {len(evs):4}", file=sys.stderr)

    seed['generated'] = TODAY.isoformat() + ' (events re-pulled, cursor paginated)'
    (HERE / 'seed.json').write_text(json.dumps(seed, indent=2, ensure_ascii=False))
    (HERE / 'seed.js').write_text('window.SEED = ' + json.dumps(seed, ensure_ascii=False) + ';\n')
    print(f"\nwrote seed.json + seed.js: {len(boards)} boards", file=sys.stderr)

if __name__ == '__main__':
    main()
