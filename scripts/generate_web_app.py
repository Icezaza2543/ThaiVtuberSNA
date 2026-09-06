"""
Thai VTuber Audience Network (SNA)
Generate web/app.js - True Obsidian Graph Archipelago Layout with Distance-Capped Stable Physics
"""
import json
from pathlib import Path

WEB_DIR = Path("web")
with open(WEB_DIR / "data.json", "r", encoding="utf-8") as f:
    web_data = json.load(f)

json_str = json.dumps(web_data, ensure_ascii=False)

app_js_code = f"""/**
 * Thai VTuber Audience Network (SNA)
 * Obsidian-Style 2D Graph Archipelago Visualizer
 *
 * 1. 2D Flat Minimalist Circles (Obsidian Graph View style)
 * 2. Modest Sizing by Subscribers: 3.5px (nano) to 13.5px (top)
 * 3. Spatial Swarm Archipelago: Dedicated, spacious island coordinates for each agency
 * 4. Central Bridge Crossroads: Inter-agency bridge VTubers (Aisha, Hoku, Schneider, Baabel, etc.)
 * 5. Outer Starfield: Solo independent VTubers rest peacefully in wide, collision-free celestial orbits
 * 6. Distance-Capped Repulsion (<60px only): Zero cross-island repulsion, ZERO explosion!
 * 7. Strict Velocity Clamping (max 1.0 px/frame) & Heavy Damping (0.70): Mathematically cannot scatter!
 * 8. 1-Second Sleep: Settles smoothly and freezes into a pristine Obsidian star map
 */

// Embedded dataset for 100% offline & file:/// execution
const EMBEDDED_DATA = {json_str};

// Agency Theme Palette (Obsidian-style solid flat tones)
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
  "ATX": "#38bdf8",
  "Independent": "#64748b"         // Obsidian Calm Slate Gray
}};

// Pre-defined Archipelago Island Coordinates for Agency Swarms
// Generously spaced so NO agency ever collides with or overlaps another
const AGENCY_ISLAND_COORDINATES = {{
  // 4 Major Cardinal Wings
  "Algorhythm Project": {{ x: -380, y: -240, r: 85 }},
  "Pixela Project": {{ x: 380, y: -240, r: 80 }},
  "Virtual Zeven (VZ)": {{ x: 380, y: 240, r: 75 }},
  "Lumina Live": {{ x: -380, y: 240, r: 70 }},

  // North & South Flanks
  "AStars Production": {{ x: -140, y: -380, r: 55 }},
  "Polygon Official": {{ x: 140, y: -380, r: 50 }},
  "Autumnia": {{ x: 140, y: 380, r: 50 }},
  "Flora Project": {{ x: -140, y: 380, r: 45 }},
  "Paralist": {{ x: 0, y: 380, r: 35 }},

  // East & West Outer Outposts
  "Euphora Project": {{ x: 530, y: 0, r: 60 }},
  "DPX": {{ x: 540, y: 160, r: 50 }},
  "Ti19t": {{ x: 540, y: -160, r: 35 }},
  "ALF": {{ x: -530, y: 0, r: 45 }},
  "V.W.Y": {{ x: -540, y: 160, r: 40 }},
  "OAL": {{ x: -540, y: -160, r: 40 }},

  // Mid-Range Satellites
  "HZ": {{ x: 350, y: 0, r: 35 }},
  "RPG": {{ x: -350, y: 0, r: 35 }},
  "Genesis Project": {{ x: -250, y: -130, r: 30 }},
  "EXia": {{ x: 250, y: -130, r: 30 }},
  "WACTOR": {{ x: 250, y: 130, r: 30 }},
  "STP": {{ x: -250, y: 130, r: 30 }},
  "Loveland Project": {{ x: 130, y: 240, r: 30 }},
  "ATX": {{ x: -130, y: 240, r: 30 }},
  "EYLZ": {{ x: -130, y: -240, r: 30 }},
  "Pandora": {{ x: 130, y: -240, r: 30 }},
  "Vtopia": {{ x: 0, y: -380, r: 30 }}
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
let zoom = 0.85; // Fit whole archipelago comfortably on load
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

// Physics Settings (Obsidian-Style Calm Physics with Quick Settling)
let alpha = 1.0;
let isSleeping = false;
let repulsionStrength = 140;
let linkDistance = 50;

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
// 2. Swarm Archipelago Anchors Setup
// ==========================================================
function setupAgencyAnchors() {{
  agencySwarmAnchors.clear();
  const agencies = (rawData.agencies || []).filter(a => a.name !== "Independent");

  agencies.forEach((ag, idx) => {{
    const coord = AGENCY_ISLAND_COORDINATES[ag.name] || {{
      x: Math.cos((idx / agencies.length) * 2 * Math.PI) * 440,
      y: Math.sin((idx / agencies.length) * 2 * Math.PI) * 320,
      r: 40
    }};

    agencySwarmAnchors.set(ag.name, {{
      x: coord.x,
      y: coord.y,
      radius: coord.r,
      name: ag.name,
      color: AGENCY_COLORS[ag.name] || "#38bdf8",
      memberCount: ag.member_count
    }});
  }});
}}

// ==========================================================
// 3. Node Sizing & Collision-Free Pre-Placement
// ==========================================================
function calculate2DRadius(subs) {{
  if (!subs || subs <= 0) return 3.5;
  // Obsidian scale: 3.5px for small nano to 13.5px for top channels
  const logSubs = Math.log10(Math.max(10, subs));
  return Math.max(3.5, Math.min(13.5, 3.5 + (logSubs - 1) * 1.9));
}}

function processGraphData() {{
  panX = container.clientWidth / 2;
  panY = container.clientHeight / 2;

  // Identify nodes with active edges (connected creators)
  const connectedNodeIds = new Set();
  (rawData.edges || []).forEach(e => {{
    connectedNodeIds.add(e.source);
    connectedNodeIds.add(e.target);
  }});

  // Count solo indies for smooth celestial distribution
  const soloIndies = (rawData.nodes || []).filter(
    n => (n.agency === "Independent" || !n.agency) && !connectedNodeIds.has(n.id)
  );
  const totalSolo = Math.max(1, soloIndies.length);

  let bridgeIndieIndex = 0;
  let soloIndieIndex = 0;
  const agencyMemberCounters = {{}};

  // Place nodes on clean, non-overlapping coordinates from Frame 0
  graphNodes = rawData.nodes.map((n) => {{
    const ag = n.agency || "Independent";
    const isConnected = connectedNodeIds.has(n.id);
    let initialX = 0;
    let initialY = 0;
    let isBridge = false;

    if (ag !== "Independent" && agencySwarmAnchors.has(ag)) {{
      // Agency Swarm: Sunflower spiral inside the agency's island
      const anchor = agencySwarmAnchors.get(ag);
      agencyMemberCounters[ag] = (agencyMemberCounters[ag] || 0) + 1;
      const mIdx = agencyMemberCounters[ag];
      
      if (mIdx === 1) {{
        initialX = anchor.x;
        initialY = anchor.y;
      }} else {{
        const angle = mIdx * 2.399963; // Golden angle
        const spread = 12 + Math.sqrt(mIdx) * 13;
        initialX = anchor.x + Math.cos(angle) * spread;
        initialY = anchor.y + Math.sin(angle) * spread;
      }}
    }} else if (isConnected) {{
      // Central Bridge Crossroads: Independent creators who connect agencies (Aisha, Hoku, etc.)
      isBridge = true;
      bridgeIndieIndex++;
      if (bridgeIndieIndex === 1) {{
        initialX = 0;
        initialY = 0;
      }} else {{
        const angle = bridgeIndieIndex * 2.399963;
        // Spacious dispersion: 40px to 170px so labels have plenty of room
        const spread = 40 + Math.sqrt(bridgeIndieIndex) * 28;
        initialX = Math.cos(angle) * spread;
        initialY = Math.sin(angle) * (spread * 0.78);
      }}
    }} else {{
      // Outer Celestial Starfield: Solo independent VTubers orbiting serenely on the outer rim
      soloIndieIndex++;
      const starAngle = (soloIndieIndex / totalSolo) * 2 * Math.PI;
      // Elliptical ring at 560px - 660px framing the archipelago like a starry night sky
      const starRadius = 560 + (soloIndieIndex % 5) * 26 + Math.sin(soloIndieIndex * 3) * 18;
      initialX = Math.cos(starAngle) * starRadius;
      initialY = Math.sin(starAngle) * (starRadius * 0.76);
    }}

    const r = calculate2DRadius(n.subscribers);
    const nodeColor = AGENCY_COLORS[ag] || "#64748b";

    return {{
      ...n,
      x: initialX,
      y: initialY,
      homeX: initialX,
      homeY: initialY,
      vx: 0,
      vy: 0,
      radius: r,
      color: nodeColor,
      isBridgeIndie: isBridge,
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
  reheatSimulation(0.8);
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
      }} else if (selectedAgency === "Independent") {{
        panX = container.clientWidth / 2;
        panY = container.clientHeight / 2;
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
// 5. Obsidian Physics Engine (100% Non-Exploding, Distance-Capped)
// ==========================================================
function simulationLoop() {{
  if (!isSleeping) {{
    updatePhysics();
  }}
  renderCanvas();
  requestAnimationFrame(simulationLoop);
}}

function updatePhysics() {{
  // Fast alpha cooling: graph breathes for ~1 second and sleeps completely
  alpha *= 0.94;
  if (alpha < 0.005) {{
    alpha = 0.0;
    isSleeping = true;
    return;
  }}

  const visibleNodes = graphNodes.filter(n => n.visible);
  const visibleEdges = graphEdges.filter(e => e.visible);

  // 1. Soft Distance-Capped Repulsion (< 60px only!)
  // Nodes farther than 60px exert ZERO force. Completely eliminates global scattering!
  const MAX_REPULSION_DIST = 60;
  const MAX_REP_DIST_SQ = MAX_REPULSION_DIST * MAX_REPULSION_DIST; // 3600

  for (let i = 0; i < visibleNodes.length; i++) {{
    const na = visibleNodes[i];
    for (let j = i + 1; j < visibleNodes.length; j++) {{
      const nb = visibleNodes[j];
      const dx = nb.x - na.x;
      const dy = nb.y - na.y;
      const distSq = dx * dx + dy * dy;

      // Ignore distant pairs entirely: zero inter-island pressure!
      if (distSq > MAX_REP_DIST_SQ || distSq < 0.5) continue;

      const dist = Math.sqrt(distSq);
      const minDist = na.radius + nb.radius + 4;
      let force = 0;

      if (dist < minDist) {{
        // Soft overlap resolution
        force = ((minDist - dist) / minDist) * 1.0 * alpha;
      }} else {{
        // Gentle local proximity buffer
        force = Math.min(0.6, (repulsionStrength / (distSq + 200)) * alpha);
      }}

      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      if (na !== draggedNode) {{ na.vx -= fx; na.vy -= fy; }}
      if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
    }}
  }}

  // 2. Link Attraction Springs (Soft & strictly clamped)
  for (const edge of visibleEdges) {{
    const na = edge.sourceNode;
    const nb = edge.targetNode;
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    const delta = dist - linkDistance;
    // Strict clamp: max spring impulse 0.5px per frame
    const springForce = Math.max(-0.5, Math.min(0.5, delta * 0.015 * alpha));
    const fx = (dx / dist) * springForce;
    const fy = (dy / dist) * springForce;

    if (na !== draggedNode) {{ na.vx -= fx; na.vy -= fy; }}
    if (nb !== draggedNode) {{ nb.vx += fx; nb.vy += fy; }}
  }}

  // 3. Island & Home Coordinates Retention Springs
  for (const node of visibleNodes) {{
    if (node === draggedNode) continue;
    const ag = node.agency || "Independent";

    if (ag !== "Independent" && agencySwarmAnchors.has(ag)) {{
      const anchor = agencySwarmAnchors.get(ag);
      // Keeps node securely within its agency island
      node.vx += (anchor.x - node.x) * 0.04 * alpha;
      node.vy += (anchor.y - node.y) * 0.04 * alpha;
    }} else if (node.isBridgeIndie) {{
      // Bridge indies stay near the central nexus (homeX, homeY)
      node.vx += (node.homeX - node.x) * 0.035 * alpha;
      node.vy += (node.homeY - node.y) * 0.035 * alpha;
    }} else {{
      // Solo indies stay serene in their designated celestial starfield home
      node.vx += (node.homeX - node.x) * 0.035 * alpha;
      node.vy += (node.homeY - node.y) * 0.035 * alpha;
    }}
  }}

  // 4. Heavy Damping (0.70) & Strict Velocity Clamp (1.0 px/frame)
  // Mathematically impossible to fly off screen or explode
  for (const node of visibleNodes) {{
    if (node === draggedNode) continue;

    node.vx *= 0.70; // 30% reduction per frame
    node.vy *= 0.70;

    // Strict speed limit: max 1.0 px per frame!
    node.vx = Math.max(-1.0, Math.min(1.0, node.vx));
    node.vy = Math.max(-1.0, Math.min(1.0, node.vy));

    node.x += node.vx;
    node.y += node.vy;
  }}
}}

// ==========================================================
// 6. 2D Canvas Renderer ("Obsidian Graph View")
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

  // 1. Draw Agency Island Labels (Clean minimal floating text)
  if (selectedAgency === "ALL") {{
    for (const [agName, anchor] of agencySwarmAnchors.entries()) {{
      if (agName === "Independent") continue;
      ctx.font = "600 11px 'Outfit', sans-serif";
      ctx.fillStyle = `${{anchor.color}}99`;
      ctx.textAlign = "center";
      ctx.fillText(anchor.name, anchor.x, anchor.y - anchor.radius - 8);
    }}
  }}

  // 2. Draw 2D Edges (Thin, crisp lines)
  for (const edge of visibleEdges) {{
    const isHovered = hoveredNode && (
      edge.sourceNode.id === hoveredNode.id || edge.targetNode.id === hoveredNode.id
    );
    const isDimmed = hoveredNode && !isHovered;

    let baseWidth = Math.max(0.7, Math.min(2.0, (edge.shared_viewers || 10) / 50));
    let alphaVal = isHovered ? 0.9 : (isDimmed ? 0.02 : 0.12);

    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.lineWidth = isHovered ? baseWidth + 1.5 : baseWidth;
    ctx.strokeStyle = isHovered ? "#38bdf8" : `rgba(200, 215, 235, ${{alphaVal}})`;
    ctx.stroke();
  }}

  // 3. Draw 2D Flat Circles ("แบบ Obsidian ไม่หลอกตา")
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
      ctx.arc(0, 0, r + 3.5, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(245, 158, 11, 0.75)";
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
    ctx.strokeStyle = isHovered ? "#ffffff" : "rgba(255, 255, 255, 0.25)";
    ctx.stroke();

    // Node Label - Obsidian smart visibility logic
    const isMajorHub = (node.priority === "S" && (node.degree > 0.3 || node.betweenness > 0.04 || node.subscribers >= 150000));
    const shouldShowLabel = isHovered || isNeighbor || 
      (isMajorHub && zoom >= 0.7) || 
      (node.priority === "S" && zoom >= 1.0) || 
      (node.priority === "A" && zoom >= 1.35) || 
      (zoom >= 1.8);

    if (shouldShowLabel) {{
      const fontSize = isHovered ? 12 : Math.max(9, Math.min(12, r * 0.85));
      ctx.font = `${{isHovered ? "600" : "500"}} ${{fontSize}}px 'Outfit', sans-serif`;
      ctx.fillStyle = isDimmed ? "rgba(148, 163, 184, 0.25)" : (isHovered ? "#ffffff" : "#f1f5f9");
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const shortName = node.label.split(" ")[0] || node.label;
      ctx.fillText(shortName, 0, r + 3);
    }}

    ctx.restore();
  }}

  ctx.restore();
}}

// ==========================================================
// 7. Mouse & Touch Event Listeners
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
    }} else if (selectedAgency === "Independent") {{
      panX = container.clientWidth / 2;
      panY = container.clientHeight / 2;
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
      reheatSimulation(0.3);
    }});
  }}

  // Link Distance Slider
  if (linkDistSlider) {{
    linkDistSlider.addEventListener("input", e => {{
      linkDistance = Number(e.target.value);
      if (linkDistValue) linkDistValue.textContent = linkDistance;
      reheatSimulation(0.3);
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
    reheatSimulation(0.3);
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
    reheatSimulation(0.15);
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

print(f"Generated Archipelago Obsidian web/app.js successfully ({len(app_js_code):,} bytes)!")
