"""Execute actual event functions against the concrete map review counterexamples."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


@unittest.skipUnless(NODE, 'Node is required for JavaScript event regressions')
class ExplorerInteractionTests(unittest.TestCase):
    def run_js(self, body):
        program = '''const assert=require('node:assert/strict');
const vm=require('node:vm');
const source=require('node:fs').readFileSync(process.argv[1],'utf8');
function fragment(start,end){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);assert(a>=0&&b>a,'Missing event function');return source.slice(a,b);}
''' + body
        result = subprocess.run([NODE, '-e', program, str(ROOT/'site/assets/explorer.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_state_change_keeps_requested_state_after_exiting_street_view(self):
        self.run_js('''
const handler=fragment("  stateSelect.addEventListener('change'", "  byId('map-state-back')");
for(const oldState of ['ny','']){
 let eventHandler,chosen;
 const control={value:'ca',addEventListener:(event,fn)=>eventHandler=fn};
 vm.runInNewContext(handler,{stateSelect:control,roadActive:true,setRoad:()=>{control.value=oldState;},choose:state=>chosen=state});
 eventHandler();assert.equal(chosen,'ca');
}
''')

    def test_map_cost_preview_preserves_existing_extra_cost_warning(self):
        self.run_js('''
const code=fragment('  const costText =','  const serviceText =')+'this.preview=costText;';
const context={};vm.runInNewContext(code,context);
const badge={textContent:'Free option'},warning={hidden:false,textContent:'Check extra costs'};
const row={querySelector:selector=>selector==='.cost-badge'?badge:warning};
assert.equal(context.preview(row),'Free option · Check extra costs');
warning.hidden=true;assert.equal(context.preview(row),'Free option');
''')

    def test_selected_city_from_broad_radius_recenters_at_city_zoom(self):
        self.run_js('''
const code=fragment('  const selectCity =','  const setRoad =')+'this.select=selectCity;';
let view;
const context={selectedCity:'ny-buffalo',pendingFocusCity:'',radiusSelect:{value:'100'},roadActive:true,roadFailed:false,choose:()=>{},centerByCity:new Map([['ny-buffalo',{lat:42.9,lon:-78.8}]]),roadMap:{getZoom:()=>7,setView:(center,zoom)=>view={center,zoom}},matchMedia:()=>({matches:false}),document:{body:{classList:{contains:()=>false}}},focusSelectedCity:()=>{}};
vm.runInNewContext(code,context);context.select('ny','ny-buffalo');
assert.equal(view.zoom,11);assert.equal(view.center[0],42.9);assert.equal(view.center[1],-78.8);assert.equal(context.radiusSelect.value,'0');
''')
