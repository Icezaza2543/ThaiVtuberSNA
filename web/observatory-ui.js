/* Observatory controls use the existing graph state and analytical inputs. */
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const compactLayout = window.matchMedia('(max-width: 1199px)');
const mobileLayout = window.matchMedia('(max-width: 767px)');
let inspectorReturnFocus = null;
let modalReturnFocus = null;

function updateSceneStatus() {
  const nodes = graphNodes.filter(node => node.visible);
  const edges = graphEdges.filter(edge => edge.visible);
  statVtubers.textContent = nodes.length.toLocaleString();
  statEdges.textContent = edges.length.toLocaleString();
  const message = document.getElementById('graphMessage');
  message.hidden = nodes.length > 0 && edges.length > 0;
  message.textContent = !nodes.length ? 'No creators match these filters. Try another name or group.' : 'No connections meet this period and threshold. Creators remain visible.';
  document.querySelectorAll('.legend-item').forEach(item => {
    const active = item.querySelector('[title]')?.title === selectedAgency;
    item.classList.toggle('active-filter', active);
    item.setAttribute('aria-pressed', String(active));
  });
}

function updateSnapshotLabel() {
  const stamp = rawData.metadata?.generated_at || rawData.metadata?.last_updated || rawData.metadata?.updated_at?.slice(0, 10);
  const date = stamp ? new Date(stamp) : null;
  document.getElementById('dataFreshness').textContent = date && !Number.isNaN(date.getTime())
    ? `Snapshot · ${date.toISOString().slice(0, 10)}` : 'Snapshot date unavailable';
}

function renderSearchResults() {
  const results = document.getElementById('searchResults');
  results.replaceChildren();
  if (!searchQuery) return;
  const matches = graphNodes.filter(node => node.visible);
  for (const node of matches.slice(0, 12)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = node.label;
    button.addEventListener('click', () => {
      openInspector(node);
      focusCreator(node);
      renderCanvas();
    });
    results.append(button);
  }
  const note = document.createElement('p');
  note.className = 'note';
  note.textContent = matches.length ? `${matches.length} matches${matches.length > 12 ? ' · refine your search to find more' : ''}` : 'No matching creators in the current filters.';
  results.append(note);
}

function setControlsOpen(open, returnFocus = true) {
  const dock = document.getElementById('controlDock');
  const trigger = document.getElementById('btnControls');
  if (!compactLayout.matches) {
    dock.inert = false;
    dock.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
    return;
  }
  if (open) closeInspector(false);
  dock.classList.toggle('open', open);
  dock.inert = !open;
  trigger.setAttribute('aria-expanded', String(open));
  if (open) searchInput.focus({ preventScroll: true });
  else if (returnFocus) trigger.focus({ preventScroll: true });
}

function closeInspector(returnFocus = true) {
  inspectorPanel.classList.remove('open');
  inspectorPanel.inert = true;
  selectedNode = null;
  if (returnFocus) {
    const target = inspectorReturnFocus?.isConnected && !inspectorReturnFocus.closest('[inert]') ? inspectorReturnFocus : canvas;
    target.focus({ preventScroll: true });
  }
  renderCanvas();
}

function setMethodologyOpen(open) {
  if (open) modalReturnFocus = document.activeElement;
  infoModal.classList.toggle('open', open);
  infoModal.inert = !open;
  document.querySelector('.header').inert = open;
  document.querySelector('.main-container').inert = open;
  if (open) document.querySelector('.modal-card').focus();
  else if (modalReturnFocus?.isConnected) modalReturnFocus.focus({ preventScroll: true });
}

