#!/usr/bin/env python3
"""Mission Wrecker -> Mission 2 migration.

Modes:
  --introspect   read both boards, print folder + attribute maps (no writes)
  --add-fields   create the missing roster attributes on Mission 2
  --dry-run      build the full migration plan, print counts + samples (no writes)
  --execute      perform the migration (drivers, then 2026 events + references)
"""
import json, sys, time, uuid, urllib.request, urllib.parse, urllib.error

TOKEN = open('/home/johnny/.config/openclaw-infinity/token').read().strip()
WS = '59792'
OLD = 'MfEUxnTRUV9'   # Mission Wrecker (label-driver board)
NEW = '7W2SQKrNcXQ'   # Mission 2 (master clone, reference-driver board)
BASE = 'https://app.startinfinity.com/api/v2'

def api(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + TOKEN)
    req.add_header('Accept', 'application/json')
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        return e.code, {'error': e.read().decode()[:300]}

def get_all_items(board, folder):
    """Paginate every item in a folder, values expanded (has_more/after cursor)."""
    items, after = [], None
    while True:
        q = f'?folder_id={folder}&expand[]=values&limit=100'
        if after:
            q += '&after=' + urllib.parse.quote(str(after))
        st, body = api('GET', f'/workspaces/{WS}/boards/{board}/items{q}')
        batch = body.get('data', []) if isinstance(body, dict) else []
        items.extend(batch)
        if not body.get('has_more') or not body.get('after'):
            break
        after = body.get('after')
    return items

def attrs(board):
    st, body = api('GET', f'/workspaces/{WS}/boards/{board}/attributes?limit=100')
    return body.get('data', [])

def folders(board):
    st, body = api('GET', f'/workspaces/{WS}/boards/{board}/folders?limit=100')
    return body.get('data', [])

def show_board(label, board):
    print(f'\n===== {label}  ({board}) =====')
    print('-- folders --')
    for f in folders(board):
        print(f"  {f.get('id')}  {f.get('name')!r}  parent={f.get('parent_id')}")
    print('-- attributes --')
    for a in attrs(board):
        opts = a.get('settings', {}).get('labels') if isinstance(a.get('settings'), dict) else None
        n = f"  ({len(opts)} opts)" if opts else ''
        print(f"  {a.get('id')}  {a.get('type'):10}  {a.get('name')!r}{n}")

def folder_detail(board, folder):
    st, body = api('GET', f'/workspaces/{WS}/boards/{board}/folders/{folder}')
    return body.get('data', body)

def vmap(item):
    """attribute_id -> data, from an expanded item."""
    out = {}
    for v in item.get('values', []) or []:
        out[v.get('attribute_id')] = v.get('data')
    return out

# ---------------- migration spec ----------------
OLD_ROSTER_FOLDER = 'e6iHBci54G6'
OLD_CAMERA_FOLDER = 'nA8R3U1XKtM'
NEW_ROSTER_FOLDER = 'tRjA68oSQ5k'
NEW_CAMERA_FOLDER = 'C8fbgdCmqQ2'

# old attribute ids
O_DRIVER = 'b3271170-6d5f-4162-8169-542eba0ebeed'   # label: driver picker (roster + events)
O_TRUCK  = '4bf81e50-083f-4b7d-9e54-55fece0b56f6'
O_PERS   = '47d18206-e861-436a-bce4-64b6a0d63b81'   # Personal Phone
O_COMP   = '1492dfc0-6e3d-4521-9d93-cf80839fc12f'   # Comp. Phone
O_DIV    = 'a66c3fdd-5a25-4bfb-af17-d7fb2ba9a390'   # Division
O_LOC    = 'a82c51d8-8e61-4c64-a5d9-6bda13b3fbb2'   # Location (label)
O_BEH    = '9043b7d2-ffd9-4608-b3fa-75ab7cb15c15'   # Behavior Observed
O_ACT    = '0b5f7543-7f19-4dc6-aa27-8ec0a2b61aaa'   # Action Taken
O_DATE   = '6028e889-c5a3-4694-be45-175582536ae9'   # Date Event Occurred
O_REVD   = '8719046d-6ea9-4a5e-ae4f-b64e82235a8f'   # Date Event Reviewed
O_CNOTE  = '1133ce5e-b58c-4d95-bc46-a272b3228ff9'   # Coaching Note (longtext)
O_MNOTE  = '2df25ae9-a295-43c6-bedc-62ab51247153'   # Management Notes (longtext)

