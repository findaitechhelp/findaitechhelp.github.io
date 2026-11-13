"""City points must align with the Census-derived state polygons, including insets."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
from geography import city_points

def inside(point,ring):
    x,y=point;hit=False
    for (ax,ay),(bx,by) in zip(ring,ring[1:]+ring[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:hit=not hit
    return hit

class GeographyTests(unittest.TestCase):
    def test_census_city_points_fall_within_matching_state_geometry(self):
        samples=[('ny','Buffalo','New York'),('ny','New York','New York'),('ca','Los Angeles','California'),('tx','Houston','Texas'),('ak','Anchorage','Alaska'),('hi','Honolulu','Hawaii'),('dc','Washington','District of Columbia'),('il','Chicago','Illinois')]
        topo=json.loads((ROOT/'data'/'states-albers-10m.json').read_text());sx,sy=topo['transform']['scale'];tx,ty=topo['transform']['translate'];arcs=[]
        for arc in topo['arcs']:
            x=y=0;coords=[]
            for dx,dy in arc:x+=dx;y+=dy;coords.append((x*sx+tx,y*sy+ty))
            arcs.append(coords)
        for state,city,state_name in samples:
            key=state+'-fixture';points=city_points({key:{'state':state,'name':city+', '+state}})
            self.assertIn(key,points,city)
            point=(points[key]['x'],points[key]['y'])
            geom=next(g for g in topo['objects']['states']['geometries'] if g['properties']['name']==state_name)
            polygons=geom['arcs'] if geom['type']=='MultiPolygon' else [geom['arcs']]
            rings=[]
            for polygon in polygons:
                ring=[]
                for index in polygon[0]:ring.extend(arcs[index] if index>=0 else reversed(arcs[~index]))
                rings.append(ring)
            self.assertTrue(any(inside(point,ring) for ring in rings),city+' marker is outside its state')
    def test_common_city_aliases_use_the_same_census_point(self):
        points=city_points({'short':{'state':'ny','name':'New York, New York'},'long':{'state':'ny','name':'New York City, New York'}})
        self.assertEqual(points['short'],points['long'])

    def test_unmatched_area_does_not_invent_a_point(self):
        self.assertEqual(city_points({'fiction':{'state':'ca','name':'No Such Synthetic City'}}),{})

    def test_named_primary_city_in_metro_label_uses_existing_census_point(self):
        for state,city,metro in [('ky','Louisville','Louisville / Jefferson County'),('nc','Raleigh','Raleigh / Research Triangle'),('va','Arlington','Arlington / Northern Virginia')]:
            points=city_points({'city':{'state':state,'name':city},'metro':{'state':state,'name':metro}})
            self.assertIn('city',points)
            self.assertEqual(points['city'],points['metro'])

if __name__=='__main__':unittest.main()
