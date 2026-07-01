#!/usr/bin/env python3
"""Backfill the "Driver Name" text shadow on reference-driver camera boards.

Reads reference links via the /references endpoint (which the inline item API
can't see), resolves each event's driver to a roster name, and stamps the
driver_name_attr shadow on events that lack it. Idempotent; --dry-run prints
the plan and writes nothing.
"""
import json, sys, time, urllib.request, urllib.parse

TOK = open('/home/johnny/.config/openclaw-infinity/token').read().strip()
WS = '59792'  # DEN
BASE = 'https://app.startinfinity.com/api/v2'

BOARDS = {
    'Bectin': dict(board='YfVHuM3X87v', cam='ypQn6acB7cx', roster='V2wkgfAEjaq',
                   ref='0a06cad2-34e2-41d7-a2e6-8f37c2336e3b',
                   shadow='32053a34-2bc2-499b-a8ec-f0071b93a20b',
                   name='32053a34-2bc2-499b-a8ec-f0071b93a20b'),
    'Mission': dict(board='7W2SQKrNcXQ', cam='C8fbgdCmqQ2', roster='tRjA68oSQ5k',
                    ref='2be1b7b7-34f4-45d9-9710-e26a669fa286',
                    shadow='61f47954-3a5e-44ae-9319-44fd8a6db756',
                    name='61f47954-3a5e-44ae-9319-44fd8a6db756'),
    'PEP': dict(board='ebSND1QoyBs', cam='oFakNYGVJxt', roster='9N9CHgHiTNg',
                ref='17e7527d-da1e-4fc1-b3f3-ac3396babec5',
                shadow='13167e24-a78a-4e02-a1dc-7d7852059838',
                name='13167e24-a78a-4e02-a1dc-7d7852059838'),
}


def api(path, method='GET', body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Bearer {TOK}')
    req.add_header('Accept', 'application/json')
    if data:
        req.add_header('Content-Type', 'application/json')
    for attempt in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2 * (attempt + 1)); continue
            raise


def page_all(path):
    """Paginate a list endpoint via has_more/after cursor."""
    out, after = [], None
    while True:
        sep = '&' if '?' in path else '?'
        p = path + (f'{sep}after={urllib.parse.quote(after)}' if after else '')
        r = api(p)
        out.extend(r.get('data', []))
        if not r.get('has_more'):
            break
        after = r.get('after')
        if not after:
            break
    return out


def run(name, cfg, dry):
    b, cam, roster = cfg['board'], cfg['cam'], cfg['roster']
    ref, shadow, nameattr = cfg['ref'], cfg['shadow'], cfg['name']

    # 1. roster item -> driver name
    roster_items = page_all(f'/workspaces/{WS}/boards/{b}/items?folder_id={roster}&expand[]=values&per_page=100')
    rmap = {}
    for it in roster_items:
        nm = None
        for v in it.get('values', []):
            if v['attribute_id'] == nameattr and isinstance(v.get('data'), str) and v['data'].strip():
                nm = v['data'].strip()
        if nm:
            rmap[it['id']] = nm

    # 2. references: event(from) -> roster(to), filtered to the driver ref attr
    refs = page_all(f'/workspaces/{WS}/boards/{b}/references?per_page=100')
    ev2roster = {r['from_item_id']: r['to_item_id'] for r in refs if r['attribute_id'] == ref}

    # 3. camera events: which already have a shadow value
    events = page_all(f'/workspaces/{WS}/boards/{b}/items?folder_id={cam}&expand[]=values&per_page=100')

    plan, already, orphan, noref = [], 0, 0, 0
    for ev in events:
        has_shadow = any(v['attribute_id'] == shadow and isinstance(v.get('data'), str) and v['data'].strip()
                         for v in ev.get('values', []))
        if has_shadow:
            already += 1; continue
        rid = ev2roster.get(ev['id'])
        if not rid:
            noref += 1; continue
        nm = rmap.get(rid)
        if not nm:
            orphan += 1; continue
        plan.append((ev['id'], nm))

    print(f"\n=== {name} ({b}) ===")
    print(f"  roster drivers: {len(rmap)} | events: {len(events)} | ref links: {len(ev2roster)}")
    print(f"  already shadowed: {already} | to backfill: {len(plan)} | orphan(deleted driver): {orphan} | no ref link: {noref}")
    from collections import Counter
    for nm, c in Counter(n for _, n in plan).most_common():
        print(f"    {c:4d}  {nm}")

    if dry or not plan:
        return
    ok = 0
    for eid, nm in plan:
        api(f'/workspaces/{WS}/boards/{b}/items/{eid}', 'PUT',
            {'values': [{'attribute_id': shadow, 'data': nm}]})
        ok += 1
    print(f"  WROTE {ok} shadows")


if __name__ == '__main__':
    dry = '--write' not in sys.argv
    which = [a for a in sys.argv[1:] if not a.startswith('-')]
    for name, cfg in BOARDS.items():
        if which and name not in which:
            continue
        run(name, cfg, dry)
    print("\n(dry run — pass --write to apply)" if dry else "\nDONE")