# new (Mission 2) attribute ids
N_DRVNAME = '61f47954-3a5e-44ae-9319-44fd8a6db756'  # Driver Name (text)
N_NAME    = '32ba5d4d-dbe2-4710-b552-e37024fc5559'  # Name (text)
N_TRUCK   = '18034e85-f532-426e-a355-fedd07de1800'  # Truck Number (exists board-level, attach)
N_BEH     = '49700280-e63d-4eda-acb4-ed26da7542b9'  # Behavior Observed
N_COACH   = '289b3c3b-efdf-4c72-8f95-7cbb659b7782'  # Coaching Needed
N_REF     = '2be1b7b7-34f4-45d9-9710-e26a669fa286'  # Driver Roster (reference)
N_DATE    = '10e94227-c1a6-49f0-9101-37c8d9e73c89'  # Camera Event Date
N_REVD    = '43786fa9-3d7a-4ef9-a48e-68c4d56b3d43'  # Date Event Reviewed
N_NOTES   = '40f881c1-b250-44ab-b1fd-38d35d7f1f24'  # Notes:

# behavior old-name -> target standard name (16 -> 12)
BEH = {
    'Distracted Driving with Phone': 'Driver Distraction-Phone',
    'Distracted Driving-Other': 'Driver Distraction-Cab',
    'Stop Sign Violation': 'Sign Violation',
    'Red Light Violation': 'Traffic Light Violation',
    'Following Distance': 'Following Distance',
    'Seat Belt': 'Seat Belt',
    'Near Miss': 'Safety-Critical Event',
    'Fatigue': 'Drowsy Driving',
    'Accident': 'Safety-Critical Event',
    'Speeding': 'Speeding',
    'Harsh Turn': 'Hard Brake',
    'Hard Brake': 'Hard Brake',
    'U Turn': 'U-Turn',
    'Camera Obstruction': 'Camera Obstruction',
    'Road Rage': 'Safety-Critical Event',
    'Camera Error': 'Camera Obstruction',
}
# action taken old-name -> coaching name (5 -> 5)
ACT = {
    'Sent Coaching Notes': 'Coaching Notes',
    'Connect and Coach': 'Face to Face',
    'Needs Additional Review': 'Critical Event',
    'Camera Needs Repaired': 'Blocked Camera',
    'Needs Additional Engagement': 'Face to Face',
}
# target name -> acceptable names on Mission 2 (handles not-yet-renamed labels)
SYN = {
    'Safety-Critical Event': ['Safety-Critical Event', 'Near Miss'],
    'Sign Violation': ['Sign Violation', 'Sign Vilolation'],
}

def opt_map(board, attr_id):
    for a in attrs(board):
        if a['id'] == attr_id:
            return {o['id']: o['name'] for o in (a.get('settings', {}).get('labels') or [])}
    return {}

def name_to_id(board, attr_id):
    return {v: k for k, v in opt_map(board, attr_id).items()}

def resolve(target, name2id):
    for cand in SYN.get(target, [target]):
        if cand in name2id:
            return name2id[cand], cand
    return None, None

def roster_fields(board):
    """name -> attr_id for attributes attached to Mission 2 roster folder."""
    det = folder_detail(board, NEW_ROSTER_FOLDER)
    ids = det.get('attribute_ids') or []
    out = {}
    for a in attrs(board):
        if a['id'] in ids:
            out[a['name']] = a
    return out

def all_attr_by_name(board):
    out = {}
    for a in attrs(board):
        out.setdefault(a['name'], a)   # first wins
    return out

def add_fields():
    print('Adding roster fields to Mission 2...')
    have = roster_fields(NEW)                 # name -> attr (already attached)
    existing = all_attr_by_name(NEW)          # name -> attr (anywhere on board)
    det = folder_detail(NEW, NEW_ROSTER_FOLDER)
    ids = list(det.get('attribute_ids') or [])
    created = []

    def ensure_id(idv):
        if idv and idv not in ids:
            ids.append(idv)

    # 1) Truck Number — attach existing board-level attr
    if 'Truck Number' not in have:
        ensure_id(N_TRUCK); created.append('Truck Number (attach existing)')
    # 2) text fields — reuse if already created, else create
    for nm in ['Personal Number', 'Company Number', 'Division']:
        if nm in have:
            continue
        if nm in existing:
            ensure_id(existing[nm]['id']); created.append(nm + ' (reattach)')
        else:
            st, r = api('POST', f'/workspaces/{WS}/boards/{NEW}/attributes',
                        {'name': nm, 'type': 'text', 'folder_id': NEW_ROSTER_FOLDER})
            ensure_id(r['id']); created.append(nm)
    # 3) Location label (each option needs an id)
    if 'Location' not in have:
        if 'Location' in existing:
            ensure_id(existing['Location']['id']); created.append('Location (reattach)')
        else:
            st, r = api('POST', f'/workspaces/{WS}/boards/{NEW}/attributes',
                        {'name': 'Location', 'type': 'label', 'folder_id': NEW_ROSTER_FOLDER,
                         'settings': {'multiple': False, 'allowNew': True, 'allowEmpty': True,
                                      'labels': [{'id': str(uuid.uuid4()), 'name': 'SA', 'color': '#B3EC8D'},
                                                 {'id': str(uuid.uuid4()), 'name': 'Houston', 'color': '#9FE1E7'}]}})
            if 'id' not in r:
                print('  LABEL CREATE FAILED:', json.dumps(r)[:300]); return
            ensure_id(r['id']); created.append('Location (label)')
    # attach everything
    api('PUT', f'/workspaces/{WS}/boards/{NEW}/folders/{NEW_ROSTER_FOLDER}', {'attribute_ids': ids})
    print('  created/attached:', created or '(nothing — already present)')
    print('  roster fields now:', list(roster_fields(NEW).keys()))

