"""Census representative place points on the existing US Atlas Albers USA map.

Points locate cities/areas, never provider street addresses. Source geometry:
https://github.com/topojson/us-atlas (scale1300, translate487.5/305)
Projection parameters: https://github.com/d3/d3-geo/tree/main/src/projection
"""
import json
import math
from pathlib import Path
import re
import unicodedata

def normalized_name(value):
    ascii_name=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',ascii_name)

def project_city(lat,lon,state):
    scale=1300.;tx,ty=487.5,305.
    if state=='ak':parallels=(55,65);rotation=154;center=(-2,58.5);scale*=.35;tx-=.307*1300;ty+=.201*1300
    elif state=='hi':parallels=(8,18);rotation=157;center=(-3,19.9);tx-=.205*1300;ty+=.212*1300
    else:parallels=(29.5,45.5);rotation=96;center=(-.6,38.7)
    p1,p2=map(math.radians,parallels);n=(math.sin(p1)+math.sin(p2))/2
    c=1+math.sin(p1)*(2*n-math.sin(p1))
    def raw(lon_deg,lat_deg):
        radius=math.sqrt(c-2*n*math.sin(math.radians(lat_deg)))/n
        angle=n*math.radians(lon_deg)
        return radius*math.sin(angle),math.sqrt(c)/n-radius*math.cos(angle)
    cx,cy=raw(*center);x,y=raw(lon+rotation,lat)
    return round(tx+scale*(x-cx),2),round(ty-scale*(y-cy),2)

def city_points(areas):
    data=json.loads((Path(__file__).resolve().parents[1]/'data'/'place-centers.json').read_text(encoding='utf-8'))['places']
    points={}
    for key,area in areas.items():
        state=area['state'];name=area['name'].split(',')[0]
        canonical=normalized_name(name)
        canonical={'newyorkcity':'newyork','saintpaul':'stpaul','washingtondc':'washington','boise':'boisecity','lexington':'lexingtonfayette'}.get(canonical,canonical)
        center=data.get(state+'|'+canonical)
        if center:
            x,y=project_city(center[0],center[1],state)
            if -60<=x<=975 and 0<=y<=640:points[key]={'x':x,'y':y,'geoid':center[2]}
    return points
