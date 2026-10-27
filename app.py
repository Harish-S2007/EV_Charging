from flask import Flask, render_template, request, jsonify
import heapq, math, copy

app = Flask(__name__)

# Demonstration data only. Coordinates are approximate illustrative locations in Vellore, Tamil Nadu.
NODES = {
 'Home': {'lat':12.9165,'lng':79.1325,'kind':'ev'},
 'Junction A': {'lat':12.9230,'lng':79.1370,'kind':'road'},
 'Junction B': {'lat':12.9290,'lng':79.1450,'kind':'road'},
 'City Center': {'lat':12.9200,'lng':79.1500,'kind':'road'},
 'Solar Hub': {'lat':12.9360,'lng':79.1260,'kind':'renewable'},
 'Wind Hub': {'lat':12.9400,'lng':79.1530,'kind':'renewable'},
 'Substation A': {'lat':12.9320,'lng':79.1340,'kind':'grid'},
 'Substation B': {'lat':12.9250,'lng':79.1590,'kind':'grid'},
 'Battery Store': {'lat':12.9440,'lng':79.1400,'kind':'battery'},
 'Station North': {'lat':12.9410,'lng':79.1330,'kind':'station'},
 'Station Central': {'lat':12.9230,'lng':79.1460,'kind':'station'},
 'Station South': {'lat':12.9100,'lng':79.1510,'kind':'station'},
}
# Road graph; each edge stores distance km, travel minutes, cost index, carbon index.
ROAD_EDGES = [
 ('Home','Junction A',1.2,4,2.2,1.5),('Home','City Center',2.8,9,2.8,2.1),
 ('Junction A','Junction B',1.7,5,1.8,1.2),('Junction A','City Center',1.5,5,1.5,1.0),
 ('Junction B','Station North',1.1,4,1.1,.8),('Junction B','Station Central',1.6,6,1.4,1.0),
 ('City Center','Station Central',.7,3,.8,.5),('City Center','Station South',2.1,7,1.8,1.3),
 ('Station Central','Station South',2.0,7,1.7,1.2),('Substation A','Station North',1.0,3,.5,.4),
 ('Substation A','Station Central',1.8,6,.8,.6),('Substation B','Station Central',1.3,4,.6,.4),
 ('Substation B','Station South',1.0,3,.5,.4),('Solar Hub','Substation A',1.2,4,.2,.1),
 ('Wind Hub','Substation B',1.5,5,.3,.2),('Battery Store','Substation A',1.0,3,.2,.1),
 ('Battery Store','Substation B',1.7,5,.3,.2),('Junction B','Substation A',1.1,4,.7,.5),
 ('City Center','Substation B',1.4,5,.7,.5),('Station North','Station Central',2.2,8,1.8,1.3),
]
STATIONS = [
 {'id':'north','name':'Station North','lat':12.9410,'lng':79.1330,'ports':4,'free':2,'price':18.0,'wait':8,'renewable':72,'grid_load':42,'carbon':0.24,'battery_impact':0.18,'connectors':['CCS2','Type 2'],'coverage':['North','West']},
 {'id':'central','name':'Station Central','lat':12.9230,'lng':79.1460,'ports':6,'free':3,'price':21.0,'wait':5,'renewable':38,'grid_load':68,'carbon':0.42,'battery_impact':0.12,'connectors':['CCS2','CHAdeMO','Type 2'],'coverage':['Central','West','East']},
 {'id':'south','name':'Station South','lat':12.9100,'lng':79.1510,'ports':3,'free':1,'price':16.5,'wait':12,'renewable':55,'grid_load':35,'carbon':0.29,'battery_impact':0.24,'connectors':['CCS2','Type 2'],'coverage':['South','East']},
]
EVS = [
 {'id':'EV-01','soc':12,'capacity':60,'deadline':35,'connector':'CCS2','emergency':True,'region':'North'},
 {'id':'EV-02','soc':28,'capacity':45,'deadline':55,'connector':'Type 2','emergency':False,'region':'Central'},
 {'id':'EV-03','soc':41,'capacity':75,'deadline':70,'connector':'CCS2','emergency':False,'region':'South'},
 {'id':'EV-04','soc':18,'capacity':50,'deadline':30,'connector':'CHAdeMO','emergency':True,'region':'East'},
 {'id':'EV-05','soc':53,'capacity':40,'deadline':90,'connector':'Type 2','emergency':False,'region':'West'},
]
SUPPLY = [('Solar Hub','Substation A',32,1),('Wind Hub','Substation B',24,2),('Battery Store','Substation A',18,3),('Substation A','Station North',20,2),('Substation A','Station Central',16,3),('Substation B','Station Central',12,2),('Substation B','Station South',18,2)]
CONFLICTS = [('EV-01','EV-02'),('EV-01','EV-03'),('EV-02','EV-04'),('EV-03','EV-04'),('EV-04','EV-05')]