def build_plan():
    """Returns (drivers, events, skips) without writing."""
    old_drv = opt_map(OLD, O_DRIVER)      # opt_id -> driver name
    old_loc = opt_map(OLD, O_LOC)         # opt_id -> location name
    old_beh = opt_map(OLD, O_BEH)
    old_act = opt_map(OLD, O_ACT)
    n_beh = name_to_id(NEW, N_BEH)
    n_coach = name_to_id(NEW, N_COACH)

    # drivers
    drivers, dup = {}, 0
    for it in get_all_items(OLD, OLD_ROSTER_FOLDER):
        v = vmap(it)
        dv = v.get(O_DRIVER)
        if not dv:
            continue
        opt = dv[0]
        if is_open_placeholder(old_drv.get(opt, '')):
            continue  # OPEN placeholder is not a real driver
        if opt in drivers:
            dup += 1
        loc = v.get(O_LOC) or []
        drivers[opt] = {
            'name': old_drv.get(opt, '(unknown)'),
            'truck': v.get(O_TRUCK) or '',
            'personal': v.get(O_PERS) or '',
            'company': v.get(O_COMP) or '',
            'division': v.get(O_DIV) or '',
            'location': old_loc.get(loc[0]) if loc else '',
        }

    # events
    events, skips = [], {'not2026': 0, 'no_driver': 0, 'driver_unmatched': 0,
                         'no_action': 0, 'beh_unmapped': 0, 'act_unmapped': 0}
    for it in get_all_items(OLD, OLD_CAMERA_FOLDER):
        v = vmap(it)
        date = (v.get(O_DATE) or '')[:10]
        if not date.startswith('2026'):
            skips['not2026'] += 1; continue
        dv = v.get(O_DRIVER)
        if not dv:
            skips['no_driver'] += 1; continue
        opt = dv[0]
        if opt not in drivers:
            skips['driver_unmatched'] += 1; continue
        av = v.get(O_ACT)
        if not av:
            skips['no_action'] += 1; continue
        act_name = old_act.get(av[0], '')
        coach_target = ACT.get(act_name)
        if not coach_target or coach_target not in n_coach:
            skips['act_unmapped'] += 1; continue
        bv = v.get(O_BEH)
        beh_id = beh_name = None
        if bv:
            beh_target = BEH.get(old_beh.get(bv[0], ''))
            beh_id, beh_name = resolve(beh_target, n_beh) if beh_target else (None, None)
        if not beh_id:
            skips['beh_unmapped'] += 1; continue
        cnote = v.get(O_CNOTE) or ''
        mnote = v.get(O_MNOTE) or ''
        notes = '\n\n'.join(x for x in [cnote, mnote] if x and x.strip())
        events.append({
            'drv_opt': opt, 'driver': drivers[opt]['name'],
            'beh_id': beh_id, 'beh_name': beh_name,
            'coach_id': n_coach[coach_target], 'coach_name': coach_target,
            'date': date, 'reviewed': (v.get(O_REVD) or '')[:10], 'notes': notes,
        })
    return drivers, events, skips, dup

def is_open_placeholder(name):
    return (name or '').strip().upper() in ('OPEN', 'OPEN DRIVER', '(UNKNOWN)', '')

