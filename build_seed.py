#!/usr/bin/env python3
"""Build seed.json for the Camera Management app.
Pulls, per camera board: driver field (reference roster OR label), driver list,
camera attribute mapping, and recent camera events. Robust: skips what it can't map.
"""
import json, sys, re, pathlib, hashlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'bin'))
import infinity as inf

HERE = pathlib.Path(__file__).parent

# (workspace, board_id, display_name) — the camera boards
BOARDS = [
    ('DEN','8gejhhHJj4e','Fiore & Sons'),
]
if '--all' in sys.argv:
    BOARDS = [
        ('DEN','8BUntjK1TqV','Panhandle Express'),
        # Apex Waste (VAixNEe3Cb5) removed — accident tracking only, no cameras
        ('DEN','XVLVu2Du8hc','PCS Trucking'),
        ('DEN','4rNDuSrCaap','All City Tow'),
        ('DEN','MfEUxnTRUV9','Mission Wrecker'),
        ('DEN','KYqKJWuumPm','Express Tow and Recovery'),
        # Andrew Distribution (JxcyoKbX2zw) removed — board being deleted, not used
        ('DEN','5gVKeGRDf8U','Alandon Tow'),
        ('DEN','MZerRFmhSHa','Starkey Trash Service'),
        # Apple Towing (rXWFWcd75XL) removed — account ends 2026-06-30
        ('DEN','81dVf6myW6q','Garmat USA'),
        ('DEN','ebSND1QoyBs','PEP MOVE - Bristlecone'),
        ('DEN','8gejhhHJj4e','Fiore & Sons'),
        ('DEN','xMfRLnqAN7y','NextDriv'),
        ('DEN','YJNwKvzFhkj','Aero Flex Logistix'),
    ]

