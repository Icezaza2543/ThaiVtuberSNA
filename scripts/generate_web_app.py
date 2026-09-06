"""
Thai VTuber Audience Network (SNA)
Generate web/app.js with embedded data, 3D sphere shading, and Agency Swarm Orbit Dynamics.
"""
import json
from pathlib import Path

WEB_DIR = Path("web")
with open(WEB_DIR / "data.json", "r", encoding="utf-8") as f:
    web_data = json.load(f)

json_str = json.dumps(web_data, ensure_ascii=False)

app_js_code = f"""/**
 * Thai VTuber Audience Network (SNA)
 * Interactive Force-Directed Swarm Visualizer
 *
 * Feature Highlights:
 * 1. Sphere Sizing: More Subscribers = Bigger Glowing 3D Spheres (ซับเยอะ = ลูกใหญ่)
 * 2. Agency Swarms: Matching Color Clusters Orbiting Closely Together (ค่ายเดียวกัน = swarm สีเดียวกัน โคจรติดๆ กัน)
 * 3. 3D Specular Shading: Glossy, tactile marble/orb rendering with inner rim lighting and outer neon aura
 * 4. Orbital Physics: Centripetal attraction + tangential velocity around celestial agency anchors
 * 5. Full Offline Support: Embedded dataset for instant file:/// browser launch
 */

// Embedded full dataset for 100% offline & file:/// execution
const EMBEDDED_DATA = {json_str};

// Agency Theme Palette
const AGENCY_COLORS = {{
  "Algorhythm Project": "#ec4899",
  "Pixela Project": "#10b981",
  "Virtual Zeven (VZ)": "#06b6d4",
  "Lumina Live": "#f59e0b",
  "Euphora Project": "#8b5cf6",
  "AStars Production": "#f43f5e",
  "Polygon Official": "#38bdf8",
  "Autumnia": "#ea580c",
  "DPX": "#eab308",
  "ALF": "#14b8a6",
  "Flora Project": "#84cc16",
  "OAL": "#2dd4bf",
  "V.W.Y": "#a855f7",
  "RPG": "#f97316",
  "Ti19t": "#6366f1",
  "HZ": "#d946ef",
  "Genesis Project": "#3b82f6",
  "EXia": "#0284c7",
  "WACTOR": "#fb923c",
  "EYLZ": "#ec4899",
  "Pandora": "#c084fc",
  "Vtopia": "#22d3ee",
  "Paralist": "#f472b6",
  "Loveland Project": "#fb7185",
  "STP": "#a3e635",
  "Independent": "#94a3b8"
}};

// State Variables
let rawData = EMBEDDED_DATA;
let graphNodes = [];
let graphEdges = [];
let nodeMap = new Map();
let agencySwarmAnchors = new Map();

// Camera & Pan/Zoom Transform
let panX = 0;
let panY = 0;
let zoom = 0.85;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;

// Interaction & Simulation Controls
let hoveredNode = null;
let selectedNode = null;
let draggedNode = null;
let spotlightBridges = false;
let swarmModeActive = true;
let swarmSpeedMultiplier = 1.0;
let currentMetric = "shared_viewers";
let minThreshold = 1;
let selectedAgency = "ALL";
let selectedTier = "ALL";
let searchQuery = "";
let pulseTime = 0;

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
const btnToggleSwarm = document.getElementById("btnToggleSwarm");
const swarmSpeedSlider = document.getElementById("swarmSpeedSlider");
const speedValue = document.getElementById("speedValue");
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
// 1. Initialization & Setup
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
    console.log("Using embedded dataset (direct file:/// mode)");
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
// 2. Swarm Celestial Anchors & Geometry
// ==========================================================
function setupAgencyAnchors() {{
  agencySwarmAnchors.clear();
  const agencies = (rawData.agencies || []).filter(a => a.name !== "Independent");
  const count = agencies.length;

  // Arrange agency swarms in a cosmic constellation ellipse
  const baseRadiusX = 580;
  const baseRadiusY = 440;

  agencies.forEach((ag, idx) => {{
    const angle = (idx / count) * 2 * Math.PI - Math.PI / 2;
    // Slight jitter to feel like natural galaxy arm
    const rVar = 1.0 + (idx % 3 === 0 ? 0.12 : (idx % 3 === 1 ? -0.08 : 0.02));
    const ax = Math.cos(angle) * (baseRadiusX * rVar);
    const ay = Math.sin(angle) * (baseRadiusY * rVar);

    agencySwarmAnchors.set(ag.name, {{
      x: ax,
      y: ay,
      baseX: ax,
      baseY: ay,
      name: ag.name,
      color: AGENCY_COLORS[ag.name] || "#38bdf8",
      memberCount: ag.member_count,
      // Alternating orbit directions for rich kinetic feeling
      orbitSpeed: (idx % 2 === 0 ? 0.006 : -0.006),
      spreadRadius: Math.max(75, Math.min(190, 50 + Math.sqrt(ag.member_count) * 28))
    }});
  }});

  // Center anchor for independent galaxy
  agencySwarmAnchors.set("Independent", {{
    x: 0,
    y: 0,
    baseX: 0,
    baseY: 0,
    name: "Independent",
    color: AGENCY_COLORS["Independent"],
    memberCount: 0,
    orbitSpeed: 0.001,
    spreadRadius: 360
  }});
}}

// ==========================================================
// 3. Data Processing & Sphere Sizing ("ซับเยอะ = ลูกใหญ่")
// ==========================================================
function calculateSphereRadius(subs) {{
  if (!subs || subs <= 0) return 7.5;
  // Power-law scaling: nano (~7-9px) to mega 500k+ (~44-46px)
  const k = Math.pow(subs / 1000, 0.42);
  return Math.max(7.5, Math.min(46, 7.5 + k * 3.6));
}}

function processGraphData() {{
  panX = container.clientWidth / 2;
  panY = container.clientHeight / 2;

  // Initialize node physics around agency anchors
  graphNodes = rawData.nodes.map((n, i) => {{
    const ag = n.agency || "Independent";
    const anchor = agencySwarmAnchors.get(ag) || agencySwarmAnchors.get("Independent");
    
    // Position initially around their agency anchor
    const localAngle = Math.random() * 2 * Math.PI;
    const localDist = Math.random() * (anchor.spreadRadius * 0.75);
    const initialX = anchor.x + Math.cos(localAngle) * localDist;
    const initialY = anchor.y + Math.sin(localAngle) * localDist;

    const r = calculateSphereRadius(n.subscribers);
    const nodeColor = AGENCY_COLORS[ag] || "#38bdf8";

    return {{
      ...n,
      x: initialX,
      y: initialY,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
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
        <span class="legend-color" style="background-color: ${{ag.color}}; box-shadow: 0 0 8px ${{ag.color}};"></span>
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

      // Pan to agency swarm
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
}}

// ==========================================================
// 5. Physics Engine & Agency Swarm Orbit Dynamics
// ==========================================================
function simulationLoop() {{
  pulseTime += 0.035;
  updatePhysics();
  renderCanvas();
  requestAnimationFrame(simulationLoop);
}}

function updatePhysics() {{
  const visibleNodes = graphNodes.filter(n => n.visible);
  const visibleEdges = graphEdges.filter(e => e.visible);

  // 1. Swarm Attraction & Orbital Tangential Motion (โคจรติดๆ กัน)
  if (swarmModeActive) {{
    for (const node of visibleNodes) {{
      if (node === draggedNode) continue;
      const ag = node.agency || "Independent";
      const anchor = agencySwarmAnchors.get(ag);
      if (!anchor) continue;

      const dx = anchor.x - node.x;
      const dy = anchor.y - node.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;

      // Centripetal spring pull towards agency anchor
      const springK = (ag === "Independent") ? 0.0003 : 0.0016;
      node.vx += dx * springK;
      node.vy += dy * springK;

      // Orbital tangential velocity around swarm center
      if (ag !== "Independent" && dist > 15) {{
        const tangentX = -dy / dist;
        const tangentY = dx / dist;
        const speed = anchor.orbitSpeed * swarmSpeedMultiplier * 1.6;
        node.vx += tangentX * speed;
        node.vy += tangentY * speed;
      }}
    }}
  }}

  // 2. Intra-Swarm & Inter-Node Repulsion (ป้องกันการชนซ้อนทับกัน)
  for (let i = 0; i < visibleNodes.length; i++) {{
    const na = visibleNodes[i];
    for (let j = i + 1; j < visibleNodes.length; j++) {{
      const nb = visibleNodes[j];
      const dx = nb.x - na.x;
      const dy = nb.y - na.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const minDist = na.radius + nb.radius + 8;

      // Strong repulsive cushion if spheres touch
      if (dist < minDist) {{
        const overlap = minDist - dist;
        const force = overlap * 0.12;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (na !== draggedNode) {{ na.vx -= fx; na.vy -= fy; }}
        if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
      }} else if (dist < 180 && na.agency === nb.agency && na.agency !== "Independent") {{
        // Soft intra-swarm spacing
        const force = 40 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (na !== draggedNode) {{ na.vx -= fx; na.vy -= fy; }}
        if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
      }}
    }}
  }}

  // 3. Edge Attraction (Audience Overlap Connection Springs)
  for (const edge of visibleEdges) {{
    const na = edge.sourceNode;
    const nb = edge.targetNode;
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    // Cross-agency colab springs
    const desiredDist = Math.max(60, 200 - Math.min(140, (edge.shared_viewers || 10) * 1.2));
    const delta = dist - desiredDist;
    const springForce = delta * 0.002;
    const fx = (dx / dist) * springForce;
    const fy = (dy / dist) * springForce;

    if (na !== draggedNode) {{ na.vx += fx; na.vy += fy; }}
    if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
  }}

  // 4. Center Galaxy Damping
  for (const node of visibleNodes) {{
    if (node === draggedNode) continue;
    node.vx -= node.x * 0.0002;
    node.vy -= node.y * 0.0002;

    node.vx *= 0.88; // Damping
    node.vy *= 0.88;

    node.x += node.vx;
    node.y += node.vy;
  }}
}}

// ==========================================================
// 6. Canvas Renderer & 3D Glossy Spheres ("ลูกกลมๆ 3 มิติ")
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

  // 1. Draw Swarm Orbital Rings & Nebula Boundaries
  if (swarmModeActive) {{
    for (const [agName, anchor] of agencySwarmAnchors.entries()) {{
      if (agName === "Independent") continue;
      if (selectedAgency !== "ALL" && selectedAgency !== agName) continue;

      const r = anchor.spreadRadius;

      // Faint orbital ellipse
      ctx.beginPath();
      ctx.arc(anchor.x, anchor.y, r, 0, 2 * Math.PI);
      ctx.strokeStyle = anchor.color;
      ctx.globalAlpha = 0.12;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 6]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Glowing swarm center badge
      ctx.globalAlpha = 0.75;
      ctx.font = "700 12px 'Outfit', sans-serif";
      ctx.fillStyle = anchor.color;
      ctx.textAlign = "center";
      ctx.fillText(`✨ ${{anchor.name}} (${{anchor.memberCount}})`, anchor.x, anchor.y - r - 8);
      ctx.globalAlpha = 1.0;
    }}
  }}

  // 2. Draw Edges
  for (const edge of visibleEdges) {{
    const isHovered = hoveredNode && (
      edge.sourceNode.id === hoveredNode.id || edge.targetNode.id === hoveredNode.id
    );
    const isDimmed = hoveredNode && !isHovered;

    let baseWidth = Math.max(1, Math.min(5, (edge.shared_viewers || 10) / 30));
    let alpha = isHovered ? 0.9 : (isDimmed ? 0.04 : 0.22);

    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.lineWidth = isHovered ? baseWidth + 2.5 : baseWidth;
    ctx.strokeStyle = isHovered ? "#38bdf8" : `rgba(148, 163, 184, ${{alpha}})`;
    ctx.stroke();
  }}

  // 3. Draw 3D Spheres ("ลูกกลมๆ")
  for (const node of visibleNodes) {{
    const isHovered = (hoveredNode && hoveredNode.id === node.id);
    const isNeighbor = (hoveredNode && neighborIds.has(node.id));
    const isDimmed = hoveredNode && !isNeighbor;
    const isBridgeSpotlight = spotlightBridges && node.betweenness > 0.05;
    const r = node.radius;

    ctx.save();
    ctx.translate(node.x, node.y);

    if (isDimmed) {{
      ctx.globalAlpha = 0.2;
    }}

    // Pulsing Outer Halo for Bridges or Tier S
    if (isBridgeSpotlight || node.priority === "S") {{
      const haloSize = r + 8 + Math.sin(pulseTime * 1.5) * 3;
      ctx.beginPath();
      ctx.arc(0, 0, haloSize, 0, 2 * Math.PI);
      ctx.strokeStyle = isBridgeSpotlight ? "rgba(245, 158, 11, 0.65)" : `${{node.color}}55`;
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }}

    // Outer Ambient Glow Aura
    ctx.shadowBlur = isHovered ? 28 : (node.priority === "S" ? 18 : 10);
    ctx.shadowColor = node.color;

    // 3D Sphere Radial Gradient: Specular Highlight at top-left
    const grad = ctx.createRadialGradient(
      -r * 0.32, -r * 0.32, r * 0.05,  // Specular center
      0, 0, r                          // Outer rim
    );
    grad.addColorStop(0, "#ffffff");            // Specular shine dot
    grad.addColorStop(0.2, lighten(node.color, 45)); // Light zone
    grad.addColorStop(0.65, node.color);        // True vibrant body
    grad.addColorStop(1, darken(node.color, 40));   // Ambient occlusion rim

    ctx.beginPath();
    ctx.arc(0, 0, r, 0, 2 * Math.PI);
    ctx.fillStyle = grad;
    ctx.fill();

    // Glossy Rim Lighting Ring
    ctx.shadowBlur = 0;
    ctx.lineWidth = isHovered ? 3 : 1.5;
    ctx.strokeStyle = isHovered ? "#ffffff" : "rgba(255, 255, 255, 0.4)";
    ctx.stroke();

    // Node Label
    if (isHovered || node.priority === "S" || node.priority === "A" || zoom > 1.2) {{
      ctx.font = `600 ${{Math.max(10, Math.min(13, r * 0.72))}}px 'Outfit', sans-serif`;
      ctx.fillStyle = isDimmed ? "rgba(148, 163, 184, 0.4)" : "#f8fafc";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const shortName = node.label.split(" ")[0] || node.label;
      ctx.fillText(shortName, 0, r + 13);
    }}

    ctx.restore();
  }}

  ctx.restore();
}}

// Color helpers for 3D sphere gradient
function lighten(color, percent) {{
  return adjustColor(color, percent);
}}
function darken(color, percent) {{
  return adjustColor(color, -percent);
}}
function adjustColor(hex, percent) {{
  hex = hex.replace("#", "");
  if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
  const num = parseInt(hex, 16);
  let r = (num >> 16) + Math.round(255 * (percent / 100));
  let g = ((num >> 8) & 0x00FF) + Math.round(255 * (percent / 100));
  let b = (num & 0x0000FF) + Math.round(255 * (percent / 100));
  r = Math.min(255, Math.max(0, r));
  g = Math.min(255, Math.max(0, g));
  b = Math.min(255, Math.max(0, b));
  return `#${{(r << 16 | g << 8 | b).toString(16).padStart(6, '0')}}`;
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
    // Auto-focus on search match
    if (searchQuery.length >= 2) {{
      const matched = graphNodes.find(n => n.visible);
      if (matched) {{
        panX = container.clientWidth / 2 - matched.x * zoom;
        panY = container.clientHeight / 2 - matched.y * zoom;
      }}
    }}
  }});

  // Agency Dropdown
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

  // Toggle Swarm Dynamics Button
  btnToggleSwarm.addEventListener("click", () => {{
    swarmModeActive = !swarmModeActive;
    btnToggleSwarm.classList.toggle("active", swarmModeActive);
    btnToggleSwarm.innerHTML = swarmModeActive 
      ? "<span>🌀 Swarm Orbit Dynamics (Active)</span>"
      : "<span>⏸ Swarm Orbit Dynamics (Paused)</span>";
  }});

  // Swarm Orbit Speed Slider
  swarmSpeedSlider.addEventListener("input", e => {{
    const val = Number(e.target.value);
    swarmSpeedMultiplier = val / 10;
    speedValue.textContent = `${{swarmSpeedMultiplier.toFixed(1)}}x`;
  }});

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
    if (dx * dx + dy * dy <= (node.radius + 6) * (node.radius + 6)) {{
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
  const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
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

print(f"Generated web/app.js successfully ({len(app_js_code):,} bytes)!")
