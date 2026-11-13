"""Display-only listing facts; never changes records, costs or approvals."""
import re
import hashlib
from pathlib import Path
from directory import LOCATIONS, METROS

FORMATS={'in-person':'In person','on-site':'On site','live-online':'Live online','online':'Online','self-paced':'Self-paced','hybrid':'Hybrid','varies':'Format varies','not-specified':'Confirm format'}
AUDIENCES={'individual':'Individuals','business':'Businesses','home-senior':'Seniors & families','small-business':'Small businesses','seniors':'Seniors','teachers':'Teachers','nonprofits':'Nonprofits','veterans':'Veterans'}

def listing_facts(record):
    cost=record.get('cost','Confirm with provider')
    free=record.get('free_option') is True or cost.startswith('Free')
    if free:
        kind='eligible' if re.search(r'eligib|accepted|selected|members?|residents?|cardholders?|\b(?:library|university)[ -]card\b|\bcard required\b|qualif|students?|faculty|staff|participants?|participating.*district',cost,re.I) else 'free'
    else:
        kind='paid' if re.search(r'^Paid\b|^Tuition and (?:college )?fees apply|^Courses advertised at \$|^U\.S./Canada: \$',cost,re.I) else 'confirm'
    labels={'eligible':'Eligibility-based free','free':'Free option','paid':'Paid option','confirm':'Confirm cost'}
    caution=free and bool(re.search(r'fee|cost|charg|expense|purchas|subscription|tuition',';'.join(cost.split(';')[1:]),re.I))
    state=record.get('state_id') or METROS.get(record.get('metro_id'),('',))[0]
    location=METROS.get(record.get('metro_id'),('',''))[1] or record.get('location_label') or LOCATIONS.get(state,'Nationwide online' if record.get('format') in ('online','self-paced','live-online') else 'Confirm location')
    art=str(sum(map(ord,record['id']))%3)
    art_bytes=(Path(__file__).parent/'assets'/'art'/('learning-'+art+'.svg')).read_bytes().replace(b'\r\n',b'\n')
    return {'cost':cost,'cost_kind':kind,'cost_label':labels[kind],'cost_caution':'Check extra costs' if caution else '',
            'format_label':FORMATS.get(record.get('format'),'Confirm format'),
            'audience_label':' · '.join(AUDIENCES.get(a,a.replace('-',' ').capitalize()) for a in record.get('audience',[])),
            'location':location,'art':art,'art_version':hashlib.sha256(art_bytes).hexdigest()[:12]}
