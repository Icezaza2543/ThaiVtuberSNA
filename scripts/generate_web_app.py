"""
Thai VTuber Audience Network (SNA)
Generate web/app.js - Obsidian-style 2D Graph View with Calm, Stable Physics
"""
import json
from pathlib import Path

WEB_DIR = Path("web")
with open(WEB_DIR / "data.json", "r", encoding="utf-8") as f:
    web_data = json.load(f)

json_str = json.dumps(web_data, ensure_ascii=False)

app_js_code = f"""/**
 * Thai VTuber Audience Network (SNA)
 * Obsidian-Style 2D Graph View Visualizer
 *
 * Designed for stability, clarity, and zero physics explosion:
 * 1. Clean 2D Flat Circles (Obsidian Graph View style)
 * 2. Scale by Subscribers: Small nano VTubers (3.5px) to Major VTubers (15px)
 * 3. Agency Swarms: Matching solid colors, clustered peacefully into cohesive groups
 * 4. Ultra-Stable Force Simulation with Alpha Cooling: Graph settles and sleeps smoothly
 * 5. Full Offline & file:/// Support with Embedded Dataset
 */

// Embedded full dataset for 100% offline & file:/// browser launch
const EMBEDDED_DATA = {json_str};

// Agency Theme Palette (Obsidian-style vibrant flat tones)
const AGENCY_COLORS = {{
  "Algorhythm Project": "#ec4899", // Neon Hot Pink
  "Pixela Project": "#10b981",     // Emerald Jade
  "Virtual Zeven (VZ)": "#06b6d4", // Electric Cyan
  "Lumina Live": "#f59e0b",        // Radiant Amber
  "Euphora Project": "#8b5cf6",    // Vivid Violet
  "AStars Production": "#f43f5e",  // Rose Crimson
  "Polygon Official": "#38bdf8",   // Sky Cerulean
  "Autumnia": "#ea580c",           // Autumn Flame
  "DPX": "#eab308",                // Cyber Yellow
  "ALF": "#14b8a6",                // Teal Mint
  "Flora Project": "#84cc16",      // Flora Lime
  "OAL": "#2dd4bf",                // Aquamarine
  "V.W.Y": "#a855f7",              // Lilac Purple
  "RPG": "#f97316",                // Tangerine Flame
  "Ti19t": "#6366f1",              // Indigo Neon
  "HZ": "#d946ef",                 // Fuchsia Pink
  "Genesis Project": "#3b82f6",    // Sapphire Blue
  "EXia": "#0284c7",               // Cobalt Blue
  "WACTOR": "#fb923c",             // Warm Amber
  "EYLZ": "#ec4899",
  "Pandora": "#c084fc",
  "Vtopia": "#22d3ee",
  "Paralist": "#f472b6",
  "Loveland Project": "#fb7185",
  "STP": "#a3e635",
  "Independent": "#64748b"         // Obsidian Calm Slate
}};

// State Variables
let rawData = EMBEDDED_DATA;
let graphNodes = [];
let graphEdges = [];
let nodeMap = new Map();
let agencySwarmAnchors = new Map();

// Camera & Pan/Zoom
let panX = 0;
let panY = 0;
let zoom = 0.95;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;

// Interaction & Simulation Controls
let hoveredNode = null;
let selectedNode = null;
let draggedNode = null;
let spotlightBridges = false;
let currentMetric = "shared_viewers";
let minThreshold = 1;
let selectedAgency = "ALL";
let selectedTier = "ALL";
let searchQuery = "";

// Physics Settings (Obsidian-Style Gentle Simulation)
let alpha = 1.0;                  // Cooling simulation factor
let isSleeping = false;           // When settled, physics pauses to save CPU & avoid jitter
let repulsionStrength = 260;      // Node spacing
let linkDistance = 65;            // Desired spring length

// Canvas Elements
const canvas = document.getElementById("networkCanvas");
const ctx = canvas.getContext("2d");
const container = document.getElementById("canvasContainer");

// UI Elements
const statVtubers = document.getElementById("statVtubers");
const statEdges = document.getElementById("statEdges");
const statCommunities = document.getElementById("statCommunities");
const statTopBridge = document.getElementById("statTopBridge");
const activeCount = document.getElementById("activeCount");
const searchInput = document.getElementById("searchInput");
const agencyFilter = document.getElementById("agencyFilter");
const tierFilter = document.getElementById("tierFilter");
const metricSelect = document.getElementById("metricSelect");
const thresholdSlider = document.getElementById("thresholdSlider");
const sliderValue = document.getElementById("sliderValue");
const btnToggleBridges = document.getElementById("btnToggleBridges");
const repulsionSlider = document.getElementById("repulsionSlider");
const repulsionValue = document.getElementById("repulsionValue");
const linkDistSlider = document.getElementById("linkDistSlider");
const linkDistValue = document.getElementById("linkDistValue");
const btnReheatSim = document.getElementById("btnReheatSim");
const dynamicLegendList = document.getElementById("dynamicLegendList");
const legendSwarmCount = document.getElementById("legendSwarmCount");
const inspectorPanel = document.getElementById("inspectorPanel");
const btnCloseInspector = document.getElementById("btnCloseInspector");
const infoModal = document.getElementById("infoModal");
const btnInfoModal = document.getElementById("btnInfoModal");
const btnCloseModal = document.getElementById("btnCloseModal");

// Inspector Elements
const inspName = document.getElementById("inspName");
const inspHandle = document.getElementById("inspHandle");
const inspTier = document.getElementById("inspTier");
const inspAgency = document.getElementById("inspAgency");
const inspSubs = document.getElementById("inspSubs");
const inspDegree = document.getElementById("inspDegree");
const inspBetweenness = document.getElementById("inspBetweenness");
const inspPageRank = document.getElementById("inspPageRank");
const inspConnectionsList = document.getElementById("inspConnectionsList");

// ==========================================================
// 1. Initialization
// ==========================================================
async function initApp() {{
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  try {{
    const res = await fetch("data.json");
    if (res.ok) {{
      rawData = await res.json();
    }}
  }} catch (e) {{
    console.log("Using embedded dataset (offline mode)");
    rawData = EMBEDDED_DATA;
  }}

  setupAgencyAnchors();
  populateAgencyFilter();
  populateDynamicLegend();
  setupEventListeners();
  processGraphData();
  updateKPIs();
  requestAnimationFrame(simulationLoop);
}}

function resizeCanvas() {{
  canvas.width = container.clientWidth * window.devicePixelRatio;
  canvas.height = container.clientHeight * window.devicePixelRatio;
  canvas.style.width = `${{container.clientWidth}}px`;
  canvas.style.height = `${{container.clientHeight}}px`;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
}}

// ==========================================================
// 2. Swarm Anchors Setup (Stationary Constellation Anchors)
// ==========================================================
function setupAgencyAnchors() {{
  agencySwarmAnchors.clear();
  const agencies = (rawData.agencies || []).filter(a => a.name !== "Independent");
  const count = agencies.length;

  // Distribute agency clusters gently in a circle
  const radius = 340;
  agencies.forEach((ag, idx) => {{
    const angle = (idx / count) * 2 * Math.PI - Math.PI / 2;
    const ax = Math.cos(angle) * radius;
    const ay = Math.sin(angle) * (radius * 0.85);

    agencySwarmAnchors.set(ag.name, {{
      x: ax,
      y: ay,
      name: ag.name,
      color: AGENCY_COLORS[ag.name] || "#38bdf8",
      memberCount: ag.member_count
    }});
  }});

  // Center anchor for independent VTubers
  agencySwarmAnchors.set("Independent", {{
    x: 0,
    y: 0,
    name: "Independent",
    color: AGENCY_COLORS["Independent"],
    memberCount: 0
  }});
}}

// ==========================================================
// 3. 2D Node Sizing & Processing ("2 มิติ ไม่ระเบิด")
// ==========================================================
function calculate2DRadius(subs) {{
  if (!subs || subs <= 0) return 3.5;
  // Obsidian scale: 3.5px for small nano to 14.5px for mega channels
  const logSubs = Math.log10(Math.max(10, subs));
  return Math.max(3.5, Math.min(14.5, 3.5 + (logSubs - 1) * 2.2));
}}

function processGraphData() {{
  panX = container.clientWidth / 2;
  panY = container.clientHeight / 2;

  // Initialize nodes clustered near their respective agency anchors
  graphNodes = rawData.nodes.map((n, i) => {{
    const ag = n.agency || "Independent";
    const anchor = agencySwarmAnchors.get(ag) || agencySwarmAnchors.get("Independent");
    
    // Controlled initial scatter (compact radius <= 60px)
    const angle = Math.random() * 2 * Math.PI;
    const dist = 10 + Math.random() * 55;
    const initialX = anchor.x + Math.cos(angle) * dist;
    const initialY = anchor.y + Math.sin(angle) * dist;

    const r = calculate2DRadius(n.subscribers);
    const nodeColor = AGENCY_COLORS[ag] || "#64748b";

    return {{
      ...n,
      x: initialX,
      y: initialY,
      vx: 0,
      vy: 0,
      radius: r,
      color: nodeColor,
      visible: true
    }};
  }});

  nodeMap.clear();
  graphNodes.forEach(n => nodeMap.set(n.id, n));

  // Initialize edges
  graphEdges = (rawData.edges || []).map(e => {{
    return {{
      ...e,
      sourceNode: nodeMap.get(e.source),
      targetNode: nodeMap.get(e.target),
      visible: true
    }};
  }}).filter(e => e.sourceNode && e.targetNode);

  applyFilters();
  reheatSimulation(1.0);
}}

function populateAgencyFilter() {{
  agencyFilter.innerHTML = '<option value="ALL">All Agencies (All Swarms)</option>';
  const agencies = rawData.agencies || [];
  agencies.forEach(ag => {{
    const opt = document.createElement("option");
    opt.value = ag.name;
    opt.textContent = `${{ag.name}} (${{ag.member_count}})`;
    agencyFilter.appendChild(opt);
  }});
}}

function populateDynamicLegend() {{
  dynamicLegendList.innerHTML = "";
  const agencies = rawData.agencies || [];
  legendSwarmCount.textContent = `${{agencies.length}} Swarms`;

  agencies.forEach(ag => {{
    const item = document.createElement("div");
    item.className = "legend-item";
    item.innerHTML = `
      <div class="legend-left">
        <span class="legend-color" style="background-color: ${{ag.color}};"></span>
        <span title="${{ag.name}}">${{ag.name}}</span>
      </div>
      <span class="legend-count">${{ag.member_count}}</span>
    `;
    item.addEventListener("click", () => {{
      selectedAgency = (selectedAgency === ag.name) ? "ALL" : ag.name;
      agencyFilter.value = selectedAgency;
      document.querySelectorAll(".legend-item").forEach(el => el.classList.remove("active-filter"));
      if (selectedAgency !== "ALL") item.classList.add("active-filter");
      applyFilters();

      if (selectedAgency !== "ALL" && agencySwarmAnchors.has(selectedAgency)) {{
        const anc = agencySwarmAnchors.get(selectedAgency);
        panX = container.clientWidth / 2 - anc.x * zoom;
        panY = container.clientHeight / 2 - anc.y * zoom;
      }}
    }});
    dynamicLegendList.appendChild(item);
  }});
}}

function updateKPIs() {{
  statVtubers.textContent = rawData.metadata.total_vtubers || graphNodes.length;
  statEdges.textContent = rawData.metadata.total_connections || graphEdges.length;
  statCommunities.textContent = rawData.metadata.agencies_count || (rawData.agencies || []).length;

  const sortedBridges = [...graphNodes].sort((a, b) => b.betweenness - a.betweenness);
  if (sortedBridges.length > 0 && sortedBridges[0].betweenness > 0) {{
    statTopBridge.textContent = sortedBridges[0].label.split(" ")[0];
  }} else {{
    statTopBridge.textContent = "Aisha";
  }}
}}

// ==========================================================
// 4. Filtering Logic
// ==========================================================
function applyFilters() {{
  let activeNodesCount = 0;

  graphNodes.forEach(n => {{
    const matchAgency = (selectedAgency === "ALL" || n.agency === selectedAgency);
    const matchTier = (selectedTier === "ALL" || n.priority === selectedTier);
    const matchSearch = !searchQuery || 
      n.label.toLowerCase().includes(searchQuery) || 
      (n.handle && n.handle.toLowerCase().includes(searchQuery));

    n.visible = matchAgency && matchTier && matchSearch;
    if (n.visible) activeNodesCount++;
  }});

  graphEdges.forEach(e => {{
    const nodesVisible = e.sourceNode.visible && e.targetNode.visible;
    const weightVal = e[currentMetric] || 0;
    if (currentMetric === "shared_viewers") {{
      e.visible = nodesVisible && (weightVal >= minThreshold);
    }} else {{
      e.visible = nodesVisible && (weightVal >= (minThreshold / 100));
    }}
  }});

  activeCount.textContent = `${{activeNodesCount}}/${{graphNodes.length}} Active`;
  reheatSimulation(0.3);
}}

function reheatSimulation(heat = 0.5) {{
  alpha = Math.max(alpha, heat);
  isSleeping = false;
}}

// ==========================================================
// 5. Obsidian Gentle Physics Simulation (Zero Explosion)
// ==========================================================
function simulationLoop() {{
  if (!isSleeping) {{
    updatePhysics();
  }}
  renderCanvas();
  requestAnimationFrame(simulationLoop);
}}

function updatePhysics() {{
  // Simulation cools down smoothly like Obsidian
  alpha *= 0.985;
  if (alpha < 0.005) {{
    alpha = 0.0;
    isSleeping = true; // Physics fully settles and stops!
    return;
  }}

  const visibleNodes = graphNodes.filter(n => n.visible);
  const visibleEdges = graphEdges.filter(e => e.visible);

  // 1. Soft, Capped Repulsion (Epsilon + 400 prevents division by zero singularity!)
  for (let i = 0; i < visibleNodes.length; i++) {{
    const na = visibleNodes[i];
    for (let j = i + 1; j < visibleNodes.length; j++) {{
      const nb = visibleNodes[j];
      const dx = nb.x - na.x;
      const dy = nb.y - na.y;
      const distSq = dx * dx + dy * dy + 400; // Epsilon damping
      const dist = Math.sqrt(distSq);

      // Controlled repulsion force
      const force = Math.min(1.8, (repulsionStrength / distSq) * alpha);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      if (na !== draggedNode) {{ na.vx -= fx; na.vy -= fy; }}
      if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
    }}
  }}

  // 2. Link Attraction Springs (Keeps connected nodes together)
  for (const edge of visibleEdges) {{
    const na = edge.sourceNode;
    const nb = edge.targetNode;
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    const delta = dist - linkDistance;
    const springForce = delta * 0.04 * alpha;
    const fx = (dx / dist) * springForce;
    const fy = (dy / dist) * springForce;

    if (na !== draggedNode) {{ na.vx += fx; na.vy += fy; }}
    if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
  }}

  // 3. Agency Swarm Cohesion (Pull members of same agency close together)
  for (const node of visibleNodes) {{
    if (node === draggedNode) continue;
    const ag = node.agency || "Independent";
    const anchor = agencySwarmAnchors.get(ag);
    if (!anchor) continue;

    if (ag !== "Independent") {{
      // Gentle cluster pull towards agency anchor
      node.vx += (anchor.x - node.x) * 0.012 * alpha;
      node.vy += (anchor.y - node.y) * 0.012 * alpha;
    }} else {{
      // Mild center pull for indies
      node.vx += (0 - node.x) * 0.003 * alpha;
      node.vy += (0 - node.y) * 0.003 * alpha;
    }}
  }}

  // 4. Heavy Damping & Strict Velocity Clamping (Nodes can NEVER shoot off)
  for (const node of visibleNodes) {{
    if (node === draggedNode) continue;

    node.vx *= 0.82; // Strong damping
    node.vy *= 0.82;

    // Strict speed limit: max 4.0 px per frame!
    node.vx = Math.max(-4.0, Math.min(4.0, node.vx));
    node.vy = Math.max(-4.0, Math.min(4.0, node.vy));

    node.x += node.vx;
    node.y += node.vy;
  }}
}}

// ==========================================================
// 6. Obsidian 2D Canvas Renderer ("แบบ 2 มิติ สะอาดตา")
// ==========================================================
function renderCanvas() {{
  const width = container.clientWidth;
  const height = container.clientHeight;

  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(zoom, zoom);

  const visibleNodes = graphNodes.filter(n => n.visible);
  const visibleEdges = graphEdges.filter(e => e.visible);

  // Set of hovered node neighbors
  const neighborIds = new Set();
  if (hoveredNode) {{
    neighborIds.add(hoveredNode.id);
    visibleEdges.forEach(e => {{
      if (e.sourceNode.id === hoveredNode.id) neighborIds.add(e.targetNode.id);
      if (e.targetNode.id === hoveredNode.id) neighborIds.add(e.sourceNode.id);
    }});
  }}

  // 1. Draw Agency Cluster Labels (Clean minimal floating text)
  if (selectedAgency === "ALL") {{
    for (const [agName, anchor] of agencySwarmAnchors.entries()) {{
      if (agName === "Independent") continue;
      ctx.font = "600 11px 'Outfit', sans-serif";
      ctx.fillStyle = `${{anchor.color}}88`;
      ctx.textAlign = "center";
      ctx.fillText(anchor.name, anchor.x, anchor.y - 45);
    }}
  }}

  // 2. Draw 2D Edges (Thin, clean lines)
  for (const edge of visibleEdges) {{
    const isHovered = hoveredNode && (
      edge.sourceNode.id === hoveredNode.id || edge.targetNode.id === hoveredNode.id
    );
    const isDimmed = hoveredNode && !isHovered;

    let baseWidth = Math.max(0.8, Math.min(2.5, (edge.shared_viewers || 10) / 45));
    let alphaVal = isHovered ? 0.9 : (isDimmed ? 0.02 : 0.15);

    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.lineWidth = isHovered ? baseWidth + 1.5 : baseWidth;
    ctx.strokeStyle = isHovered ? "#38bdf8" : `rgba(200, 210, 230, ${{alphaVal}})`;
    ctx.stroke();
  }}

  // 3. Draw 2D Flat Circles ("แบบ Obsidian ไม่ต้อง 3 มิติ")
  for (const node of visibleNodes) {{
    const isHovered = (hoveredNode && hoveredNode.id === node.id);
    const isNeighbor = (hoveredNode && neighborIds.has(node.id));
    const isDimmed = hoveredNode && !isNeighbor;
    const isBridgeSpotlight = spotlightBridges && node.betweenness > 0.05;
    const r = node.radius;

    ctx.save();
    ctx.translate(node.x, node.y);

    if (isDimmed) {{
      ctx.globalAlpha = 0.15;
    }}

    // Subtle bridge halo
    if (isBridgeSpotlight) {{
      ctx.beginPath();
      ctx.arc(0, 0, r + 4, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(245, 158, 11, 0.7)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }}

    // Clean 2D Flat Circle
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, 2 * Math.PI);
    ctx.fillStyle = node.color;
    ctx.fill();

    // Clean 2D Border
    ctx.lineWidth = isHovered ? 2.5 : 1.0;
    ctx.strokeStyle = isHovered ? "#ffffff" : "rgba(255, 255, 255, 0.3)";
    ctx.stroke();

    // Node Label (Clean & legible for important nodes or on hover)
    if (isHovered || node.priority === "S" || (node.priority === "A" && zoom > 1.1) || zoom > 1.6) {{
      ctx.font = `500 ${{Math.max(9, Math.min(12, r * 0.85))}}px 'Outfit', sans-serif`;
      ctx.fillStyle = isDimmed ? "rgba(148, 163, 184, 0.3)" : "#f1f5f9";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const shortName = node.label.split(" ")[0] || node.label;
      ctx.fillText(shortName, 0, r + 4);
    }}

    ctx.restore();
  }}

  ctx.restore();
}}

// ==========================================================
// 7. Mouse & Interactive Controls
// ==========================================================
function setupEventListeners() {{
  container.addEventListener("mousedown", onMouseDown);
  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
  container.addEventListener("wheel", onWheel, {{ passive: false }});

  // Search
  searchInput.addEventListener("input", e => {{
    searchQuery = e.target.value.toLowerCase().trim();
    applyFilters();
    if (searchQuery.length >= 2) {{
      const matched = graphNodes.find(n => n.visible);
      if (matched) {{
        panX = container.clientWidth / 2 - matched.x * zoom;
        panY = container.clientHeight / 2 - matched.y * zoom;
      }}
    }}
  }});

  // Agency Filter
  agencyFilter.addEventListener("change", e => {{
    selectedAgency = e.target.value;
    applyFilters();
    if (selectedAgency !== "ALL" && agencySwarmAnchors.has(selectedAgency)) {{
      const anc = agencySwarmAnchors.get(selectedAgency);
      panX = container.clientWidth / 2 - anc.x * zoom;
      panY = container.clientHeight / 2 - anc.y * zoom;
    }}
  }});

  // Tier Filter
  tierFilter.addEventListener("change", e => {{
    selectedTier = e.target.value;
    applyFilters();
  }});

  // Metric Select
  metricSelect.addEventListener("change", e => {{
    currentMetric = e.target.value;
    if (currentMetric === "shared_viewers") {{
      thresholdSlider.max = 150;
      thresholdSlider.value = 1;
      sliderValue.textContent = "1";
    }} else {{
      thresholdSlider.max = 100;
      thresholdSlider.value = 5;
      sliderValue.textContent = "5%";
    }}
    minThreshold = Number(thresholdSlider.value);
    applyFilters();
  }});

  // Threshold Slider
  thresholdSlider.addEventListener("input", e => {{
    minThreshold = Number(e.target.value);
    sliderValue.textContent = currentMetric === "shared_viewers" 
      ? minThreshold 
      : `${{minThreshold}}%`;
    applyFilters();
  }});

  // Repulsion Slider
  if (repulsionSlider) {{
    repulsionSlider.addEventListener("input", e => {{
      repulsionStrength = Number(e.target.value);
      if (repulsionValue) repulsionValue.textContent = repulsionStrength;
      reheatSimulation(0.4);
    }});
  }}

  // Link Distance Slider
  if (linkDistSlider) {{
    linkDistSlider.addEventListener("input", e => {{
      linkDistance = Number(e.target.value);
      if (linkDistValue) linkDistValue.textContent = linkDistance;
      reheatSimulation(0.4);
    }});
  }}

  // Reheat / Rearrange Button
  if (btnReheatSim) {{
    btnReheatSim.addEventListener("click", () => {{
      reheatSimulation(0.8);
    }});
  }}

  // Bridge Spotlight Button
  btnToggleBridges.addEventListener("click", () => {{
    spotlightBridges = !spotlightBridges;
    btnToggleBridges.classList.toggle("active", spotlightBridges);
  }});

  // Inspector Panel Close
  btnCloseInspector.addEventListener("click", () => {{
    inspectorPanel.classList.remove("open");
    selectedNode = null;
  }});

  // Info Modal
  btnInfoModal.addEventListener("click", () => infoModal.classList.add("open"));
  btnCloseModal.addEventListener("click", () => infoModal.classList.remove("open"));
  infoModal.addEventListener("click", e => {{
    if (e.target === infoModal) infoModal.classList.remove("open");
  }});
}}

function getGraphCoordinates(e) {{
  const rect = container.getBoundingClientRect();
  const screenX = e.clientX - rect.left;
  const screenY = e.clientY - rect.top;
  return {{
    x: (screenX - panX) / zoom,
    y: (screenY - panY) / zoom
  }};
}}

function findNodeAt(x, y) {{
  const visible = graphNodes.filter(n => n.visible);
  for (let i = visible.length - 1; i >= 0; i--) {{
    const node = visible[i];
    const dx = node.x - x;
    const dy = node.y - y;
    if (dx * dx + dy * dy <= (node.radius + 5) * (node.radius + 5)) {{
      return node;
    }}
  }}
  return null;
}}

function onMouseDown(e) {{
  const coords = getGraphCoordinates(e);
  const clicked = findNodeAt(coords.x, coords.y);

  if (clicked) {{
    draggedNode = clicked;
    reheatSimulation(0.4);
    openInspector(clicked);
  }} else {{
    isPanning = true;
    startPanX = e.clientX - panX;
    startPanY = e.clientY - panY;
  }}
}}

function onMouseMove(e) {{
  if (draggedNode) {{
    const coords = getGraphCoordinates(e);
    draggedNode.x = coords.x;
    draggedNode.y = coords.y;
    draggedNode.vx = 0;
    draggedNode.vy = 0;
    reheatSimulation(0.2);
    return;
  }}

  if (isPanning) {{
    panX = e.clientX - startPanX;
    panY = e.clientY - startPanY;
    return;
  }}

  const coords = getGraphCoordinates(e);
  const hovered = findNodeAt(coords.x, coords.y);
  hoveredNode = hovered;
  container.style.cursor = hovered ? "pointer" : (isPanning ? "grabbing" : "grab");
}}

function onMouseUp() {{
  draggedNode = null;
  isPanning = false;
}}

function onWheel(e) {{
  e.preventDefault();
  const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
  const newZoom = Math.max(0.25, Math.min(3.5, zoom * zoomFactor));

  const rect = container.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  panX = mouseX - (mouseX - panX) * (newZoom / zoom);
  panY = mouseY - (mouseY - panY) * (newZoom / zoom);
  zoom = newZoom;
}}

// ==========================================================
// 8. Inspector Card
// ==========================================================
function openInspector(node) {{
  selectedNode = node;
  inspName.textContent = node.label;
  inspHandle.textContent = node.handle || `@${{node.id}}`;
  inspTier.textContent = `Tier ${{node.priority}}`;
  inspAgency.textContent = node.agency;
  inspSubs.textContent = `${{node.subscribers.toLocaleString()}} Subs`;

  inspDegree.textContent = (node.degree || 0).toFixed(3);
  inspBetweenness.textContent = (node.betweenness || 0).toFixed(4);
  inspPageRank.textContent = node.pagerank ? node.pagerank.toFixed(3) : "0.000";

  // Find all overlaps connected to this VTuber
  const connections = [];
  graphEdges.forEach(e => {{
    if (e.sourceNode.id === node.id) {{
      connections.push({{ partner: e.targetNode, shared: e.shared_viewers, jaccard: e.jaccard }});
    }} else if (e.targetNode.id === node.id) {{
      connections.push({{ partner: e.sourceNode, shared: e.shared_viewers, jaccard: e.jaccard }});
    }}
  }});

  connections.sort((a, b) => b.shared - a.shared);

  inspConnectionsList.innerHTML = "";
  if (connections.length === 0) {{
    inspConnectionsList.innerHTML = `<div style="font-size:0.8rem; color: var(--text-muted);">No recorded stream overlap yet.</div>`;
  }} else {{
    const maxShared = connections[0].shared || 1;
    connections.slice(0, 6).forEach(c => {{
      const pct = Math.min(100, Math.round((c.shared / maxShared) * 100));
      const item = document.createElement("div");
      item.className = "connection-item";
      item.innerHTML = `
        <div class="connection-head">
          <span class="connection-name">${{c.partner.label}}</span>
          <span class="connection-shared">${{c.shared}} Viewers (${{(c.jaccard * 100).toFixed(1)}}%)</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${{pct}}%"></div>
        </div>
      `;
      item.addEventListener("click", () => {{
        openInspector(c.partner);
        panX = container.clientWidth / 2 - c.partner.x * zoom;
        panY = container.clientHeight / 2 - c.partner.y * zoom;
      }});
      inspConnectionsList.appendChild(item);
    }});
  }}

  inspectorPanel.classList.add("open");
}}

// Launch app on load
window.addEventListener("DOMContentLoaded", initApp);
"""

with open(WEB_DIR / "app.js", "w", encoding="utf-8") as f:
    f.write(app_js_code)

print(f"Generated Obsidian-style web/app.js successfully ({len(app_js_code):,} bytes)!")
