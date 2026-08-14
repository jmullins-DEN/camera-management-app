import json,urllib.request,re,sys
WB=json.load(open('wb.json'))
API='https://camera-management-api.jmullins-af4.workers.dev'
KEY='yesryx5p-YO3gCFXNTTdO1ttAGaV8Flw'
# Fiore orphan-driver corrections
DRIVER_FIX={'ND1783516713348897':'019f1fa4-4d09-73de-8f47-8efba7958563',  # Efrain Sotelo
            'ND1783599144750936':'26632b8b-ec9f-45a3-93d5-f74b14a04cad'}  # William Esslinger (created)
def linkifyNotes(t):
    if not t: return t
    # Store bare URLs — Infinity board view shows raw [url](url) brackets, not a link.
    return re.sub(r'\[(https?://[^\]\s]+)\]\((https?://[^)\s]+)\)', r'\2', t)
def post(path,body):
    r=urllib.request.Request(API+path,data=json.dumps(body).encode(),
        headers={'Content-Type':'application/json','X-App-Key':KEY,'User-Agent':'Mozilla/5.0 (denvision-flush)','Origin':'https://camera-management-app.pages.dev'},method='POST')
    return json.load(urllib.request.urlopen(r,timeout=60))
def build_values(ev,wb):
    v=[]
    blab=wb['behavior_labels'].get(ev.get('behavior')); 
    if blab: v.append({'attribute_id':wb['behavior_attr'],'data':[blab]})
    clab=wb['coaching_labels'].get(ev.get('coaching'))
    if clab: v.append({'attribute_id':wb['coaching_attr'],'data':[clab]})
    if ev.get('date'): v.append({'attribute_id':wb['date_attr'],'data':ev['date']})
    if ev.get('reviewed'): v.append({'attribute_id':wb['reviewed_attr'],'data':ev['reviewed']})
    if ev.get('notes'): v.append({'attribute_id':wb['notes_attr'],'data':linkifyNotes(ev['notes'])})
    did=DRIVER_FIX.get(ev.get('driverId'), ev.get('driverId'))
    if did: v.append({'attribute_id':wb['driver_attr'],'data':[did]})
    return v,did

ONLY=sys.argv[1] if len(sys.argv)>1 else None   # board id to restrict (canary)
st=json.load(open('camera-state.json')); local=st['local']
targets=[e for e in local if not e.get('synced') and e.get('board') in WB and (ONLY is None or e.get('board')==ONLY)]
print(f"pushing {len(targets)} events"+(f" (canary {ONLY})" if ONLY else ""))
idx={id(e):e for e in local}
ok=0;fail=0;results=[]
for e in targets:
    wb=WB[e['board']]
    values,did=build_values(e,wb)
    try:
        res=post('/item',{'board':e['board'],'folder_id':wb['cam_folder'],'values':values})
        iid=(res.get('item') or {}).get('id')
        if not res.get('ok') or not iid: raise Exception('bad resp '+json.dumps(res)[:200])
        e['infItemId']=iid; e['synced']=True; e['syncError']=None
        if did!=e.get('driverId'): e['driverId']=did
        ok+=1; results.append((e['driver'],iid))
    except Exception as ex:
        e['syncError']=str(ex); fail+=1; results.append((e.get('driver'),'FAIL:'+str(ex)[:120]))
        print("  FAIL",e.get('driver'),ex)
# persist state + entered
ent=set(st.get('entered',[]))
for e in targets:
    if e.get('synced') and e.get('infItemId'): ent.add(e['infItemId'])
st['entered']=list(ent)
json.dump(st,open('camera-state.json','w'))
print(f"OK {ok}  FAIL {fail}")
for r in results[:5]: print("   ",r)