# Per-board overrides for hand-built boards whose fields don't auto-detect.
# These boards pick the driver via a LABEL ("<Customer> Roster"), with driver
# names stored as the label's options — not via a roster reference or text field.
OVERRIDES = {
    'MfEUxnTRUV9': {  # Mission Wrecker
        'driver_attr': 'b3271170-6d5f-4162-8169-542eba0ebeed',  # "Mission Wrecker Roster List" label
        'driver_type': 'label',
        'attr': {
            'date':     '6028e889-c5a3-4694-be45-175582536ae9',  # Date Event Occurred (auto-pick grabbed Reviewed)
            'coaching': None,  # board has no "Coaching Needed" label yet — needs adding during cleanup
        },
    },
    '5gVKeGRDf8U': {  # Alandon Tow
        'driver_attr': '18551c98-7fe7-42bf-b000-43a3e813d815',  # "Alandon Tow Roster" label
        'driver_type': 'label',
    },
    '4rNDuSrCaap': {  # All City Tow — TWO roster attrs; auto-detect grabs the wrong
        # "Driver Roster" (1ade285d, 140 "Last,First"). Pin the real one + attrs.
        'camera_folder': 'a6WNieruvo8',
        'driver_attr': 'aacdaf03-b809-42a4-a8e5-1c96d720db51',  # "All City Tow Driver Roster" (69)
        'driver_type': 'label',
        'attr': {
            'date':     '87824913-df27-41cc-8d74-e4f26f7ae380',  # Camera Event Date
            'reviewed': '1b63e265-30cd-4438-956f-af0276be9d9f',  # Date Event Reviewed
            'behavior': 'c7ce22a6-d4ab-4d08-ab9f-e2b78a5acc8a',  # Behavior Observed
            'coaching': '4474fabe-b947-4dda-9079-0521e04fd49d',  # Coaching Needed
            'notes':    '6a079894-333c-468a-a4ae-eeff38c101fb',  # Notes: longtext
        },
    },
    'JthqRmXvJ9v': {  # T-Miller — auto-detect grabbed empty "Driver Roster" (0 opts)
        # over the real "T-Miller Driver List" (22 opts) events populate.
        'camera_folder': '9UzRRPDdiaq',
        'driver_attr': '019a7b18-0863-7330-ad9a-9618258e485b',  # "T-Miller Driver List"
        'driver_type': 'label',
        'attr': {
            'date':     '1f2c5cfe-6489-481e-a9b4-ef3d7ee57fc2',  # Date Event Occurred
            'reviewed': 'c02edb6d-4c67-4a47-b699-da6a9c222c79',  # Date Event was Reviewed
            'behavior': '72361b2f-ff3f-400a-8028-e87e7681f64e',  # Behavior Observed
            'coaching': 'fe911153-7172-4d51-b827-0cc7f9aa420a',  # Coaching Needed
            'notes':    '10abe1d3-1186-48f0-a84a-9ef5966545cf',  # Coaching Note longtext
        },
    },
    'XVLVu2Du8hc': {  # PCS Trucking — FIVE roster attrs; auto-detect grabs a big
        # "Driver Roster" over the real "PCS Driver Roster" (71) events populate.
        'camera_folder': 'fdP5zPifaYY',
        'driver_attr': '019a0810-437c-7aae-88b4-3ba95ac836e3',  # "PCS Driver Roster"
        'driver_type': 'label',
        'attr': {
            'date':     'fe479dd5-9cea-4e46-8f67-206316be702c',  # Camera Event Date
            'reviewed': '179dd595-9033-467c-aa3d-67f0294b73d2',  # Date Event Reviewed
            'behavior': '9a3de765-06b3-48c2-bb8b-f1955b2ccfbe',  # Behavior Observed
            'coaching': 'ce659933-85c7-4282-95c3-b1d86eb991b3',  # Coaching Needed
            'notes':    '7f7a53e2-b8ea-4574-b8bb-53ca4c657130',  # Notes: longtext
        },
    },
    'ebSND1QoyBs': {  # PEP MOVE - Bristlecone — REFERENCE-driver board (shadow backfilled).
        'camera_folder': 'oFakNYGVJxt',
        'driver_attr': '17e7527d-da1e-4fc1-b3f3-ac3396babec5',  # reference "Driver Roster"
        'driver_type': 'reference',
        'driver_name_attr': '13167e24-a78a-4e02-a1dc-7d7852059838',  # text "Driver Name" shadow
        'attr': {
            'date':     '8a1db309-89a0-4a8e-8a87-9e8cde8b0463',  # Camera Event Date
            'reviewed': '6af016e9-e5c9-450b-8c0f-d39ff23d5854',  # Date Event Reviewed
            'behavior': '4a577d28-c661-4f7a-9089-c37541f68fca',  # Behavior Observed 2 (populated one)
            'coaching': '4e5e1ec9-2d88-419a-b2e1-1acc81cfefa7',  # Coaching Needed
            'notes':    '0dad4f6b-1977-4c30-af51-c99ee4ee3f55',  # Coaching Notes longtext
        },
    },
}

def ws_id(ws): return inf.WS[ws]

def pick_attr(attrs, *needles):
    for a in attrs:
        n=(a.get('name') or '').lower()
        if all(x in n for x in needles): return a
    return None

# type-filtered picker: coaching must be a choice/label ("Action Taken"), never a
# free-text notes field containing "coaching" (that's how ATR resolved to a URL);
# notes must be the longtext field, never a short-text "Sent Coaching Notes?" flag
def pick_type_attr(attrs, atype, *needles):
    for a in attrs:
        n=(a.get('name') or '').lower()
        if a.get('type')==atype and all(x in n for x in needles): return a
    return None

def pick_label_attr(attrs, *needles):
    return pick_type_attr(attrs, 'label', *needles)

def val_for(item, attr_id):
    for v in item.get('values', []):
        if v.get('attribute_id')==attr_id:
            return v.get('data')
    return None

def strip_html(s):
    if not isinstance(s,str): return s
    return re.sub(r'<[^>]+>','',s).replace('&amp;','&').strip()

def resolve(data, lmap):
    """label id(s) -> name(s); HTML/text -> clean text."""
    if isinstance(data,list):
        return ', '.join(lmap.get(x,strip_html(x)) for x in data if x is not None) or None
    if isinstance(data,str):
        return lmap.get(data, strip_html(data)) or None
    return data