function updatePeriodControls() {
  const label = TIMELINE_STEPS[currentTimelineStep];
  document.getElementById('timeSlider').value = currentTimelineStep;
  document.getElementById('timeSlider').setAttribute('aria-valuetext', label);
  document.getElementById('scenePeriod').textContent = `${label} · ${isCumulativeTimeline ? 'cumulative' : 'yearly'}`;
  document.querySelectorAll('[data-step]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.step) === currentTimelineStep)));
}

function updatePlaybackButton() {
  document.querySelector('#playIcon use').setAttribute('href', isPlayingTimeline ? '#i-pause' : '#i-play');
  document.getElementById('playText').textContent = isPlayingTimeline ? 'Pause' : 'Play';
  document.getElementById('btnPlayTimeline').setAttribute('aria-pressed', String(isPlayingTimeline));
}

function stopTimeline() {
  clearInterval(timelinePlayTimer);
  timelinePlayTimer = null;
  isPlayingTimeline = false;
  updatePlaybackButton();
}

function visibleStageRect() {
  const width = container.clientWidth, height = container.clientHeight;
  const left = compactLayout.matches ? 20 : 338;
  const right = !mobileLayout.matches && inspectorPanel.classList.contains('open') ? 420 : 24;
  const bottom = mobileLayout.matches && inspectorPanel.classList.contains('open') ? inspectorPanel.clientHeight + 20 : 110;
  return { left, top: 100, width: Math.max(100, width - left - right), height: Math.max(100, height - 100 - bottom) };
}

function focusCreator(node) {
  const view = visibleStageRect();
  panX = view.left + view.width / 2 - node.x * zoom;
  panY = view.top + view.height / 2 - node.y * zoom;
}

function fitConstellation() {
  const nodes = graphNodes.filter(node => node.visible);
  if (!nodes.length) return;
  const view = visibleStageRect();
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  nodes.forEach(node => {
    minX = Math.min(minX, node.x - node.radius - 60);
    maxX = Math.max(maxX, node.x + node.radius + 60);
    minY = Math.min(minY, node.y - node.radius - 150);
    maxY = Math.max(maxY, node.y + node.radius + 60);
  });
  zoom = Math.max(.05, Math.min(.65, view.width / (maxX - minX), view.height / (maxY - minY)));
  panX = view.left + view.width / 2 - (minX + maxX) * zoom / 2;
  panY = view.top + view.height / 2 - (minY + maxY) * zoom / 2;
  renderCanvas();
}

function zoomScene(factor) {
  const view = visibleStageRect();
  const centerX = view.left + view.width / 2, centerY = view.top + view.height / 2;
  const next = Math.max(.05, Math.min(3.5, zoom * factor));
  panX = centerX - (centerX - panX) * next / zoom;
  panY = centerY - (centerY - panY) * next / zoom;
  zoom = next;
  renderCanvas();
}

function setupObservatoryUI() {
  const dock = document.getElementById('controlDock');
  dock.inert = compactLayout.matches;
  document.getElementById('btnControls').addEventListener('click', () => setControlsOpen(!dock.classList.contains('open')));
  document.getElementById('btnCloseControls').addEventListener('click', () => setControlsOpen(false));
  const search = () => { setControlsOpen(true); searchInput.focus(); };
  document.getElementById('btnSearch').addEventListener('click', search);
  document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => {
    stopTimeline(); updateTimelineSlice(Number(button.dataset.step));
  }));
  document.getElementById('btnZoomIn').addEventListener('click', () => zoomScene(1.25));
  document.getElementById('btnZoomOut').addEventListener('click', () => zoomScene(.8));
  document.getElementById('btnFitGraph').addEventListener('click', fitConstellation);
  canvas.addEventListener('keydown', event => {
    const steps = { ArrowLeft: [40,0], ArrowRight: [-40,0], ArrowUp: [0,40], ArrowDown: [0,-40] };
    if (steps[event.key]) { event.preventDefault(); panX += steps[event.key][0]; panY += steps[event.key][1]; renderCanvas(); }
    if (event.key === '+' || event.key === '=') zoomScene(1.25);
    if (event.key === '-') zoomScene(.8);
  });
  searchInput.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown') { event.preventDefault(); document.querySelector('#searchResults button')?.focus(); }
    if (event.key === 'Enter') document.querySelector('#searchResults button')?.click();
  });
  document.addEventListener('keydown', event => {
    const editing = event.target.matches('input,select,textarea,[contenteditable]');
    if (event.key === '/' && !editing && !infoModal.classList.contains('open')) { event.preventDefault(); search(); }
    if (event.key === 'Escape') {
      if (infoModal.classList.contains('open')) setMethodologyOpen(false);
      else if (inspectorPanel.classList.contains('open')) closeInspector();
      else if (dock.classList.contains('open')) setControlsOpen(false);
    }
    if (event.key === 'Tab' && infoModal.classList.contains('open')) {
      const focusable = [...infoModal.querySelectorAll('a[href],button:not([disabled]),[tabindex="0"]')];
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && (document.activeElement === first || document.activeElement.classList.contains('modal-card'))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  const motionChanged = () => {
    if (reducedMotion.matches) stopTimeline();
    const play = document.getElementById('btnPlayTimeline');
    play.disabled = reducedMotion.matches;
    play.title = reducedMotion.matches ? 'Automatic playback is off for reduced motion. Select a year manually.' : 'Play observation years';
  };
  reducedMotion.addEventListener('change', motionChanged);
  motionChanged();
  compactLayout.addEventListener('change', () => setControlsOpen(false, false));
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopTimeline(); });
  // Match the controls to the existing simulation defaults without changing physics.
  repulsionSlider.value = repulsionStrength; repulsionValue.textContent = repulsionStrength;
  linkDistSlider.value = linkDistance; linkDistValue.textContent = linkDistance;
}
