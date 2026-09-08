/* ═══════════════════════════════════════════════════════════════
   Thai VTuber SNA — Research Dashboard JavaScript
   Pure vanilla JS with Canvas 2D charting
   ═══════════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  // ── Data ──────────────────────────────────────────────────
  let DATA = null;

  const COLORS = {
    cyan: '#62e7ff', blue: '#3b82f6', violet: '#a78bfa',
    pink: '#ec4899', amber: '#f59e0b', emerald: '#10b981',
    red: '#ef4444', slate: '#94a3b8',
    cyanA: 'rgba(6,182,212,0.3)', blueA: 'rgba(59,130,246,0.3)',
    violetA: 'rgba(139,92,246,0.3)', pinkA: 'rgba(236,72,153,0.3)',
    amberA: 'rgba(245,158,11,0.3)', emeraldA: 'rgba(16,185,129,0.3)',
  };

  const YEAR_LABELS = ['2020','2021','2022','2023','2024','2025','2026 YTD'];
  const COHORT_PALETTE = [COLORS.cyan, COLORS.blue, COLORS.violet, COLORS.pink, COLORS.amber, COLORS.emerald, COLORS.red];

  // ── Initialization ────────────────────────────────────────

  async function init() {
    try {
      const resp = await fetch('dashboard_data.json');
      DATA = await resp.json();
    } catch(e) {
      document.querySelector('.dash-main').innerHTML =
        '<div style="text-align:center;padding:60px;color:#ef4444;">Research evidence could not load. Reload this page or return to the constellation.</div>';
      return;
    }

    document.getElementById('footerGen').textContent = 'Generated: ' + (DATA.meta?.generated_at || 'unknown');
    document.getElementById('genTimestamp').textContent = DATA.meta?.generated_at?.slice(0, 10) || 'Snapshot date unavailable';

    setupTabs();
    await document.fonts.ready;
    renderActivePanel();
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(renderActivePanel, 120);
    });
  }

  function renderActivePanel() {
    const renderers = { overview: renderOverview, ecosystem: renderEcosystem, lineage: renderLineage,
      cohorts: renderCohorts, centrality: renderCentrality, quality: renderQuality };
    const name = document.querySelector('.tab-btn.active')?.dataset.tab;
    renderers[name]?.();
    document.querySelectorAll('.scrollable-table').forEach(table => {
      table.tabIndex = 0;
      table.setAttribute('role', 'region');
      table.setAttribute('aria-label', table.closest('.card')?.querySelector('h3')?.textContent || 'Research table');
    });
    document.querySelectorAll('canvas').forEach(canvas => {
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', `${canvas.closest('.card')?.querySelector('h3')?.textContent || 'Research chart'}. Values are available in the associated research tables.`);
    });
  }

  function setupTabs() {
    const buttons = [...document.querySelectorAll('.tab-btn')];
    buttons.forEach((btn, index) => {
      btn.id = 'tab-' + btn.dataset.tab;
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-controls', 'panel-' + btn.dataset.tab);
      btn.setAttribute('aria-selected', String(btn.classList.contains('active')));
      btn.tabIndex = btn.classList.contains('active') ? 0 : -1;
      const panel = document.getElementById('panel-' + btn.dataset.tab);
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', btn.id);
      btn.addEventListener('click', () => {
        buttons.forEach(button => {
          const active = button === btn;
          button.classList.toggle('active', active);
          button.setAttribute('aria-selected', String(active));
          button.tabIndex = active ? 0 : -1;
        });
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p === panel));
        renderActivePanel();
      });
      btn.addEventListener('keydown', event => {
        const next = event.key === 'ArrowRight' ? (index + 1) % buttons.length : event.key === 'ArrowLeft' ? (index - 1 + buttons.length) % buttons.length : event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : null;
        if (next !== null) { event.preventDefault(); buttons[next].focus(); buttons[next].click(); }
      });
    });
  }

  // ── Chart Helpers ─────────────────────────────────────────

  function getCtx(id) {
    const canvas = document.getElementById(id);
    if (!canvas) return null;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const height = Number(canvas.dataset.chartHeight || canvas.getAttribute('height')) || 260;
    canvas.dataset.chartHeight = height;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w: rect.width, h: height };
  }

  function drawLineChart(id, datasets, labels, opts = {}) {
    const c = getCtx(id);
    if (!c) return;
    const { ctx, w, h } = c;
    const pad = { top: 30, right: 20, bottom: 40, left: opts.leftPad || 60 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    // find y range
    let yMin = opts.yMin ?? Infinity, yMax = opts.yMax ?? -Infinity;
    datasets.forEach(ds => {
      ds.data.forEach(v => {
        if (v !== null && v !== undefined) {
          if (v < yMin) yMin = v;
          if (v > yMax) yMax = v;
        }
      });
    });

    if (yMin === yMax) { yMax = yMin + 1; }
    const yRange = yMax - yMin;
    const yPad = yRange * 0.1;
    yMin = opts.yMin ?? (yMin - yPad);
    yMax = opts.yMax ?? (yMax + yPad);

    // grid
    ctx.strokeStyle = 'rgba(148,163,184,0.08)';
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = pad.top + plotH - (plotH * i / gridLines);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + plotW, y);
      ctx.stroke();

      // y labels
      const val = yMin + ((yMax - yMin) * i / gridLines);
      ctx.fillStyle = '#9298aa';
      ctx.font = '11px "JetBrains Mono"';
      ctx.textAlign = 'right';
      ctx.fillText(opts.yFmt ? opts.yFmt(val) : val.toFixed(opts.yDecimals ?? 1), pad.left - 8, y + 4);
    }

    // x labels
    ctx.fillStyle = '#9298aa';
    ctx.font = '11px "JetBrains Mono"';
    ctx.textAlign = 'center';
    labels.forEach((lbl, i) => {
      const x = pad.left + (plotW * i / (labels.length - 1));
      if (w < 500 && i % 2 && i !== labels.length - 1) return;
      const label = String(lbl) === '2026' ? '2026 YTD' : String(lbl);
      const half = ctx.measureText(label).width / 2;
      ctx.fillText(label, Math.max(half + 4, Math.min(w - half - 4, x)), h - pad.bottom + 20);
    });

    // datasets
    datasets.forEach(ds => {
      ctx.strokeStyle = ds.color;
      ctx.lineWidth = ds.lineWidth || 2;
      ctx.beginPath();
      let started = false;
      ds.data.forEach((v, i) => {
        if (v === null || v === undefined) return;
        const x = pad.left + (plotW * i / (labels.length - 1));
        const y = pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
        if (!started) { ctx.moveTo(x, y); started = true; }
        else { ctx.lineTo(x, y); }
      });
      ctx.stroke();

      // fill
      if (ds.fill) {
        ctx.globalAlpha = 0.15;
        ctx.lineTo(pad.left + plotW, pad.top + plotH);
        ctx.lineTo(pad.left, pad.top + plotH);
        ctx.closePath();
        ctx.fillStyle = ds.color;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // dots
      ds.data.forEach((v, i) => {
        if (v === null || v === undefined) return;
        const x = pad.left + (plotW * i / (labels.length - 1));
        const y = pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = ds.color;
        ctx.fill();
        ctx.strokeStyle = '#0a0e1a';
        ctx.lineWidth = 2;
        ctx.stroke();
      });
    });

    // legend
    if (datasets.length > 1) {
      let lx = pad.left + 8;
      const ly = pad.top - 10;
      ctx.font = '11px "Noto Sans Thai"';
      datasets.forEach(ds => {
        ctx.fillStyle = ds.color;
        ctx.fillRect(lx, ly - 6, 12, 3);
        ctx.fillStyle = '#94a3b8';
        ctx.textAlign = 'left';
        ctx.fillText(ds.label, lx + 16, ly);
        lx += ctx.measureText(ds.label).width + 36;
      });
    }
  }

  function drawBarChart(id, data, labels, opts = {}) {
    const c = getCtx(id);
    if (!c) return;
    const { ctx, w, h } = c;
    const pad = { top: 30, right: 20, bottom: 40, left: opts.leftPad || 60 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    let yMax = Math.max(...data.map(d => typeof d === 'object' ? d.value : d)) * 1.15;
    if (yMax <= 0) yMax = 1;

    const barW = Math.min(plotW / data.length * 0.7, 40);
    const gap = plotW / data.length;

    data.forEach((d, i) => {
      const val = typeof d === 'object' ? d.value : d;
      const color = typeof d === 'object' ? d.color : (opts.color || COLORS.cyan);
      const barH = (val / yMax) * plotH;
      const x = pad.left + gap * i + (gap - barW) / 2;
      const y = pad.top + plotH - barH;

      // glow
      ctx.shadowColor = color;
      ctx.shadowBlur = 0;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(x, y, barW, barH, [4, 4, 0, 0]);
      ctx.fill();
      ctx.shadowBlur = 0;

      // value
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px "JetBrains Mono"';
      ctx.textAlign = 'center';
      ctx.fillText(opts.valFmt ? opts.valFmt(val) : val.toLocaleString(), x + barW/2, y - 6);
    });

    // x labels
    ctx.fillStyle = '#9298aa';
    ctx.font = '11px "JetBrains Mono"';
    ctx.textAlign = 'center';
    labels.forEach((lbl, i) => {
      const x = pad.left + gap * i + gap / 2;
      ctx.fillText(lbl, x, h - pad.bottom + 18);
    });
  }

  function drawDonut(id, segments, opts = {}) {
    const c = getCtx(id);
    if (!c) return;
    const { ctx, w, h } = c;

    const cx = w / 2;
    const cy = h / 2;
    const R = Math.min(w, h) * 0.35;
    const r = R * 0.6;
    const total = segments.reduce((s, seg) => s + seg.value, 0);

    let angle = -Math.PI / 2;
    segments.forEach(seg => {
      const sliceAngle = (seg.value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, R, angle, angle + sliceAngle);
      ctx.arc(cx, cy, r, angle + sliceAngle, angle, true);
      ctx.closePath();
      ctx.fillStyle = seg.color;
      ctx.fill();

      // label
      const midAngle = angle + sliceAngle / 2;
      const labelR = R + 16;
      const lx = cx + Math.cos(midAngle) * labelR;
      const ly = cy + Math.sin(midAngle) * labelR;
      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px "Noto Sans Thai"';
      ctx.textAlign = midAngle > Math.PI/2 && midAngle < 3*Math.PI/2 ? 'right' : 'left';
      ctx.fillText(`${seg.label} (${seg.value})`, lx, ly);

      angle += sliceAngle;
    });

    // center text
    ctx.fillStyle = var_('--text-primary', '#f1f5f9');
    ctx.font = 'bold 20px "JetBrains Mono"';
    ctx.textAlign = 'center';
    ctx.fillText(total.toString(), cx, cy + 2);
    ctx.fillStyle = '#9298aa';
    ctx.font = '11px "Noto Sans Thai"';
    ctx.fillText(opts.centerLabel || 'Channels', cx, cy + 18);
  }

  function var_(name, fallback) { return fallback; }

  // ── Table Helpers ─────────────────────────────────────────

  function buildTable(headers, rows) {
    let html = '<table class="data-table"><thead><tr>';
    headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead><tbody>';
    rows.forEach(row => {
      html += '<tr>';
      row.forEach(cell => html += `<td>${cell}</td>`);
      html += '</tr>';
    });
    html += '</tbody></table>';
    return html;
  }

  function fmtNum(v, decimals = 0) {
    if (v === null || v === undefined) return '–';
    return typeof v === 'number' ? v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : v;
  }

  function fmtPct(v, decimals = 1) {
    if (v === null || v === undefined) return '–';
    return (v * 100).toFixed(decimals) + '%';
  }

  function tagify(text, cls) {
    return `<span class="tag ${cls}">${text}</span>`;
  }

  // ── OVERVIEW ──────────────────────────────────────────────

  function renderOverview() {
    if (!DATA) return;
    const eco = DATA.ecosystem?.yearly_metrics;
    if (!eco || eco.length === 0) return;

    const latest = eco[eco.length - 1];
    const prev = eco.length > 1 ? eco[eco.length - 2] : null;

    const kpis = [
      {
        label: 'Active Channels',
        value: fmtNum(latest.active_channels),
        color: COLORS.cyan,
        delta: prev ? `${((latest.active_channels / prev.active_channels - 1) * 100).toFixed(1)}% YoY` : null,
        deltaDir: prev ? (latest.active_channels >= prev.active_channels ? 'positive' : 'negative') : 'neutral',
      },
      {
        label: 'Edges',
        value: fmtNum(latest.edges),
        color: COLORS.blue,
        delta: prev ? `${((latest.edges / prev.edges - 1) * 100).toFixed(1)}% YoY` : null,
        deltaDir: prev ? (latest.edges >= prev.edges ? 'positive' : 'negative') : 'neutral',
      },
      {
        label: 'Modularity Q',
        value: latest.modularity?.toFixed(3) || '–',
        color: COLORS.violet,
        delta: prev ? `Δ ${(latest.modularity - prev.modularity).toFixed(3)}` : null,
        deltaDir: 'neutral',
      },
      {
        label: 'Communities',
        value: latest.communities || latest.num_communities || '–',
        color: COLORS.pink,
      },
      {
        label: 'Density',
        value: latest.density?.toFixed(4) || '–',
        color: COLORS.amber,
      },
      {
        label: 'Giant Component',
        value: fmtPct(latest.giant_component_share || latest.giant_share, 1),
        color: COLORS.emerald,
      },
    ];

    const strip = document.getElementById('kpiStrip');
    strip.innerHTML = kpis.map(k => `
      <div class="kpi-card">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-value" style="color: ${k.color}">${k.value}</div>
        ${k.delta ? `<div class="kpi-delta ${k.deltaDir}">${k.delta}</div>` : ''}
      </div>
    `).join('');

    // Ecosystem growth chart (overview)
    const channels = eco.map(r => r.active_channels);
    const edges = eco.map(r => r.edges);
    drawLineChart('canvasEcosystemGrowth', [
      { label: 'Channels', data: channels, color: COLORS.cyan, fill: true },
      { label: 'Edges', data: edges, color: COLORS.blue, fill: false },
    ], YEAR_LABELS, { yMin: 0, yDecimals: 0, yFmt: v => Math.round(v).toLocaleString() });

    // Modularity / density chart
    const mod = eco.map(r => r.modularity);
    const dens = eco.map(r => r.density);
    drawLineChart('canvasModDensity', [
      { label: 'Modularity Q', data: mod, color: COLORS.violet },
      { label: 'Density', data: dens, color: COLORS.amber },
    ], YEAR_LABELS, { yDecimals: 3 });

    // Cohort survival overview
    renderSurvivalOverview();

    // Quality overview
    renderQualityOverview();

    // Structural breaks table
    renderBreaksTable();
  }

  function renderSurvivalOverview() {
    const surv = DATA.cohorts?.survival_curve;
    if (!surv) return;

    // Group by elapsed_years
    const byElapsed = {};
    surv.forEach(r => {
      const key = r.elapsed_years ?? r.elapsed_horizon;
      if (!byElapsed[key]) byElapsed[key] = r;
    });

    const elapsed = Object.keys(byElapsed).map(Number).sort((a,b) => a-b);
    const rates = elapsed.map(e => {
      const r = byElapsed[e];
      const rate = r.persistence_rate ?? r.pooled_continuation_rate ?? r.continuation_rate;
      return typeof rate === 'number' ? (rate > 1 ? rate / 100 : rate) : null;
    });

    drawLineChart('canvasSurvivalOverview', [
      { label: 'Persistence Rate', data: rates, color: COLORS.emerald, fill: true },
    ], elapsed.map(e => '+' + e + 'y'), { yMin: 0, yMax: 1, yDecimals: 0, yFmt: v => (v*100).toFixed(0) + '%' });
  }

  function renderQualityOverview() {
    const yq = DATA.quality?.yearly_quality;
    if (!yq) return;

    const years = yq.map(r => String(r.year));
    const interactions = yq.map(r => r.total_interactions || r.interactions || 0);
    drawBarChart('canvasQualityOverview', interactions, years, {
      color: COLORS.cyan,
      valFmt: v => v.toLocaleString(),
    });
  }

  function renderBreaksTable() {
    const breaks = DATA.ecosystem?.structural_breaks;
    if (!breaks || breaks.length === 0) return;

    const headers = ['Transition', 'Metric', 'Category', 'Shift'];
    const rows = breaks.map(b => [
      b.transition || `${b.from_year || ''}→${b.to_year || ''}`,
      b.metric_dimension || b.metric || '',
      tagify(b.category || '', 'tag-mod'),
      b.relative_shift ? (b.relative_shift > 0 ? '+' : '') + (b.relative_shift * 100).toFixed(1) + '%' : (b.descriptive_context || ''),
    ]);

    document.getElementById('breaksTable').innerHTML = buildTable(headers, rows);
  }

  // ── ECOSYSTEM ─────────────────────────────────────────────

  function renderEcosystem() {
    const eco = DATA.ecosystem?.yearly_metrics;
    if (!eco) return;

    // Full metrics table
    const headers = ['Year', 'Channels', 'Edges', 'Density', 'Avg Degree', 'Giant %', 'Q', 'Deg Gini', 'Ag Assort', 'Cross-Comm %'];
    const rows = eco.map(r => {
      const yr = r.year === 2026 ? '2026 (YTD)' : String(r.year);
      return [
        yr,
        fmtNum(r.active_channels),
        fmtNum(r.edges),
        r.density?.toFixed(4) || '–',
        r.avg_degree?.toFixed(1) || '–',
        fmtPct(r.giant_component_share || r.giant_share, 1),
        r.modularity?.toFixed(3) || '–',
        r.degree_gini?.toFixed(3) || '–',
        r.agency_assortativity?.toFixed(3) || '–',
        fmtPct(r.cross_community_edge_share || r.cross_comm_share, 1),
      ];
    });
    document.getElementById('ecosystemTable').innerHTML = buildTable(headers, rows);

    // Charts
    const channels = eco.map(r => r.active_channels);
    const edges = eco.map(r => r.edges);
    drawLineChart('canvasEcoFull', [
      { label: 'Channels', data: channels, color: COLORS.cyan, fill: true },
      { label: 'Edges', data: edges, color: COLORS.blue },
    ], YEAR_LABELS, { yMin: 0, yDecimals: 0, yFmt: v => Math.round(v).toLocaleString() });

    const mod = eco.map(r => r.modularity);
    const dens = eco.map(r => r.density);
    drawLineChart('canvasEcoModDens', [
      { label: 'Modularity', data: mod, color: COLORS.violet },
      { label: 'Density', data: dens, color: COLORS.amber },
    ], YEAR_LABELS, { yDecimals: 3 });

    const assort = eco.map(r => r.agency_assortativity);
    drawLineChart('canvasAgencyAssort', [
      { label: 'Agency Assortativity', data: assort, color: COLORS.pink, fill: true },
    ], YEAR_LABELS, { yDecimals: 3 });

    const crossComm = eco.map(r => r.cross_community_edge_share || r.cross_comm_share);
    drawLineChart('canvasCrossComm', [
      { label: 'Cross-Community %', data: crossComm, color: COLORS.emerald, fill: true },
    ], YEAR_LABELS, { yDecimals: 3, yFmt: v => (v*100).toFixed(1) + '%' });
  }

  // ── LINEAGE ───────────────────────────────────────────────

  function renderLineage() {
    const lc = DATA.lineage?.lifecycles;
    if (!lc) return;

    // Lifecycle table
    const headers = ['Lineage', 'Birth', 'Last', 'Span', 'Status', 'Dom Agency', 'Share', 'Creators', 'Churn'];
    const rows = lc.map(r => [
      r.lineage_id || '',
      r.birth_year || '',
      r.last_observed_year || r.last_observed || '',
      r.lifespan_years || r.lifespan || '',
      tagify(r.status || '', r.status === 'ACTIVE' ? 'tag-active' : 'tag-disappeared'),
      r.dominant_agency || '',
      fmtPct(r.dominant_agency_share || r.agency_share, 1),
      fmtNum(r.total_unique_creators || r.total_creators || 0),
      fmtPct(r.mean_churn_rate || r.churn_rate, 1),
    ]);
    document.getElementById('lineageLifecycleTable').innerHTML = buildTable(headers, rows);

    // Timeline Gantt
    renderLineageTimeline(lc);

    // Transitions table
    const trans = DATA.lineage?.transitions;
    if (trans && trans.length > 0) {
      const tHeaders = ['Years', 'From', 'To', 'Relation', 'Shared', 'Jaccard', 'Fwd', 'Bwd'];
      const tRows = trans.map(t => [
        `${t.from_year || t.year_from || ''}→${t.to_year || t.year_to || ''}`,
        t.from_lineage || t.source_lineage || '',
        t.to_lineage || t.target_lineage || '',
        tagify(t.relation_type || t.relation || '', getRelationTag(t.relation_type || t.relation)),
        fmtNum(t.shared_channels || t.shared || 0),
        (t.jaccard || 0).toFixed(3),
        fmtPct(t.forward_overlap || t.fwd_overlap, 1),
        fmtPct(t.backward_overlap || t.bwd_overlap, 1),
      ]);
      document.getElementById('lineageTransitionsTable').innerHTML = buildTable(tHeaders, tRows);
    }
  }

  function getRelationTag(rel) {
    if (!rel) return 'tag-mod';
    if (rel.includes('continuation')) return 'tag-continuation';
    if (rel.includes('split')) return 'tag-split';
    if (rel.includes('merge')) return 'tag-merge';
    return 'tag-mod';
  }

  function renderLineageTimeline(lifecycles) {
    const c = getCtx('canvasLineageTimeline');
    if (!c) return;
    const { ctx, w, h } = c;
    const pad = { top: 20, right: 30, bottom: 30, left: 100 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const years = [2020, 2021, 2022, 2023, 2024, 2025, 2026];
    const rowH = Math.min(plotH / lifecycles.length, 22);

    // x axis
    years.forEach((yr, i) => {
      const x = pad.left + (plotW * i / (years.length - 1));
      ctx.fillStyle = '#9298aa';
      ctx.font = '11px "JetBrains Mono"';
      ctx.textAlign = 'center';
      ctx.fillText(String(yr), x, h - pad.bottom + 18);

      ctx.strokeStyle = 'rgba(148,163,184,0.06)';
      ctx.beginPath();
      ctx.moveTo(x, pad.top);
      ctx.lineTo(x, pad.top + plotH);
      ctx.stroke();
    });

    // rows
    lifecycles.forEach((lc, idx) => {
      const y = pad.top + idx * rowH + rowH / 2;
      const birth = lc.birth_year || 2020;
      const last = lc.last_observed_year || lc.last_observed || birth;

      const x1 = pad.left + (plotW * (birth - 2020) / 6);
      const x2 = pad.left + (plotW * (last - 2020) / 6);

      // label
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px "JetBrains Mono"';
      ctx.textAlign = 'right';
      ctx.fillText(lc.lineage_id || `L${idx+1}`, pad.left - 8, y + 4);

      // bar
      const color = lc.status === 'ACTIVE' ? COLORS.cyan : COLORS.slate;
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.7;
      ctx.beginPath();
      ctx.roundRect(x1, y - 5, Math.max(x2 - x1, 8), 10, 3);
      ctx.fill();
      ctx.globalAlpha = 1;

      // dots at endpoints
      [x1, x2].forEach(x => {
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      });
    });
  }

  // ── COHORTS ───────────────────────────────────────────────

  function renderCohorts() {
    // Survival chart
    const surv = DATA.cohorts?.survival_curve;
    if (surv) {
      const byElapsed = {};
      surv.forEach(r => {
        const key = r.elapsed_years ?? r.elapsed_horizon;
        if (!byElapsed[key]) byElapsed[key] = r;
      });

      const elapsed = Object.keys(byElapsed).map(Number).sort((a,b) => a-b);
      const rates = elapsed.map(e => {
        const r = byElapsed[e];
        const rate = r.persistence_rate ?? r.pooled_continuation_rate ?? r.continuation_rate;
        return typeof rate === 'number' ? (rate > 1 ? rate / 100 : rate) : null;
      });
      const sameChannel = elapsed.map(e => {
        const r = byElapsed[e];
        const rate = r.same_channel_persistence ?? r.same_channel_rate;
        return typeof rate === 'number' ? (rate > 1 ? rate / 100 : rate) : null;
      });
      const crossChannel = elapsed.map(e => {
        const r = byElapsed[e];
        const rate = r.cross_channel_persistence ?? r.cross_channel_rate;
        return typeof rate === 'number' ? (rate > 1 ? rate / 100 : rate) : null;
      });

      const datasets = [
        { label: 'Total Persistence', data: rates, color: COLORS.emerald, fill: true },
      ];
      if (sameChannel.some(v => v !== null)) {
        datasets.push({ label: 'Same-Channel', data: sameChannel, color: COLORS.cyan });
      }
      if (crossChannel.some(v => v !== null)) {
        datasets.push({ label: 'Cross-Channel', data: crossChannel, color: COLORS.violet });
      }

      drawLineChart('canvasCohortSurvival', datasets,
        elapsed.map(e => '+' + e + 'y'), { yMin: 0, yMax: 1, yDecimals: 0, yFmt: v => (v*100).toFixed(0) + '%' });
    }

    // Retention matrix
    const ret = DATA.cohorts?.retention_matrix;
    if (ret && ret.length > 0) {
      const headers = ['Cohort', 'Size', 'Obs Year', 'Elapsed', 'Re-Obs', 'Rate', 'Same-Ch', 'Cross-Ch'];
      const rows = ret.map(r => [
        r.cohort_year || r.first_observed_year || '',
        fmtNum(r.cohort_size || r.cohort_count || 0),
        r.observation_year || r.obs_year || '',
        `+${r.elapsed_years ?? r.elapsed ?? 0}`,
        fmtNum(r.reobserved_viewers || r.re_observed || 0),
        fmtPct(r.continuation_rate || r.persistence_rate || 0, 1),
        fmtNum(r.same_channel_retained || r.same_channel || 0),
        fmtNum(r.cross_channel_viewers || r.cross_channel || 0),
      ]);
      document.getElementById('cohortRetentionTable').innerHTML = buildTable(headers, rows);
    }

    // Reactivation
    const react = DATA.cohorts?.reactivation;
    if (react && react.length > 0) {
      // Group by gap duration
      const byGap = {};
      react.forEach(r => {
        const gap = r.gap_duration || r.gap_years || 0;
        if (!byGap[gap]) byGap[gap] = 0;
        byGap[gap] += (r.reactivated_viewers || r.reactivated || 0);
      });

      const gaps = Object.keys(byGap).map(Number).sort((a,b) => a-b);
      const counts = gaps.map(g => byGap[g]);

      drawBarChart('canvasReactivation', counts, gaps.map(g => g + 'yr gap'), {
        color: COLORS.amber,
        valFmt: v => v.toLocaleString(),
      });
    }
  }

  // ── CENTRALITY ────────────────────────────────────────────

  function renderCentrality() {
    const bridges = DATA.centrality?.bridge_dynamics;
    if (bridges && bridges.length > 0) {
      const headers = ['Channel', 'Classification', 'Years Appeared', 'Peak Year', 'Stability'];
      const seen = new Set();
      const uniqueBridges = bridges.filter(b => {
        const key = b.channel_name || b.channel_id || '';
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });

      const rows = uniqueBridges.slice(0, 50).map(b => [
        b.channel_name || b.channel_id || '',
        tagify(b.structural_classification || b.classification || '', 'tag-active'),
        fmtNum(b.years_appeared || b.appearances || 0),
        b.peak_year || '–',
        b.stability_note || b.stability_ratio?.toFixed(2) || '–',
      ]);
      document.getElementById('bridgeTable').innerHTML = buildTable(headers, rows);
    }

    // Change points
    const cps = DATA.centrality?.change_points;
    if (cps && cps.length > 0) {
      // Count ascents vs declines per year
      const byYear = {};
      cps.forEach(cp => {
        const yr = cp.year || cp.to_year || 0;
        if (!byYear[yr]) byYear[yr] = { ascent: 0, decline: 0 };
        const delta = cp.delta_pct ?? cp.delta ?? 0;
        if (delta > 0) byYear[yr].ascent++;
        else byYear[yr].decline++;
      });

      const years = Object.keys(byYear).sort();
      const ascents = years.map(y => byYear[y].ascent);
      const declines = years.map(y => -byYear[y].decline);

      drawLineChart('canvasChangePoints', [
        { label: 'Ascents', data: ascents, color: COLORS.emerald },
        { label: 'Declines', data: declines, color: COLORS.red },
      ], years, { yDecimals: 0 });
    }
  }

  // ── QUALITY ───────────────────────────────────────────────

  function renderQuality() {
    const yq = DATA.quality?.yearly_quality;
    if (yq) {
      const headers = ['Year', 'Catalog', 'Sampled', 'Ratio', 'Interactions', 'Cap≥95 Rate', 'Tier'];
      const rows = yq.map(r => {
        const tier = r.evidence_tier || r.yearly_tier || '';
        const tierCls = tier === 'HIGH' ? 'tag-high' : tier === 'MODERATE' ? 'tag-mod' : 'tag-low';
        return [
          r.year === 2026 ? '2026 (YTD)' : String(r.year),
          fmtNum(r.catalog_videos || r.catalog_vids || 0),
          fmtNum(r.sampled_videos || r.sampled_vids || 0),
          fmtPct(r.sampling_ratio || r.sampling_rate || 0, 1),
          fmtNum(r.total_interactions || r.interactions || 0),
          fmtPct(r.cap_100_exposure_rate || r.cap_rate || 0, 1),
          tagify(tier, tierCls),
        ];
      });
      document.getElementById('qualityTable').innerHTML = buildTable(headers, rows);
    }

    // Tier donut
    const tierDist = DATA.quality?.channel_tier_distribution;
    if (tierDist) {
      const segments = [];
      if (tierDist.HIGH) segments.push({ label: 'HIGH', value: tierDist.HIGH, color: COLORS.emerald });
      if (tierDist.MODERATE) segments.push({ label: 'MODERATE', value: tierDist.MODERATE, color: COLORS.amber });
      if (tierDist.LOW) segments.push({ label: 'LOW', value: tierDist.LOW, color: COLORS.red });
      drawDonut('canvasTierDonut', segments, { centerLabel: 'Channels' });
    }

    // Sensitivity chart
    const sens = DATA.quality?.bias_sensitivity;
    if (sens && sens.length > 0) {
      // Group by year, show modularity across scenarios
      const scenarios = [...new Set(sens.map(s => s.scenario))];
      const years = [...new Set(sens.map(s => s.year))].sort();

      const datasets = scenarios.slice(0, 5).map((sc, i) => ({
        label: sc,
        data: years.map(yr => {
          const match = sens.find(s => s.year === yr && s.scenario === sc);
          return match?.modularity ?? null;
        }),
        color: COHORT_PALETTE[i % COHORT_PALETTE.length],
      }));

      drawLineChart('canvasSensitivity', datasets, years.map(String), { yDecimals: 3 });
    }
  }

  // ── Boot ──────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