def build_board(ws, b, name):
    wid = ws_id(ws)
    attrs = inf.attributes(wid, b)
    folders = inf.folders(wid, b)
    cam = next((f for f in folders if 'camera' in (f.get('name') or '').lower()), None)
    rec = {'ws':ws,'board':b,'name':name,'camera_folder': cam and cam['id']}

    # driver field. Two working shapes:
    #  - LABEL roster: names live as label options, readable straight off events.
    #  - REFERENCE roster (the Master template): a shared "Driver Roster" folder
    #    linked from every workflow. The API can't read a reference value off an
    #    event, so a reference-driver board ALSO carries a "Driver Name" text
    #    shadow the app stamps on write and we read here. Detect the reference
    #    roster by name ("driver"+"roster") so we never grab a decoy label like
    #    "Driver's Driver Manager"/"Type of Driver".
    drv_ref = (pick_label_attr(attrs,'driver','roster')
               or pick_type_attr(attrs,'reference','driver','roster')
               or pick_label_attr(attrs,'driver name') or pick_label_attr(attrs,'driver')
               or pick_attr(attrs,'driver','roster') or pick_attr(attrs,'driver name') or pick_attr(attrs,'driver'))
    rec['driver_attr'] = drv_ref and drv_ref['id']
    rec['driver_type'] = drv_ref and drv_ref.get('type')
    # reference roster => read the driver name off the text shadow, not the ref.
    rec['driver_name_attr'] = ((pick_type_attr(attrs,'text','driver','name') or {}).get('id')
                               if (drv_ref and drv_ref.get('type')=='reference') else None)

    # camera attribute mapping
    rec['attr'] = {
        'date':     (pick_attr(attrs,'camera','date') or pick_attr(attrs,'event','date') or {}).get('id'),
        'behavior': (pick_attr(attrs,'behavior') or {}).get('id'),
        'coaching': (pick_label_attr(attrs,'coaching','needed') or pick_label_attr(attrs,'action','taken') or pick_label_attr(attrs,'coaching') or {}).get('id'),
        'reviewed': (pick_attr(attrs,'event','reviewed') or pick_attr(attrs,'reviewed') or {}).get('id'),
        'notes':    (pick_type_attr(attrs,'longtext','note') or pick_attr(attrs,'note') or {}).get('id'),
    }
    # per-board overrides for hand-built boards that don't auto-map
    ov = OVERRIDES.get(b)
    if ov:
        if ov.get('driver_attr'):
            rec['driver_attr'] = ov['driver_attr']
            rec['driver_type'] = ov.get('driver_type')
            drv_ref = next((a for a in attrs if a['id']==ov['driver_attr']), drv_ref)
        if 'driver_name_attr' in ov: rec['driver_name_attr'] = ov['driver_name_attr']
        for k,v in (ov.get('attr') or {}).items():
            rec['attr'][k] = v

    # behavior label choices
    bev = pick_attr(attrs,'behavior')
    rec['behaviors'] = [l.get('name') for l in ((bev or {}).get('settings',{}) or {}).get('labels',[])] if bev else []

    # drivers
    drivers=[]
    if drv_ref and drv_ref.get('type')=='label':
        labels=((drv_ref.get('settings',{}) or {}).get('labels',[]))
        for l in labels:
            if not inf.is_placeholder(l.get('name')):
                drivers.append({'id':l.get('id'),'name':l.get('name')})
    else:
        # reference: roster items
        roster = next((f for f in inf.driver_rosters(folders)), None)
        rec['roster_folder']= roster and roster['id']
        if roster:
            items = inf.call('GET', f'/workspaces/{wid}/boards/{b}/items',
                             params={'folder_id':roster['id'],'expand[]':'values','per_page':300}).get('data',[])
            # name attr = first label-ish attr on roster, fallback to drv_ref id
            for it in items:
                nm=None
                for v in it.get('values',[]):
                    d=v.get('data')
                    if isinstance(d,str) and d.strip():
                        nm=d.strip(); break
                if nm and not inf.is_placeholder(nm):
                    drivers.append({'id':it.get('id'),'name':nm})
    # dedup + sort canonical A-Z
    seen=set(); uniq=[]
    for d in drivers:
        k=d['name'].lower()
        if k in seen: continue
        seen.add(k); uniq.append(d)
    uniq.sort(key=lambda d:d['name'].lower())
    rec['drivers']=uniq

    # recent camera events (capped)
    events=[]
    if cam:
        items = inf.call('GET', f'/workspaces/{wid}/boards/{b}/items',
                         params={'folder_id':cam['id'],'expand[]':'values','per_page':200}).get('data',[])
        a=rec['attr']
        # label id -> name maps for behavior, coaching, driver(label boards)
        bmap={l.get('id'):l.get('name') for l in ((pick_attr(attrs,'behavior') or {}).get('settings',{}) or {}).get('labels',[])}
        cmap={l.get('id'):l.get('name') for l in (next((x for x in attrs if x.get('id')==a['coaching']),{}) or {}).get('settings',{}).get('labels',[]) } if a['coaching'] else {}
        idname={d['id']:d['name'] for d in uniq}
        for it in items:
            dname=None
            # reference-roster board: readable name lives on the text shadow
            # ("Driver Name"); the reference itself comes back empty from the API.
            if rec.get('driver_name_attr'):
                nv=val_for(it, rec['driver_name_attr'])
                if isinstance(nv,str) and nv.strip(): dname=nv.strip()
            if dname is None:
                draw = val_for(it, rec['driver_attr'])
                if isinstance(draw,list) and draw: dname=idname.get(draw[0]) or idname.get(draw[0])
                elif isinstance(draw,str): dname=idname.get(draw) or draw
            ev={
                'driver': dname,
                'date': val_for(it,a['date']),
                'behavior': resolve(val_for(it,a['behavior']), bmap),
                'coaching': resolve(val_for(it,a['coaching']), cmap),
                'reviewed': val_for(it,a['reviewed']),
                'item': it.get('id'),
            }
            if ev['date'] or ev['behavior'] or ev['driver']:
                events.append(ev)
    rec['events']=events
    return rec

