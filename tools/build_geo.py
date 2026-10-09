import json,math,sys
rows=json.load(open('/tmp/osm_rows.json'))
def polys(g):
    t=g['type']
    if t=='Polygon': return [g['coordinates']]
    if t=='MultiPolygon': return g['coordinates']
    if t=='GeometryCollection': return [p for x in g['geometries'] for p in polys(x)]
    return []
def pip(x,y,ring):
    c=False;n=len(ring);j=n-1
    for i in range(n):
        xi,yi=ring[i];xj,yj=ring[j]
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:c=not c
        j=i
    return c
def inpoly(x,y,P): return any(pip(x,y,p[0]) and not any(pip(x,y,h) for h in p[1:]) for p in P)
def area(P):
    a=0
    for p in P:
        for k,r in enumerate(p):
            s=sum(r[i][0]*r[(i+1)%len(r)][1]-r[(i+1)%len(r)][0]*r[i][1] for i in range(len(r)))/2
            a+= abs(s) if k==0 else -abs(s)
    return abs(a)
F=[]
for r in rows:
    P=polys(json.loads(r['gj']))
    if P: F.append(dict(name=r['name'],al=r['al'],P=P,clat=float(r['clat']),clon=float(r['clon']),area=area(P)))
cities=[f for f in F if f['al']=='8'];bairros=[f for f in F if f['al']=='10' and not f['name'].isdigit()]
for b in bairros:
    b['city']=next((c['name'] for c in cities if inpoly(b['clon'],b['clat'],c['P'])),'')
bairros=[b for b in bairros if b['city']]
bairros.sort(key=lambda b:b['area'])
def enc(P):
    out=[]
    for p in P:
        for r in p:
            px=py=0;a=[]
            for lon,lat in r:
                X=round(lon*1e4);Y=round(lat*1e4);a+=[X-px,Y-py];px,py=X,Y
            out.append(a)
    return out
data={'c':[[c['name'],enc(c['P']),round(c['clat'],4),round(c['clon'],4)] for c in cities],
      'b':[[b['name'],b['city'],enc(b['P']),round(b['clat'],4),round(b['clon'],4)] for b in bairros]}
s=json.dumps(data,ensure_ascii=False,separators=(',',':'))
print(len(cities),len(bairros),len(s))
import collections;print(collections.Counter(b['city'] for b in bairros))
open('/tmp/pdgeo.json','w').write(s)