def build_full_plan():
    """Roster drivers (full) + off-roster drivers (name-only, OPEN skipped) + events."""
    roster, events, skips, dup = build_plan()  # roster=opt->full, events excludes off-roster
    old_drv = opt_map(OLD, O_DRIVER)
    old_beh = opt_map(OLD, O_BEH)
    old_act = opt_map(OLD, O_ACT)
    n_beh = name_to_id(NEW, N_BEH)
    n_coach = name_to_id(NEW, N_COACH)

    # second pass over events: rescue off-roster drivers (create name-only), skip OPEN
    offroster = {}
    open_skipped = 0
    for it in get_all_items(OLD, OLD_CAMERA_FOLDER):
        v = vmap(it)
        date = (v.get(O_DATE) or '')[:10]
        if not date.startswith('2026'):
            continue
        dv = v.get(O_DRIVER)
        if not dv:
            continue
        opt = dv[0]
        if opt in roster:
            continue  # already handled by build_plan -> events
        name = old_drv.get(opt, '')
        if is_open_placeholder(name):
            open_skipped += 1
            continue
        av = v.get(O_ACT)
        if not av:
            continue
        coach_target = ACT.get(old_act.get(av[0], ''))
        if not coach_target or coach_target not in n_coach:
            continue
        bv = v.get(O_BEH)
        beh_id = beh_name = None
        if bv:
            beh_target = BEH.get(old_beh.get(bv[0], ''))
            beh_id, beh_name = resolve(beh_target, n_beh) if beh_target else (None, None)
        if not beh_id:
            continue
        offroster.setdefault(opt, {'name': name, 'truck': '', 'personal': '',
                                   'company': '', 'division': '', 'location': ''})
        cnote = v.get(O_CNOTE) or ''
        mnote = v.get(O_MNOTE) or ''
        notes = '\n\n'.join(x for x in [cnote, mnote] if x and x.strip())
        events.append({
            'drv_opt': opt, 'driver': name,
            'beh_id': beh_id, 'beh_name': beh_name,
            'coach_id': n_coach[coach_target], 'coach_name': coach_target,
            'date': date, 'reviewed': (v.get(O_REVD) or '')[:10], 'notes': notes,
        })
    return roster, offroster, events, open_skipped