def graph():
    g={n:[] for n in NODES}
    for a,b,d,t,c,co in ROAD_EDGES:
        w={'distance':d,'time':t,'cost':c,'carbon':co}
        g[a].append((b,w)); g[b].append((a,w))
    return g

def shortest_path(start, goal, weights):
    g=graph(); dist={n:float('inf') for n in g}; prev={}; dist[start]=0; pq=[(0,start)]
    for_cost=lambda e: e['distance']*weights['distance'] + e['time']*weights['time'] + e['cost']*weights['cost'] + e['carbon']*weights['carbon']
    while pq:
        d,u=heapq.heappop(pq)
        if d!=dist[u]: continue
        if u==goal: break
        for v,e in g[u]:
            nd=d+for_cost(e)
            if nd<dist[v]: dist[v]=nd; prev[v]=u; heapq.heappush(pq,(nd,v))
    if dist[goal]==float('inf'): return None
    path=[]; cur=goal
    while cur!=start: path.append(cur); cur=prev[cur]
    path.append(start); path.reverse()
    metrics={'distance':0,'time':0,'cost':0,'carbon':0}
    lookup={}
    for a,b,d,t,c,co in ROAD_EDGES: lookup[(a,b)]={'distance':d,'time':t,'cost':c,'carbon':co}; lookup[(b,a)]=lookup[(a,b)]
    for a,b in zip(path,path[1:]):
        for k,val in lookup[(a,b)].items(): metrics[k]+=val
    return {'path':path,'score':round(dist[goal],2),'metrics':{k:round(v,2) for k,v in metrics.items()}}

def matching(evs, stations):
    ports=[]
    for s in stations:
        for i in range(s['free']): ports.append((s['name'],i,s['connectors']))
    adj={e['id']:[j for j,p in enumerate(ports) if e['connector'] in p[2]] for e in evs}
    owner={}
    def augment(ev,seen):
        for j in adj[ev]:
            if j in seen: continue
            seen.add(j)
            if j not in owner or augment(owner[j],seen): owner[j]=ev; return True
        return False
    order=sorted(evs,key=lambda e:(not e['emergency'],e['soc'],e['deadline']))
    for e in order: augment(e['id'],set())
    assigned=[]
    for j,ev in owner.items(): assigned.append({'ev':ev,'station':ports[j][0],'port':ports[j][1]+1})
    assigned.sort(key=lambda x:x['ev'])
    return {'assignments':assigned,'unassigned':[e['id'] for e in evs if e['id'] not in {a['ev'] for a in assigned}], 'matched':len(assigned)}

def color_schedule():
    adj={e['id']:set() for e in EVS}
    for a,b in CONFLICTS: adj[a].add(b); adj[b].add(a)
    colors={}
    for ev in sorted(adj,key=lambda x:len(adj[x]),reverse=True):
        used={colors[n] for n in adj[ev] if n in colors}; c=0
        while c in used: c+=1
        colors[ev]=c
    return [{'ev':e,'slot':f'Slot {colors[e]+1}'} for e in sorted(colors)]

