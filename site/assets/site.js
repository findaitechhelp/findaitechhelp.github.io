/* Progressive enhancement. Ready-made plans remain ordinary links without JS. */
(() => {
  'use strict';
  const needs = new Set(['learn', 'setup', 'repair', 'unsure']);
  const audiences = new Set(['individual', 'business', 'team', 'senior']);
  const states = new Map(Array.from(document.querySelectorAll('select[name="state"] option')).map(o => [o.value, o.textContent]));
  const params = new URLSearchParams(window.location.search);
  const chosenState = params.get('state') || '';
  const stateCode = /^[a-z]{2}$/.test(chosenState) ? chosenState : '';
  const finder = document.getElementById('help-finder');
  if (finder) {
    finder.hidden = false;
    const invalid = (params.has('need') && !needs.has(params.get('need'))) ||
      (params.has('audience') && !audiences.has(params.get('audience'))) ||
      (params.has('state') && params.get('state') !== '' && !states.has(params.get('state')));
    if (invalid) {
      const feedback = document.getElementById('finder-feedback');
      feedback.textContent = 'Some choices in this link could not be used. Please select who needs help, what you need, and a state below—or choose a ready-made plan.';
      feedback.hidden = false;
    }
    if (states.has(stateCode)) finder.elements.state.value = stateCode;
    for (const [name, allowed] of [['need', needs], ['audience', audiences]]) {
      if (allowed.has(params.get(name))) finder.elements[name].value = params.get(name);
    }
    finder.addEventListener('submit', event => {
      if (!finder.reportValidity()) return;
      event.preventDefault();
      const need = needs.has(finder.elements.need.value) ? finder.elements.need.value : 'unsure';
      const audience = audiences.has(finder.elements.audience.value) ? finder.elements.audience.value : 'individual';
      const state = finder.elements.state.value;
      window.location.assign('/find/' + need + '/' + audience + '/' + (state ? '?state=' + encodeURIComponent(state) : ''));
    });
  }
  const locations = document.getElementById('location-finder');
  if (locations) locations.hidden = false;
  if (locations) locations.addEventListener('submit', event => {
    if (!locations.reportValidity()) return;
    event.preventDefault();
    window.location.assign('/find/?state=' + encodeURIComponent(locations.elements.state.value));
  });
  const place = document.getElementById('plan-location');
  if (place && stateCode) {
    // State names are selected from the same fixed list, never injected as HTML.
    const allNames = {al:'Alabama',ak:'Alaska',az:'Arizona',ar:'Arkansas',ca:'California',co:'Colorado',ct:'Connecticut',de:'Delaware',fl:'Florida',ga:'Georgia',hi:'Hawaii',id:'Idaho',il:'Illinois',in:'Indiana',ia:'Iowa',ks:'Kansas',ky:'Kentucky',la:'Louisiana',me:'Maine',md:'Maryland',ma:'Massachusetts',mi:'Michigan',mn:'Minnesota',ms:'Mississippi',mo:'Missouri',mt:'Montana',ne:'Nebraska',nv:'Nevada',nh:'New Hampshire',nj:'New Jersey',nm:'New Mexico',ny:'New York',nc:'North Carolina',nd:'North Dakota',oh:'Ohio',ok:'Oklahoma',or:'Oregon',pa:'Pennsylvania',ri:'Rhode Island',sc:'South Carolina',sd:'South Dakota',tn:'Tennessee',tx:'Texas',ut:'Utah',vt:'Vermont',va:'Virginia',wa:'Washington',wv:'West Virginia',wi:'Wisconsin',wy:'Wyoming'};
    if (allNames[stateCode]) {
      place.textContent = 'A starting plan for ' + allNames[stateCode] + '. This is general guidance, not a checked local directory.';
      const localPath = stateCode === 'ny' ? '/ny/buffalo/' : stateCode === 'tx' ? '/tx/dallas/' : '';
      if (localPath) {
        const a = document.createElement('a');
        a.href = localPath;
        a.textContent = ' Explore the local directory research.';
        place.append(a);
      }
    }
  }
  const map = document.getElementById('location-map');
  const stateSelect = document.getElementById('explore-state');
  if (map && stateSelect) {
    document.getElementById('map-controls').hidden = false;
    document.getElementById('explore-state-control').hidden = false;
    const explorer = map.closest('.location-explorer');
    const rows = Array.from(document.querySelectorAll('[data-local-state]'));
    const cities = Array.from(document.querySelectorAll('[data-city]'));
    const names = new Map(Array.from(stateSelect.options).map(o => [o.value, o.textContent.split(' · ')[0]]));
    const nationwide = Number(explorer.dataset.nationwide);
    let selectedState = '', selectedCity = '';
    let box = [0, 0, 975, 640];
    const draw = () => map.setAttribute('viewBox', box.join(' '));
    const fitState = state => {
      const path = map.querySelector('[data-map-state="' + state + '"] path');
      if (!path) { box = [0, 0, 975, 640]; draw(); return; }
      const b = path.getBBox(), pad = Math.max(b.width, b.height) * .14;
      box = [b.x-pad, b.y-pad, Math.max(b.width+2*pad, 20), Math.max(b.height+2*pad, 20)];
      draw();
    };
    const choose = (state, city = '', updateUrl = true) => {
      selectedState = names.has(state) ? state : '';
      selectedCity = cities.some(c => c.dataset.city === city && c.dataset.cityState === selectedState) ? city : '';
      stateSelect.value = selectedState;
      let count = 0;
      for (const row of rows) {
        row.hidden = !!((selectedState && row.dataset.localState !== selectedState) || (selectedCity && row.dataset.localMetro !== selectedCity));
        if (!row.hidden) count++;
      }
      for (const cityLink of cities) {
        cityLink.hidden = !!(selectedState && cityLink.dataset.cityState !== selectedState);
        if (cityLink.dataset.city === selectedCity) cityLink.setAttribute('aria-current', 'true');
        else cityLink.removeAttribute('aria-current');
      }
      document.getElementById('city-choices').hidden = !cities.some(c => !c.hidden);
      const cityLink = cities.find(c => c.dataset.city === selectedCity);
      const name = cityLink ? cityLink.dataset.cityName : selectedState ? names.get(selectedState) : 'the United States';
      document.getElementById('location-heading').textContent = 'Published listings in ' + name;
      document.getElementById('location-summary').textContent = count + ' local/state listings. Free options appear first. Confirm details directly with the organization.';
      document.getElementById('map-status').textContent = name + ': ' + count + ' local/state listings + ' + nationwide + ' nationwide online programs.';
      document.getElementById('location-empty').hidden = count > 0;
      for (const a of map.querySelectorAll('[data-map-state]')) a.classList.toggle('selected', a.dataset.mapState === selectedState);
      fitState(selectedState);
      if (updateUrl) {
        const url = new URL(window.location.href);
        if (selectedState) url.searchParams.set('state', selectedState); else url.searchParams.delete('state');
        if (selectedCity) url.searchParams.set('city', selectedCity); else url.searchParams.delete('city');
        window.history.replaceState(null, '', url.pathname + url.search);
      }
    };
    stateSelect.addEventListener('change', () => choose(stateSelect.value));
    for (const a of map.querySelectorAll('[data-map-state]')) a.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); choose(a.dataset.mapState);
    });
    for (const a of cities) a.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); choose(a.dataset.cityState, a.dataset.city);
    });
    document.getElementById('map-reset').addEventListener('click', () => choose(''));
    const zoom = factor => {
      const width = Math.max(15, Math.min(975, box[2] * factor));
      const height = Math.max(15, Math.min(640, box[3] * factor));
      box = [box[0]+(box[2]-width)/2, box[1]+(box[3]-height)/2, width, height]; draw();
    };
    document.getElementById('map-zoom-in').addEventListener('click', () => zoom(.7));
    document.getElementById('map-zoom-out').addEventListener('click', () => zoom(1/.7));
    for (const button of explorer.querySelectorAll('[data-map-pan]')) button.addEventListener('click', () => {
      const direction = button.dataset.mapPan;
      box[0] += (direction === 'east' ? 1 : direction === 'west' ? -1 : 0) * box[2] * .2;
      box[1] += (direction === 'south' ? 1 : direction === 'north' ? -1 : 0) * box[3] * .2; draw();
    });
    const expand = document.getElementById('map-fullscreen');
    const obscured = [];
    let previousOverflow = '';
    const setExpanded = expanded => {
      explorer.classList.toggle('map-expanded', expanded);
      expand.setAttribute('aria-expanded', String(expanded));
      expand.textContent = expanded ? 'Close expanded map' : 'Expand map';
      if (expanded) {
        explorer.setAttribute('role', 'dialog');
        explorer.setAttribute('aria-modal', 'true');
        previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        for (let node = explorer; node.parentElement; node = node.parentElement) {
          for (const sibling of node.parentElement.children) {
            if (sibling !== node && sibling instanceof HTMLElement) {
              obscured.push([sibling, sibling.inert]); sibling.inert = true;
            }
          }
          if (node.parentElement === document.body) break;
        }
      } else {
        explorer.removeAttribute('role'); explorer.removeAttribute('aria-modal');
        for (const [element, wasInert] of obscured) element.inert = wasInert;
        obscured.length = 0;
        document.body.style.overflow = previousOverflow;
      }
      expand.focus();
    };
    expand.addEventListener('click', () => setExpanded(!explorer.classList.contains('map-expanded')));
    explorer.addEventListener('keydown', event => {
      if (!explorer.classList.contains('map-expanded')) return;
      if (event.key === 'Escape') { event.preventDefault(); setExpanded(false); }
      if (event.key === 'Tab') {
        const targets = Array.from(explorer.querySelectorAll('a[href],button,select,input,summary,[tabindex="0"]'))
          .filter(element => !element.disabled && element.getClientRects().length > 0 && !element.closest('[hidden]'));
        const first = targets[0], last = targets[targets.length-1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    choose(params.get('state') || '', params.get('city') || '', false);
  }
  for (const button of document.querySelectorAll('.print-button')) {
    button.hidden = false;
    button.addEventListener('click', () => window.print());
  }
})();