def main():
    out=[]
    for ws,b,name in BOARDS:
        try:
            r=build_board(ws,b,name)
            out.append(r)
            print(f"OK  {name:32} type={r['driver_type']:9} drivers={len(r['drivers']):3} events={len(r['events']):3} attrs={ {k:bool(v) for k,v in r['attr'].items()} }", file=sys.stderr)
        except Exception as e:
            print(f"ERR {name}: {e}", file=sys.stderr)
    coaching=['Coaching Notes','Critical Event','Blocked Camera','Unidentified Driver']
    # Version = hash of the actual board content (NOT a frozen date). This value is
    # written into SEED.generated, and the app wipes its per-browser cam_refreshed
    # cache whenever SEED.generated changes (index.html applyRefreshCache). A frozen
    # 'generated' meant that wipe NEVER fired, so stale per-browser board snapshots
    # could resurrect removed boards forever -> different people saw different boards.
    # Hashing the content makes it change exactly when the board set does.
    ver=hashlib.md5(json.dumps([out,coaching],ensure_ascii=False).encode()).hexdigest()[:8]
    seed={'generated':ver,'boards':out,'coaching_types':coaching}
    (HERE/'seed.json').write_text(json.dumps(seed,indent=2,ensure_ascii=False))
    # seed.js lets index.html load data under file:// (no server / no fetch)
    seedjs='window.SEED = ' + json.dumps(seed,ensure_ascii=False) + ';\n'
    (HERE/'seed.js').write_text(seedjs)
    # Stamp the same version into index.html's <script src> so every rebuild produces a
    # fresh seed.js?v=<ver> URL. A changed URL can't match a browser's old cache entry,
    # so this evicts anyone holding a stale seed.js. Unchanged content -> same ver -> 304.
    idx=HERE/'index.html'
    idx.write_text(re.sub(r'seed\.js\?v=[0-9a-f]+', f'seed.js?v={ver}', idx.read_text()))
    print(f"\nwrote seed.json + seed.js ({len(out)} boards), stamped index.html seed-ver={ver}", file=sys.stderr)

if __name__ == '__main__':
    main()
