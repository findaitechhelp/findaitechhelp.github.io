/* Local SVG explorer: no remote tiles, tracking, geolocation or dependencies. */
(() => {
  'use strict';
  const map = document.getElementById('location-map');
  const stateSelect = document.getElementById('explore-state');
  if (!map || !stateSelect) return;
  const explorer = map.closest('.location-explorer');
  const byId = id => document.getElementById(id);
  const rows = [...explorer.querySelectorAll('[data-local-state]')];
  const cities = [...explorer.querySelectorAll('[data-city]')];
  const markers = [...map.querySelectorAll('[data-city-marker]')];
  const stateLinks = [...map.querySelectorAll('[data-map-state]')];
  const mapLinks = [...stateLinks, ...markers];
  const citySelect = byId('explore-city');
  const search = byId('directory-search');
  const kind = byId('directory-kind');
  const names = new Map([...stateSelect.options].map(o => [o.value, o.textContent.split(' · ')[0]]));
  const fold = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const nationwide = Number(explorer.dataset.nationwide);
  const params = new URLSearchParams(location.search);
  const allowedKinds = new Set([...kind.options].map(o => o.value));
  search.value = (params.get('q') || '').slice(0,120);
  kind.value = allowedKinds.has(params.get('kind')) ? params.get('kind') : '';
  for (const link of explorer.querySelectorAll('[data-js-shortcut]')) link.hidden=false;
  for (const id of ['map-controls','explore-state-control','directory-filters','map-gesture','selection-actions']) byId(id).hidden = false;
  map.classList.add('is-interactive');
  let selectedState = '', selectedCity = '', shownLimit = 12;
  let box = [0,0,975,640];
  const constrain = () => {
    box[2] = Math.max(80, Math.min(975, box[2]));
    box[3] = box[2] * 640 / 975;
    box[0] = Math.max(-35, Math.min(1010-box[2], box[0]));
    box[1] = Math.max(-25, Math.min(665-box[3], box[1]));
  };
  const markerNodes=markers.map(marker=>({marker,dot:marker.querySelector('.pin-dot'),halo:marker.querySelector('.pin-halo'),label:marker.querySelector('.city-label')}));
  for(const item of markerNodes)item.label.textContent=item.marker.dataset.cityName.split(',')[0];
  const labelNodes=stateLinks.map(link=>({label:link.querySelector('.state-label'),bounds:link.querySelector('path').getBBox()}));
  let frame=0,lastUnit=0,renderedBox=[...box];
  let viewport={width:map.getBoundingClientRect().width,height:map.getBoundingClientRect().height};
  const unitsPerPixel=()=>Math.max(box[2]/Math.max(viewport.width,1),box[3]/Math.max(viewport.height,1));
  const draw = () => {
    constrain();
    if(frame)return;
    frame=requestAnimationFrame(()=>{
      frame=0;map.setAttribute('viewBox',box.join(' '));renderedBox=[...box];
      const unit=unitsPerPixel();
      if(Math.abs(unit-lastUnit)<.00001)return;
      lastUnit=unit;
      for(const {label,bounds} of labelNodes){
        label.style.fontSize=(10*unit)+'px';
        label.style.strokeWidth=(2*unit)+'px';
        label.style.display=bounds.width/unit<21 || bounds.height/unit<13 ? 'none' : '';
      }
      for(const {marker,dot,halo,label} of markerNodes){
        dot.setAttribute('r',2.8*unit);halo.setAttribute('r',10*unit);
        label.style.fontSize=(12*unit)+'px';label.style.strokeWidth=(4*unit)+'px';
        label.setAttribute('text-anchor','middle');label.setAttribute('dx','0');label.setAttribute('dy',-12*unit);
      }
    });
  };
  if(window.ResizeObserver)new ResizeObserver(entries=>{
    viewport={width:entries[0].contentRect.width,height:entries[0].contentRect.height};lastUnit=0;draw();
  }).observe(map);
  const fit = (state, city) => {
    const marker = markers.find(m => m.dataset.cityMarker===city);
    if (marker) {
      box = [Number(marker.dataset.markerX)-100,Number(marker.dataset.markerY)-65.64,200,131.28];
    } else {
      const path = stateLinks.find(a => a.dataset.mapState===state)?.querySelector('path');
      if (!path) box = [0,0,975,640];
      else {
        const b = path.getBBox();
        const width = Math.max(130,b.width*1.3,b.height*1.3*975/640);
        box = [b.x+b.width/2-width/2,b.y+b.height/2-width*640/975/2,width,width*640/975];
      }
    }
    draw();
  };
  const tooltip = byId('map-tooltip');
  const hideTooltip = () => { tooltip.hidden = true; };
  const showTooltip = link => {
    tooltip.textContent = link.getAttribute('aria-label') + (link.dataset.cityMarker ? ' · Representative city point' : ' · Select to explore');
    tooltip.hidden = false;
  };
  const choose = (state, city='', {updateUrl=true, resetLimit=true, move=false}={}) => {
    const nextState = names.has(state) ? state : '';
    const nextCity = cities.some(c=>c.dataset.city===city && c.dataset.cityState===nextState) ? city : '';
    const changed = nextState!==selectedState || nextCity!==selectedCity;
    selectedState = nextState; selectedCity = nextCity;
    stateSelect.value = selectedState;
    for (const option of citySelect.options) {
      const unavailable = !!(selectedState && option.value && option.dataset.optionState!==selectedState);
      option.hidden = unavailable; option.disabled = unavailable;
    }
    citySelect.value = selectedCity;
    if (resetLimit) shownLimit=12;
    const query=fold(search.value.trim());
    const matched = rows.filter(row => {
      const services=row.dataset.service.split(' ');
      const type=kind.value;
      return (!selectedState || row.dataset.localState===selectedState) &&
        (!selectedCity || row.dataset.localMetro===selectedCity) &&
        (!query || fold(row.dataset.search).includes(query)) &&
        (!type || (type==='ai' && row.dataset.ai==='true') ||
          (type==='general' && row.dataset.ai!=='true') || (type==='free' && row.dataset.free==='true') ||
          (type==='learning' && services.some(s=>['learning','ai-training'].includes(s))) || services.includes(type));
    });
    const visible=new Set(matched.slice(0,shownLimit));
    const cityCounts=new Map(), stateCounts=new Map();
    for (const row of matched) {
      cityCounts.set(row.dataset.localMetro,(cityCounts.get(row.dataset.localMetro)||0)+1);
      stateCounts.set(row.dataset.localState,(stateCounts.get(row.dataset.localState)||0)+1);
    }
    for (const row of rows) row.hidden=!visible.has(row);
    for (const marker of markers) {
      const count=cityCounts.get(marker.dataset.cityMarker)||0;
      marker.toggleAttribute('hidden',!count);
      marker.classList.toggle('selected',marker.dataset.cityMarker===selectedCity);
      marker.setAttribute('aria-label',marker.dataset.cityName+': '+count+' matching local listings');
      marker.querySelector('title').textContent=marker.dataset.cityName+' · '+count+' matching listings · approximate city point';
    }
    for (const link of stateLinks) {
      const count=stateCounts.get(link.dataset.mapState)||0;
      link.classList.toggle('has-matches',count>0); link.classList.toggle('no-matches',count===0);
      link.classList.toggle('selected',link.dataset.mapState===selectedState);
      link.setAttribute('aria-label',link.dataset.stateName+' — '+count+' matching local/state listings');
      link.querySelector('title').textContent=link.getAttribute('aria-label');
    }
    for (const cityLink of cities) {
      cityLink.hidden=!(cityCounts.get(cityLink.dataset.city));
      if (cityLink.dataset.city===selectedCity) cityLink.setAttribute('aria-current','true');
      else cityLink.removeAttribute('aria-current');
    }
    byId('city-choices').hidden=!cities.some(c=>!c.hidden);
    const cityLink=cities.find(c=>c.dataset.city===selectedCity);
    const name=cityLink ? cityLink.dataset.cityName : selectedState ? names.get(selectedState) : 'the United States';
    byId('location-heading').textContent='Published listings in '+name;
    byId('location-summary').textContent=matched.length+' local/state listings. Free options appear first. Confirm details directly with the organization.';
    byId('map-status').textContent=name+': '+matched.length+' local/state listings + '+nationwide+' nationwide online programs.'+(matched.length?'':' No local matches. Change the filters or reset all filters.');
    byId('location-empty').hidden=matched.length>0;
    byId('directory-pagination').hidden=!matched.length;
    byId('directory-more').hidden=matched.length<=shownLimit;
    byId('directory-page-status').textContent='Showing '+Math.min(shownLimit,matched.length)+' of '+matched.length+' matching listings.';
    const active=[];
    if (selectedState) active.push(name);
    if (kind.value) active.push(kind.selectedOptions[0].textContent);
    if (search.value.trim()) active.push('Search: '+search.value.trim());
    byId('active-filters').textContent='Showing: '+(active.join(' · ')||'All locations and help types');
    byId('active-filters').hidden=!active.length;
    for (const button of explorer.querySelectorAll('[data-quick-kind]')) button.setAttribute('aria-pressed',String(button.dataset.quickKind===kind.value));
    const selectedLink=mapLinks.find(link=>selectedCity ? link.dataset.cityMarker===selectedCity && !link.hasAttribute('hidden') : selectedState ? link.dataset.mapState===selectedState : false) || stateLinks.find(a=>a.dataset.mapState===selectedState) || stateLinks[0];
    for (const link of mapLinks) link.setAttribute('tabindex',link===selectedLink?'0':'-1');
    if (changed || move) fit(selectedState,selectedCity);
    hideTooltip();
    if (updateUrl) {
      const url=new URL(location.href);
      for (const [key,value] of [['state',selectedState],['city',selectedCity],['kind',kind.value],['q',search.value.trim()]]) {
        if (value) url.searchParams.set(key,value); else url.searchParams.delete(key);
      }
      history.replaceState(null,'',url.pathname+url.search+url.hash);
    }
    return matched;
  };
  stateSelect.addEventListener('change',()=>choose(stateSelect.value,'',{move:true}));
  citySelect.addEventListener('change',()=>{
    const city=cities.find(c=>c.dataset.city===citySelect.value);
    choose(city ? city.dataset.cityState : selectedState,city ? city.dataset.city : '',{move:true});
  });
  search.addEventListener('input',()=>choose(selectedState,selectedCity));
  kind.addEventListener('change',()=>choose(selectedState,selectedCity));
  for (const button of explorer.querySelectorAll('[data-quick-kind]')) button.addEventListener('click',()=>{
    kind.value=button.dataset.quickKind; choose(selectedState,selectedCity);
  });
  byId('directory-clear').addEventListener('click',()=>{
    search.value='';kind.value='';choose(selectedState,selectedCity);search.focus();
  });
  const reset=()=>{search.value='';kind.value='';choose('','',{move:true});};
  byId('map-reset').addEventListener('click',()=>choose('','',{move:true}));
  byId('directory-reset').addEventListener('click',()=>{reset();stateSelect.focus();});
  byId('directory-more').addEventListener('click',()=>{
    const old=shownLimit;shownLimit+=12;
    const matched=choose(selectedState,selectedCity,{resetLimit:false});
    const next=matched[old];if(next){next.tabIndex=-1;next.focus({preventScroll:true});next.scrollIntoView({block:'nearest'});}
  });
  let suppressClick=false;
  for (const link of [...mapLinks,...cities]) link.addEventListener('click',event=>{
    if (suppressClick || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    choose(link.dataset.mapState || link.dataset.markerState || link.dataset.cityState,link.dataset.cityMarker || link.dataset.city || '',{move:true});
  });
  for (const link of mapLinks) {
    link.addEventListener('pointerenter',()=>showTooltip(link));
    link.addEventListener('pointerleave',hideTooltip);
    link.addEventListener('focus',()=>showTooltip(link));
    link.addEventListener('blur',hideTooltip);
  }
  map.addEventListener('keydown',event=>{
    if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)) return;
    const targets=mapLinks.filter(link=>!link.hasAttribute('hidden'));
    event.preventDefault();
    const index=targets.indexOf(document.activeElement);
    const direction=['ArrowLeft','ArrowUp'].includes(event.key)?-1:1;
    const next=event.key==='Home'?0:event.key==='End'?targets.length-1:(index+direction+targets.length)%targets.length;
    const target=targets[next];if(!target)return;
    for(const link of mapLinks)link.setAttribute('tabindex','-1');
    fit(target.dataset.mapState || target.dataset.markerState,target.dataset.cityMarker || '');
    target.setAttribute('tabindex','0');target.focus();
  });
  const point=(x,y)=>{const p=map.createSVGPoint();p.x=x;p.y=y;const world=p.matrixTransform(map.getScreenCTM().inverse());return {x:box[0]+(world.x-renderedBox[0])*box[2]/renderedBox[2],y:box[1]+(world.y-renderedBox[1])*box[3]/renderedBox[3]};};
  const zoom=(factor,x,y)=>{
    const anchor=Number.isFinite(x)?point(x,y):{x:box[0]+box[2]/2,y:box[1]+box[3]/2};
    const width=Math.max(80,Math.min(975,box[2]*factor));
    const ratio=width/box[2];
    box=[anchor.x-(anchor.x-box[0])*ratio,anchor.y-(anchor.y-box[1])*ratio,width,width*640/975];draw();hideTooltip();
  };
  byId('map-zoom-in').addEventListener('click',()=>zoom(.75));
  byId('map-zoom-out').addEventListener('click',()=>zoom(1/.75));
  for(const button of explorer.querySelectorAll('[data-map-pan]'))button.addEventListener('click',()=>{
    const d=button.dataset.mapPan;
    box[0]+=(d==='east'?1:d==='west'?-1:0)*box[2]*.2;
    box[1]+=(d==='south'?1:d==='north'?-1:0)*box[3]*.2;draw();hideTooltip();
  });
  map.addEventListener('dblclick',event=>{event.preventDefault();zoom(.65,event.clientX,event.clientY);});
  // Ordinary wheel and touch scroll remain page navigation. Touch map gestures
  // are explicit opt-in so the map does not trap people scrolling a phone.
  let touchEnabled=false;
  const touchButton=byId('map-touch');
  if(touchButton)touchButton.addEventListener('click',()=>{
    touchEnabled=!touchEnabled;touchButton.setAttribute('aria-pressed',String(touchEnabled));
    touchButton.textContent=touchEnabled?'Touch gestures on':'Touch gestures';
    map.style.touchAction=touchEnabled?'none':'pan-y pinch-zoom';
  });
  map.addEventListener('wheel',event=>{
    if(!event.ctrlKey)return;event.preventDefault();zoom(event.deltaY>0?1.15:1/1.15,event.clientX,event.clientY);
  },{passive:false});
  const pointers=new Map();let travel=0;
  map.addEventListener('pointerdown',event=>{
    if(event.button!==0 || (event.pointerType==='touch'&&!touchEnabled))return;
    if(!pointers.size){suppressClick=false;travel=0;}
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
  });
  map.addEventListener('pointermove',event=>{
    if(!pointers.has(event.pointerId))return;
    if(event.pointerType==='mouse' && !(event.buttons&1)){endPointer(event);return;}
    const before=[...pointers.values()];const previous=pointers.get(event.pointerId);
    const dx=event.clientX-previous.x,dy=event.clientY-previous.y;
    travel+=Math.hypot(dx,dy);
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    if(travel<6)return;
    suppressClick=true;map.classList.add('is-dragging');
    if(!map.hasPointerCapture(event.pointerId))map.setPointerCapture(event.pointerId);
    if(event.cancelable)event.preventDefault();
    const after=[...pointers.values()];
    const factor=pointers.size>1?.5:1;
    const unit=unitsPerPixel();
    box[0]-=dx*unit*factor;box[1]-=dy*unit*factor;
    if(after.length===2 && before.length===2){
      const oldDistance=Math.hypot(before[0].x-before[1].x,before[0].y-before[1].y);
      const newDistance=Math.hypot(after[0].x-after[1].x,after[0].y-after[1].y);
      if(oldDistance>5&&newDistance>5)zoom(oldDistance/newDistance,(after[0].x+after[1].x)/2,(after[0].y+after[1].y)/2);
      else draw();
    }else draw();
    hideTooltip();
  });
  const endPointer=event=>{
    pointers.delete(event.pointerId);
    if(map.hasPointerCapture(event.pointerId))map.releasePointerCapture(event.pointerId);
    if(!pointers.size)map.classList.remove('is-dragging');
  };
  map.addEventListener('pointerup',endPointer);map.addEventListener('pointercancel',endPointer);
  window.addEventListener('pointerup',endPointer);window.addEventListener('pointercancel',endPointer);
  window.addEventListener('blur',()=>{pointers.clear();map.classList.remove('is-dragging');});
  map.addEventListener('lostpointercapture',event=>{pointers.delete(event.pointerId);if(!pointers.size)map.classList.remove('is-dragging');});
  map.addEventListener('click',event=>{if(suppressClick){event.preventDefault();event.stopPropagation();suppressClick=false;}},true);
  const expand=byId('map-fullscreen');const obscured=[];let previousOverflow='';
  const setExpanded=expanded=>{
    explorer.classList.toggle('map-expanded',expanded);expand.setAttribute('aria-expanded',String(expanded));
    expand.textContent=expanded?'Close expanded map':'Expand map';
    if(expanded){
      explorer.setAttribute('role','dialog');explorer.setAttribute('aria-modal','true');
      previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
      for(let node=explorer;node.parentElement;node=node.parentElement){
        for(const sibling of node.parentElement.children)if(sibling!==node&&sibling instanceof HTMLElement){obscured.push([sibling,sibling.inert]);sibling.inert=true;}
        if(node.parentElement===document.body)break;
      }
    }else{
      explorer.removeAttribute('role');explorer.removeAttribute('aria-modal');
      for(const [element,wasInert]of obscured)element.inert=wasInert;obscured.length=0;
      document.body.style.overflow=previousOverflow;
    }
    expand.focus();
  };
  expand.addEventListener('click',()=>setExpanded(!explorer.classList.contains('map-expanded')));
  byId('selection-actions').querySelector('a').addEventListener('click',()=>{
    if(explorer.classList.contains('map-expanded')){
      setExpanded(false);
      byId('location-results').focus();
    }
  });
  explorer.addEventListener('keydown',event=>{
    if(!explorer.classList.contains('map-expanded'))return;
    if(event.key==='Escape'){event.preventDefault();setExpanded(false);}
    if(event.key==='Tab'){
      const targets=[...explorer.querySelectorAll('a[href],button,select,input,summary,[tabindex="0"]')].filter(el=>!el.disabled&&el.getClientRects().length>0&&!el.closest('[hidden]'));
      const first=targets[0],last=targets[targets.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
  choose(params.get('state')||'',params.get('city')||'',{updateUrl:false,move:true});
})();
