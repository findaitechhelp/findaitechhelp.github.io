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
    const allNames = {al:'Alabama',ak:'Alaska',az:'Arizona',ar:'Arkansas',ca:'California',co:'Colorado',ct:'Connecticut',de:'Delaware',fl:'Florida',ga:'Georgia',hi:'Hawaii',id:'Idaho',il:'Illinois',in:'Indiana',ia:'Iowa',ks:'Kansas',ky:'Kentucky',la:'Louisiana',me:'Maine',md:'Maryland',ma:'Massachusetts',mi:'Michigan',mn:'Minnesota',ms:'Mississippi',mo:'Missouri',mt:'Montana',ne:'Nebraska',nv:'Nevada',nh:'New Hampshire',nj:'New Jersey',nm:'New Mexico',ny:'New York',nc:'North Carolina',nd:'North Dakota',oh:'Ohio',ok:'Oklahoma',or:'Oregon',pa:'Pennsylvania',ri:'Rhode Island',sc:'South Carolina',sd:'South Dakota',tn:'Tennessee',tx:'Texas',ut:'Utah',vt:'Vermont',va:'Virginia',wa:'Washington',wv:'West Virginia',wi:'Wisconsin',wy:'Wyoming',dc:'District of Columbia'};
    if (allNames[stateCode]) {
      place.textContent = 'A starting plan for ' + allNames[stateCode] + '. This is general guidance, not a checked local directory.';
      const plan = place.closest('[data-plan]');
      const helpKind = {learn:'learning',setup:'ai-consulting',repair:'computer-repair',unsure:''}[plan?.dataset.plan] || '';
      const localPath = '/locations/?state=' + encodeURIComponent(stateCode) + (helpKind ? '&kind=' + helpKind : '');
      if (localPath) {
        const a = document.createElement('a');
        a.href = localPath;
        a.textContent = ' Browse published listings in this state.';
        place.append(a);
      }
      for (const a of plan.querySelectorAll('a[href^="/locations/"],a[href^="/find/?"]')) {
        const destination = new URL(a.href);
        destination.searchParams.set('state', stateCode);
        a.href = destination.pathname + destination.search;
      }
      const emailLink = plan.querySelector('a[href^="mailto:"]');
      if (emailLink) {
        const email = new URL(emailLink.href);
        const lines = (email.searchParams.get('body') || '').split('\n');
        const last = lines.length - 1;
        try {
          const savedPlan = new URL(lines[last]);
          if (savedPlan.protocol === 'https:' && savedPlan.pathname.startsWith('/find/')) {
            savedPlan.searchParams.set('state', stateCode);
            lines[last] = savedPlan.href;
            email.searchParams.set('body', lines.join('\n'));
            emailLink.href = email.href;
          }
        } catch (_) { /* Keep the server-generated draft if its final line is not a URL. */ }
      }
    }
  }
  for (const button of document.querySelectorAll('.print-button')) {
    button.hidden = false;
    button.addEventListener('click', () => window.print());
  }
})();