def do_execute():
    rf = roster_fields(NEW)
    F_TRUCK = rf['Truck Number']['id']
    F_PERS  = rf['Personal Number']['id']
    F_COMP  = rf['Company Number']['id']
    F_DIV   = rf['Division']['id']
    F_LOC   = rf['Location']['id']
    loc_n2i = {o['name']: o['id'] for o in (rf['Location'].get('settings', {}).get('labels') or [])}

    roster, offroster, events, open_skipped = build_full_plan()
    total_drivers = len(roster) + len(offroster)
    print(f'EXECUTE: {len(roster)} full drivers + {len(offroster)} name-only (OPEN skipped: {open_skipped})')
    print(f'         {len(events)} events to migrate')
    log = {'drivers': {}, 'events': [], 'refs': [], 'errors': []}

    def create_item(folder, vals):
        st, r = api('POST', f'/workspaces/{WS}/boards/{NEW}/items',
                    {'folder_id': folder, 'values': vals})
        item = r.get('data', r) if isinstance(r, dict) else {}
        return st, item.get('id'), r

    # ---- drivers ----
    opt2new = {}
    def driver_vals(d, full):
        vals = [{'attribute_id': N_DRVNAME, 'data': d['name']},
                {'attribute_id': N_NAME, 'data': d['name']}]
        if full:
            if d['truck']:    vals.append({'attribute_id': F_TRUCK, 'data': d['truck']})
            if d['personal']: vals.append({'attribute_id': F_PERS, 'data': d['personal']})
            if d['company']:  vals.append({'attribute_id': F_COMP, 'data': d['company']})
            if d['division']: vals.append({'attribute_id': F_DIV, 'data': d['division']})
            if d['location'] and d['location'] in loc_n2i:
                vals.append({'attribute_id': F_LOC, 'data': [loc_n2i[d['location']]]})
        return vals

    n = 0
    for opt, d in list(roster.items()) + [(o, dd) for o, dd in offroster.items()]:
        full = opt in roster
        st, iid, raw = create_item(NEW_ROSTER_FOLDER, driver_vals(d, full))
        if not iid:
            log['errors'].append({'driver': d['name'], 'resp': str(raw)[:200]})
            print(f'  !! driver FAIL {d["name"]}: {str(raw)[:120]}')
            continue
        opt2new[opt] = iid
        log['drivers'][opt] = {'name': d['name'], 'id': iid, 'full': full}
        n += 1
        if n % 10 == 0:
            print(f'  ...{n}/{total_drivers} drivers')
        time.sleep(0.05)
    print(f'  drivers created: {len(opt2new)}/{total_drivers}')

    # ---- events + references ----
    ev_ok = ref_ok = 0
    for i, e in enumerate(events, 1):
        drv_id = opt2new.get(e['drv_opt'])
        if not drv_id:
            log['errors'].append({'event': e, 'why': 'driver not created'})
            continue
        vals = [{'attribute_id': N_BEH, 'data': [e['beh_id']]},
                {'attribute_id': N_COACH, 'data': [e['coach_id']]},
                {'attribute_id': N_DATE, 'data': e['date']}]
        if e['reviewed']:
            vals.append({'attribute_id': N_REVD, 'data': e['reviewed']})
        if e['notes']:
            vals.append({'attribute_id': N_NOTES, 'data': e['notes']})
        st, iid, raw = create_item(NEW_CAMERA_FOLDER, vals)
        if not iid:
            log['errors'].append({'event': e, 'resp': str(raw)[:200]})
            print(f'  !! event FAIL {e["driver"]} {e["date"]}: {str(raw)[:120]}')
            continue
        ev_ok += 1
        log['events'].append(iid)
        # link driver
        rst, rr = api('POST', f'/workspaces/{WS}/boards/{NEW}/references',
                      {'attribute_id': N_REF, 'from_item_id': iid, 'to_item_id': drv_id})
        if rst in (200, 201):
            ref_ok += 1
            log['refs'].append(iid)
        else:
            log['errors'].append({'ref_for': iid, 'resp': str(rr)[:200]})
        if i % 25 == 0:
            print(f'  ...{i}/{len(events)} events  (refs ok: {ref_ok})')
        time.sleep(0.12)

    print(f'\n=== DONE ===  events: {ev_ok}/{len(events)}   driver-links: {ref_ok}/{ev_ok}   errors: {len(log["errors"])}')
    with open('migrate_log.json', 'w') as fh:
        json.dump(log, fh, indent=2)
    print('  full log -> migrate_log.json')
    if log['errors']:
        print('  first errors:', json.dumps(log['errors'][:3], indent=2)[:600])

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else '--introspect'
    if mode == '--introspect':
        show_board('OLD Mission Wrecker', OLD)
        show_board('NEW Mission 2', NEW)
    elif mode == '--add-fields':
        add_fields()
    elif mode == '--dry-run':
        drivers, events, skips, dup = build_plan()
        print(f'\n=== DRY RUN (no writes) ===')
        print(f'DRIVERS to create: {len(drivers)}  (duplicate-option rows collapsed: {dup})')
        for d in list(drivers.values())[:5]:
            print(f"   {d['name']:24} truck={d['truck']:6} loc={d['location']:8} "
                  f"pers={d['personal']} comp={d['company']} div={d['division']}")
        print(f'\nEVENTS (2026, with driver + mapped coaching) to migrate: {len(events)}')
        from collections import Counter
        print('  by behavior:', dict(Counter(e['beh_name'] for e in events)))
        print('  by coaching:', dict(Counter(e['coach_name'] for e in events)))
        print('  sample rows:')
        for e in events[:6]:
            print(f"   {e['date']}  {e['driver']:22} {e['beh_name']:22} -> {e['coach_name']:14} "
                  f"notes={len(e['notes'])}c")
        print('\n  SKIPPED:', skips)
    elif mode == '--rollback':
        log = json.load(open('migrate_log.json'))
        ev_ids = log.get('events', [])
        drv_ids = [d['id'] for d in log.get('drivers', {}).values()]
        print(f'Rolling back {len(ev_ids)} events + {len(drv_ids)} drivers...')
        ok = fail = 0
        for iid in ev_ids + drv_ids:
            st, _ = api('DELETE', f'/workspaces/{WS}/boards/{NEW}/items/{iid}')
            if st in (200, 204):
                ok += 1
            else:
                fail += 1
            time.sleep(0.04)
        print(f'  deleted: {ok}  failed: {fail}')
    elif mode == '--execute':
        do_execute()
    elif mode == '--probe':
        print('-- Mission 2 Driver Roster folder detail --')
        print(json.dumps(folder_detail(NEW, 'tRjA68oSQ5k'), indent=2)[:1500])
        print('\n-- OLD roster sample (3 items, values) --')
        ri = get_all_items(OLD, 'e6iHBci54G6')
        print(f'total old roster items: {len(ri)}')
        for it in ri[:3]:
            print(' ', it.get('id'), json.dumps(vmap(it)))
        print('\n-- OLD camera events sample (3 items, values) --')
        ev = get_all_items(OLD, 'nA8R3U1XKtM')
        print(f'total old camera events: {len(ev)}')
        for it in ev[:3]:
            print(' ', it.get('id'), json.dumps(vmap(it))[:400])