def min_cost_flow():
    # Successive shortest augmenting paths using Bellman-Ford; reverse residual edges may be negative.
    names=list(NODES); idx={n:i for i,n in enumerate(names)}; n=len(names); src=n; sink=n+1; N=n+2
    adj=[[] for _ in range(N)]
    def add(u,v,cap,cost,label):
        adj[u].append([v,cap,cost,len(adj[v]),label]); adj[v].append([u,0,-cost,len(adj[u])-1,'reverse'])
    # Renewable/battery source capacities
    add(src,idx['Solar Hub'],32,0,'solar supply'); add(src,idx['Wind Hub'],24,0,'wind supply'); add(src,idx['Battery Store'],18,0,'battery supply')
    # supply network arcs, cost is a simplified loss/congestion index
    for a,b,cap,cost in SUPPLY: add(idx[a],idx[b],cap,cost,f'{a} → {b}')
    for s in STATIONS: add(idx[s['name']],sink,max(0,s['free']*8),max(1,round(s['grid_load']/25)),f'{s["name"]} demand')
    flow=0; total=0; paths=[]; target=48
    while flow<target:
        dist=[float('inf')]*N; parent=[None]*N; dist[src]=0
        for _ in range(N-1):
            changed=False
            for u in range(N):
                if dist[u]==float('inf'): continue
                for ei,e in enumerate(adj[u]):
                    v,cap,cost,rev,label=e
                    if cap>0 and dist[v]>dist[u]+cost:
                        dist[v]=dist[u]+cost; parent[v]=(u,ei); changed=True
            if not changed: break
        if parent[sink] is None: break
        addflow=target-flow; v=sink; path=[]
        while v!=src:
            u,ei=parent[v]; e=adj[u][ei]; addflow=min(addflow,e[1]); path.append(e[4]); v=u
        v=sink
        while v!=src:
            u,ei=parent[v]; e=adj[u][ei]; e[1]-=addflow; adj[v][e[3]][1]+=addflow; v=u
        flow+=addflow; total+=addflow*dist[sink]; paths.append({'units':addflow,'path':list(reversed(path)),'cost':dist[sink]})
    return {'flow_units':flow,'target_units':target,'total_cost_index':total,'paths':paths,'note':'Units and costs are illustrative planning values, not real kW or tariffs.'}

def dominating_set():
    # Greedy approximation for covering modeled service zones; not an exact optimization proof.
    zones=sorted({z for s in STATIONS for z in s['coverage']}); uncovered=set(zones); chosen=[]
    while uncovered:
        candidates=[s for s in STATIONS if len(set(s['coverage'])&uncovered)>0 and s['name'] not in chosen]
        if not candidates: break
        best=max(candidates,key=lambda s:len(set(s['coverage'])&uncovered))
        chosen.append(best['name']); uncovered-=set(best['coverage'])
    return {'selected_stations':chosen,'zones_covered':sorted(set(zones)-uncovered),'uncovered_zones':sorted(uncovered),'method':'Greedy dominating-set approximation'}

def priority_info(mode):
    ranked=sorted(EVS,key=lambda e: (0 if e['emergency'] else 1, e['soc'], e['deadline']))
    if mode=='deadline': ranked=sorted(EVS,key=lambda e:e['deadline'])
    elif mode=='low_soc': ranked=sorted(EVS,key=lambda e:e['soc'])
    return [{'ev':e['id'],'priority':'Emergency' if e['emergency'] else ('Critical SOC' if e['soc']<20 else 'Normal'),'soc':e['soc'],'deadline_min':e['deadline']} for e in ranked]

@app.route('/')
def index():
    return render_template('index.html', nodes=NODES, stations=STATIONS, evs=EVS)

@app.route('/api/optimize', methods=['POST'])
def optimize():
    data=request.get_json(silent=True) or {}
    weights={k:max(0,float(data.get(k,default))) for k,default in [('distance',1),('time',1),('cost',1),('carbon',1)]}
    if sum(weights.values())==0: weights['time']=1
    start=data.get('start','Home'); goal=data.get('goal','Station Central')
    if start not in NODES or goal not in NODES: return jsonify({'error':'Unknown start or destination node.'}),400
    route=shortest_path(start,goal,weights)
    station_scores=[]
    for s in STATIONS:
        # normalized, transparent score: lower is better
        score=(s['price']/25)*weights['cost']+(s['wait']/15)*weights['time']+(s['carbon']/0.5)*weights['carbon']+(s['grid_load']/100)*0.4+(s['battery_impact']/0.3)*0.3-(s['renewable']/100)*0.5
        station_scores.append({**s,'score':round(score,3)})
    station_scores.sort(key=lambda s:s['score'])
    match=matching(EVS,STATIONS)
    return jsonify({'route':route,'station_ranking':station_scores,'matching':match,'schedule':color_schedule(),'energy_flow':min_cost_flow(),'facility_placement':dominating_set(),'priority':priority_info(data.get('priority','adaptive')),'weights':weights,'disclaimer':'Prototype uses synthetic data and simplified models. It is not connected to live chargers, traffic, weather, tariffs, grid sensors or vehicle telemetry.'})

@app.route('/api/data')
def data():
    return jsonify({'nodes':NODES,'edges':[{'from':a,'to':b,'distance':d,'time':t,'cost':c,'carbon':co} for a,b,d,t,c,co in ROAD_EDGES],'stations':STATIONS,'evs':EVS})

if __name__ == '__main__':
    app.run(debug=True)