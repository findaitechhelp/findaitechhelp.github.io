"""Pure directory geography and measurable coverage; no listing approvals or HTML."""
import json
from pathlib import Path
from content import STATES
from geography import normalized_name
LOCATIONS={**STATES,'dc':'District of Columbia'}
METROS={'ny-buffalo':('ny','Buffalo, New York','/ny/buffalo/'),'tx-dallas':('tx','Dallas, Texas','/tx/dallas/')}

def local_rows(records):
    rows=[]
    for kind in ['providers','programs','resources']:
        for record in records[kind]:
            state=record.get('state_id') or METROS.get(record.get('metro_id'),('',))[0]
            if state in LOCATIONS:rows.append((state,record))
    return rows

def locality(state,record):
    if record.get('metro_id') in METROS:
        info=METROS[record['metro_id']];return record['metro_id'],info[1],info[2]
    if record.get('location_slug') and record.get('location_label'):
        return state+'-'+record['location_slug'],record['location_label'],'/locations/?state='+state+'&city='+state+'-'+record['location_slug']+'#location-results'
    return '',LOCATIONS[state],''

def coverage_report(records):
    rows=local_rows(records);states={st for st,row in rows};cities={}
    for state,row in rows:
        key,label,url=locality(state,row)
        if key:cities[key]={'state':state,'name':label}
    aliases={'newyorkcity':'newyork','saintpaul':'stpaul'}
    def norm(value):
        name=normalized_name(value.split(',')[0]);return aliases.get(name,name)
    names={(area['state'],norm(area['name'])) for area in cities.values()}
    targets=json.loads((Path(__file__).parent/'coverage-targets.json').read_text(encoding='utf-8'))
    missing=[target['name']+', '+LOCATIONS[target['state_id']] for target in targets['cities'] if (target['state_id'],norm(target['name'])) not in names]
    return {'geographic_listings':len(rows),'states_with_listings':len(states-set(['dc'])),'district_of_columbia':'dc' in states,'cities_and_areas':len(cities),'ai_specific_geographic_listings':sum(row.get('ai_specific') is True for st,row in rows),'major_city_basis':targets['basis'],'major_cities_covered':len(targets['cities'])-len(missing),'major_cities_total':len(targets['cities']),'major_city_gaps':missing,'state_gaps':[name for st,name in STATES.items() if st not in states]}
