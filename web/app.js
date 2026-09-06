/**
 * Thai VTuber Audience Network (SNA)
 * Interactive Force-Directed Graph Visualizer
 */

// Fallback embedded dataset for direct file:/// viewing
const EMBEDDED_DATA = {
  "metadata": {
    "total_vtubers": 15,
    "total_connections": 28,
    "communities_count": 9
  },
  "nodes": [
    { "id": "UC_ARP001_SCHNEIDER", "label": "Schneider ARP", "handle": "@SchneiderARP", "subscribers": 185000, "agency": "Algorhythm Project", "priority": "S", "community": 0, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_ARP002_BAABEL", "label": "Baabel ARP", "handle": "@BaabelARP", "subscribers": 142000, "agency": "Algorhythm Project", "priority": "S", "community": 0, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_ARP003_MAYLYN", "label": "Maylyn ARP", "handle": "@MaylynARP", "subscribers": 128000, "agency": "Algorhythm Project", "priority": "S", "community": 0, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_ARP004_ZENITH", "label": "Zenith ARP", "handle": "@ZenithARP", "subscribers": 96000, "agency": "Algorhythm Project", "priority": "A", "community": 1, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_ARP005_DACAPO", "label": "Dacapo ARP", "handle": "@DacapoARP", "subscribers": 115000, "agency": "Algorhythm Project", "priority": "S", "community": 0, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_POLY001_HOKU", "label": "Hoku Polygon", "handle": "@HokuPolygon", "subscribers": 110000, "agency": "Polygon Official", "priority": "S", "community": 2, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_POLY002_LUCINE", "label": "Lucine Polygon", "handle": "@LucinePolygon", "subscribers": 89000, "agency": "Polygon Official", "priority": "A", "community": 0, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_POLY003_ZONA", "label": "Zona Polygon", "handle": "@ZonaPolygon", "subscribers": 64000, "agency": "Polygon Official", "priority": "A", "community": 3, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_PIX001_HINABE", "label": "Hinabe Pixela", "handle": "@HinabePixela", "subscribers": 78000, "agency": "Pixela Project", "priority": "A", "community": 2, "degree": 0.5, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_PIX002_MASHIRO", "label": "Mashiro Pixela", "handle": "@MashiroPixela", "subscribers": 52000, "agency": "Pixela Project", "priority": "A", "community": 4, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_INDIE001_AISHA", "label": "Aisha Channel", "handle": "@AishaChannelTH", "subscribers": 480000, "agency": "Independent", "priority": "S", "community": 0, "degree": 0.5, "betweenness": 0.1758, "pagerank": 0.0 },
    { "id": "UC_INDIE002_MEW", "label": "Mew Kitten", "handle": "@MewKittenTH", "subscribers": 35000, "agency": "Independent", "priority": "B", "community": 5, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_INDIE003_KORRA", "label": "Korra VT", "handle": "@KorraStreamer", "subscribers": 18000, "agency": "Independent", "priority": "B", "community": 6, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_INDIE004_ZEPHYR", "label": "Zephyr Sky", "handle": "@ZephyrChTH", "subscribers": 7500, "agency": "Independent", "priority": "C", "community": 7, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 },
    { "id": "UC_FOREIGN_001_TEST", "label": "Global Gamer JP", "handle": "@ForeignGamer", "subscribers": 250000, "agency": "Other", "priority": "S", "community": 8, "degree": 0.0, "betweenness": 0.0, "pagerank": 0.0 }
  ],
  "edges": [
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_ARP002_BAABEL", "shared_viewers": 105, "jaccard": 0.3134, "overlap_coefficient": 0.5585, "weight": 105.0 },
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_ARP005_DACAPO", "shared_viewers": 55, "jaccard": 0.1288, "overlap_coefficient": 0.2926, "weight": 55.0 },
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_ARP003_MAYLYN", "shared_viewers": 48, "jaccard": 0.1176, "overlap_coefficient": 0.2553, "weight": 48.0 },
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_POLY001_HOKU", "shared_viewers": 36, "jaccard": 0.1032, "overlap_coefficient": 0.1915, "weight": 36.0 },
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_PIX001_HINABE", "shared_viewers": 36, "jaccard": 0.1032, "overlap_coefficient": 0.1915, "weight": 36.0 },
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_POLY002_LUCINE", "shared_viewers": 35, "jaccard": 0.0964, "overlap_coefficient": 0.1862, "weight": 35.0 },
    { "source": "UC_ARP001_SCHNEIDER", "target": "UC_INDIE001_AISHA", "shared_viewers": 19, "jaccard": 0.0592, "overlap_coefficient": 0.125, "weight": 19.0 },
    { "source": "UC_ARP002_BAABEL", "target": "UC_ARP003_MAYLYN", "shared_viewers": 112, "jaccard": 0.2745, "overlap_coefficient": 0.4444, "weight": 112.0 },
    { "source": "UC_ARP002_BAABEL", "target": "UC_ARP005_DACAPO", "shared_viewers": 90, "jaccard": 0.1974, "overlap_coefficient": 0.3571, "weight": 90.0 },
    { "source": "UC_ARP002_BAABEL", "target": "UC_POLY001_HOKU", "shared_viewers": 59, "jaccard": 0.1513, "overlap_coefficient": 0.2995, "weight": 59.0 },
    { "source": "UC_ARP002_BAABEL", "target": "UC_PIX001_HINABE", "shared_viewers": 59, "jaccard": 0.1513, "overlap_coefficient": 0.2995, "weight": 59.0 },
    { "source": "UC_ARP002_BAABEL", "target": "UC_POLY002_LUCINE", "shared_viewers": 55, "jaccard": 0.1351, "overlap_coefficient": 0.2619, "weight": 55.0 },
    { "source": "UC_ARP002_BAABEL", "target": "UC_INDIE001_AISHA", "shared_viewers": 29, "jaccard": 0.0773, "overlap_coefficient": 0.1908, "weight": 29.0 },
    { "source": "UC_ARP003_MAYLYN", "target": "UC_ARP005_DACAPO", "shared_viewers": 144, "jaccard": 0.3445, "overlap_coefficient": 0.5373, "weight": 144.0 },
    { "source": "UC_ARP003_MAYLYN", "target": "UC_POLY002_LUCINE", "shared_viewers": 60, "jaccard": 0.1435, "overlap_coefficient": 0.2857, "weight": 60.0 },
    { "source": "UC_ARP003_MAYLYN", "target": "UC_POLY001_HOKU", "shared_viewers": 58, "jaccard": 0.1425, "overlap_coefficient": 0.2944, "weight": 58.0 },
    { "source": "UC_ARP003_MAYLYN", "target": "UC_PIX001_HINABE", "shared_viewers": 58, "jaccard": 0.1425, "overlap_coefficient": 0.2944, "weight": 58.0 },
    { "source": "UC_ARP003_MAYLYN", "target": "UC_INDIE001_AISHA", "shared_viewers": 30, "jaccard": 0.0769, "overlap_coefficient": 0.1974, "weight": 30.0 },
    { "source": "UC_ARP005_DACAPO", "target": "UC_POLY002_LUCINE", "shared_viewers": 123, "jaccard": 0.3228, "overlap_coefficient": 0.5857, "weight": 123.0 },
    { "source": "UC_ARP005_DACAPO", "target": "UC_PIX001_HINABE", "shared_viewers": 68, "jaccard": 0.1608, "overlap_coefficient": 0.3452, "weight": 68.0 },
    { "source": "UC_ARP005_DACAPO", "target": "UC_POLY001_HOKU", "shared_viewers": 68, "jaccard": 0.1608, "overlap_coefficient": 0.3452, "weight": 68.0 },
    { "source": "UC_ARP005_DACAPO", "target": "UC_INDIE001_AISHA", "shared_viewers": 38, "jaccard": 0.0931, "overlap_coefficient": 0.25, "weight": 38.0 },
    { "source": "UC_POLY001_HOKU", "target": "UC_PIX001_HINABE", "shared_viewers": 119, "jaccard": 0.4327, "overlap_coefficient": 0.6041, "weight": 119.0 },
    { "source": "UC_POLY001_HOKU", "target": "UC_POLY002_LUCINE", "shared_viewers": 48, "jaccard": 0.1337, "overlap_coefficient": 0.2437, "weight": 48.0 },
    { "source": "UC_POLY001_HOKU", "target": "UC_INDIE001_AISHA", "shared_viewers": 24, "jaccard": 0.0738, "overlap_coefficient": 0.1579, "weight": 24.0 },
    { "source": "UC_POLY002_LUCINE", "target": "UC_PIX001_HINABE", "shared_viewers": 48, "jaccard": 0.1337, "overlap_coefficient": 0.2437, "weight": 48.0 },
    { "source": "UC_POLY002_LUCINE", "target": "UC_INDIE001_AISHA", "shared_viewers": 21, "jaccard": 0.0616, "overlap_coefficient": 0.1382, "weight": 21.0 },
    { "source": "UC_PIX001_HINABE", "target": "UC_INDIE001_AISHA", "shared_viewers": 24, "jaccard": 0.0738, "overlap_coefficient": 0.1579, "weight": 24.0 }
  ]
};

// Agency Colors Mapping
const AGENCY_COLORS = {
  "Algorhythm Project": "#ec4899",
  "Polygon Official": "#06b6d4",
  "Pixela Project": "#10b981",
  "Independent": "#f59e0b",
  "Other": "#8b5cf6"
};

// State Variables
let rawData = null;
let graphNodes = [];
let graphEdges = [];
let nodeMap = new Map();

// Camera Transform
let panX = 0;
let panY = 0;
let zoom = 1.0;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;

// Interaction & Filters
let hoveredNode = null;
let selectedNode = null;
let draggedNode = null;
let spotlightBridges = false;
let currentMetric = "shared_viewers";
let minThreshold = 1;
let selectedAgency = "ALL";
let selectedTier = "ALL";
let searchQuery = "";

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
// Initialization & Data Loading
// ==========================================================
async function initApp() {
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  try {
    const res = await fetch("data.json");
    if (!res.ok) throw new Error("Could not fetch data.json");
    rawData = await res.json();
  } catch (err) {
    console.warn("Using embedded fallback dataset:", err);
    rawData = EMBEDDED_DATA;
  }

  setupEventListeners();
  processGraphData();
  updateKPIs();
  requestAnimationFrame(simulationLoop);
}

function resizeCanvas() {
  canvas.width = container.clientWidth * window.devicePixelRatio;
  canvas.height = container.clientHeight * window.devicePixelRatio;
  canvas.style.width = `${container.clientWidth}px`;
  canvas.style.height = `${container.clientHeight}px`;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
}

function processGraphData() {
  const width = container.clientWidth;
  const height = container.clientHeight;
  panX = width / 2;
  panY = height / 2;

  // Initialize node physics
  graphNodes = rawData.nodes.map((n, i) => {
    const angle = (i / rawData.nodes.length) * 2 * Math.PI;
    const radius = 180 + Math.random() * 120;
    const baseRadius = Math.max(10, Math.min(32, Math.sqrt(n.subscribers) / 28));

    return {
      ...n,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
      radius: baseRadius,
      color: AGENCY_COLORS[n.agency] || "#8b5cf6",
      visible: true
    };
  });

  nodeMap.clear();
  graphNodes.forEach(n => nodeMap.set(n.id, n));

  // Initialize edges
  graphEdges = rawData.edges.map(e => {
    return {
      ...e,
      sourceNode: nodeMap.get(e.source),
      targetNode: nodeMap.get(e.target),
      visible: true
    };
  }).filter(e => e.sourceNode && e.targetNode);

  applyFilters();
}

function updateKPIs() {
  statVtubers.textContent = rawData.metadata.total_vtubers;
  statEdges.textContent = rawData.metadata.total_connections;
  statCommunities.textContent = rawData.metadata.communities_count;

  // Top Bridge
  const sortedBridges = [...rawData.nodes].sort((a, b) => b.betweenness - a.betweenness);
  if (sortedBridges.length > 0 && sortedBridges[0].betweenness > 0) {
    statTopBridge.textContent = sortedBridges[0].label;
  } else {
    statTopBridge.textContent = "Schneider ARP";
  }
}

// ==========================================================
// Filtering Logic
// ==========================================================
function applyFilters() {
  let activeNodesCount = 0;

  graphNodes.forEach(n => {
    let matchAgency = (selectedAgency === "ALL" || n.agency === selectedAgency);
    let matchTier = (selectedTier === "ALL" || n.priority === selectedTier);
    let matchSearch = !searchQuery || 
      n.label.toLowerCase().includes(searchQuery) || 
      n.handle.toLowerCase().includes(searchQuery);

    n.visible = matchAgency && matchTier && matchSearch;
    if (n.visible) activeNodesCount++;
  });

  graphEdges.forEach(e => {
    const nodesVisible = e.sourceNode.visible && e.targetNode.visible;
    let weightVal = e[currentMetric];
    if (currentMetric === "shared_viewers") {
      e.visible = nodesVisible && (weightVal >= minThreshold);
    } else {
      // Jaccard or overlap coefficient (0.0 to 1.0, scale slider to 0-100%)
      e.visible = nodesVisible && (weightVal >= (minThreshold / 100));
    }
  });

  activeCount.textContent = `${activeNodesCount}/${graphNodes.length} Active`;
}

// ==========================================================
// Force-Directed Physics Simulation
// ==========================================================
let pulseTime = 0;

function simulationLoop() {
  pulseTime += 0.04;
  updatePhysics();
  renderCanvas();
  requestAnimationFrame(simulationLoop);
}

function updatePhysics() {
  const visibleNodes = graphNodes.filter(n => n.visible);
  const visibleEdges = graphEdges.filter(e => e.visible);

  // 1. Repulsion between visible nodes
  for (let i = 0; i < visibleNodes.length; i++) {
    const na = visibleNodes[i];
    for (let j = i + 1; j < visibleNodes.length; j++) {
      const nb = visibleNodes[j];
      const dx = nb.x - na.x;
      const dy = nb.y - na.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      
      if (dist < 400) {
        const force = 1800 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (na !== draggedNode) { na.vx -= fx; na.vy -= fy; }
        if (nb !== draggedNode) { nb.vx += fx; nb.vy += fy; }
      }
    }
  }

  // 2. Spring Attraction along Edges
  for (const edge of visibleEdges) {
    const na = edge.sourceNode;
    const nb = edge.targetNode;
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    // Desired distance inversely proportional to connection weight
    const desiredDist = Math.max(90, 260 - Math.min(180, edge.shared_viewers * 1.5));
    const delta = dist - desiredDist;
    const springForce = delta * 0.003;
    const fx = (dx / dist) * springForce;
    const fy = (dy / dist) * springForce;

    if (na !== draggedNode) { na.vx += fx; na.vy += fy; }
    if (nb !== draggedNode) { nb.vx -= fx; nb.vy -= fy; }
  }

  // 3. Center Gravity & Damping
  for (const node of visibleNodes) {
    if (node === draggedNode) continue;
    node.vx -= node.x * 0.001;
    node.vy -= node.y * 0.001;

    node.vx *= 0.88; // Damping
    node.vy *= 0.88;

    node.x += node.vx;
    node.y += node.vy;
  }
}

// ==========================================================
// Canvas Renderer
// ==========================================================
function renderCanvas() {
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
  if (hoveredNode) {
    neighborIds.add(hoveredNode.id);
    visibleEdges.forEach(e => {
      if (e.sourceNode.id === hoveredNode.id) neighborIds.add(e.targetNode.id);
      if (e.targetNode.id === hoveredNode.id) neighborIds.add(e.sourceNode.id);
    });
  }

  // 1. Draw Edges
  for (const edge of visibleEdges) {
    const isHovered = hoveredNode && (
      edge.sourceNode.id === hoveredNode.id || edge.targetNode.id === hoveredNode.id
    );
    const isDimmed = hoveredNode && !isHovered;

    let baseWidth = Math.max(1, Math.min(6, edge.shared_viewers / 25));
    let alpha = isHovered ? 0.9 : (isDimmed ? 0.08 : 0.35);

    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.lineWidth = isHovered ? baseWidth + 2 : baseWidth;
    ctx.strokeStyle = isHovered ? "#38bdf8" : `rgba(148, 163, 184, ${alpha})`;
    ctx.stroke();
  }

  // 2. Draw Nodes
  for (const node of visibleNodes) {
    const isHovered = (hoveredNode && hoveredNode.id === node.id);
    const isNeighbor = (hoveredNode && neighborIds.has(node.id));
    const isDimmed = hoveredNode && !isNeighbor;
    const isBridgeSpotlight = spotlightBridges && node.betweenness > 0.05;

    ctx.save();
    ctx.translate(node.x, node.y);

    // Glowing Outer Halo for Bridges
    if (isBridgeSpotlight) {
      const pulseSize = node.radius + 10 + Math.sin(pulseTime) * 4;
      ctx.beginPath();
      ctx.arc(0, 0, pulseSize, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(245, 158, 11, 0.7)";
      ctx.lineWidth = 2.5;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Node Glow Shadow
    ctx.shadowBlur = isHovered ? 24 : 10;
    ctx.shadowColor = node.color;

    // Node Base Circle
    ctx.beginPath();
    ctx.arc(0, 0, node.radius, 0, 2 * Math.PI);
    ctx.fillStyle = isDimmed ? "rgba(30, 41, 59, 0.4)" : node.color;
    ctx.fill();

    // Node Border
    ctx.lineWidth = isHovered ? 3 : 1.5;
    ctx.strokeStyle = isHovered ? "#ffffff" : "rgba(255, 255, 255, 0.6)";
    ctx.stroke();

    // Label
    ctx.shadowBlur = 0;
    ctx.font = `600 ${Math.max(10, Math.min(13, node.radius * 0.75))}px 'Outfit', sans-serif`;
    ctx.fillStyle = isDimmed ? "rgba(148, 163, 184, 0.3)" : "#f8fafc";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(node.label.split(" ")[0], 0, node.radius + 14);

    ctx.restore();
  }

  ctx.restore();
}

// ==========================================================
// Mouse / Touch Event Listeners
// ==========================================================
function setupEventListeners() {
  container.addEventListener("mousedown", onMouseDown);
  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
  container.addEventListener("wheel", onWheel, { passive: false });

  // Filter Event Listeners
  searchInput.addEventListener("input", e => {
    searchQuery = e.target.value.toLowerCase().trim();
    applyFilters();
  });

  agencyFilter.addEventListener("change", e => {
    selectedAgency = e.target.value;
    applyFilters();
  });

  tierFilter.addEventListener("change", e => {
    selectedTier = e.target.value;
    applyFilters();
  });

  metricSelect.addEventListener("change", e => {
    currentMetric = e.target.value;
    if (currentMetric === "shared_viewers") {
      thresholdSlider.max = 150;
      thresholdSlider.value = 1;
      sliderValue.textContent = "1";
    } else {
      thresholdSlider.max = 100;
      thresholdSlider.value = 5;
      sliderValue.textContent = "5%";
    }
    minThreshold = Number(thresholdSlider.value);
    applyFilters();
  });

  thresholdSlider.addEventListener("input", e => {
    minThreshold = Number(e.target.value);
    sliderValue.textContent = currentMetric === "shared_viewers" 
      ? minThreshold 
      : `${minThreshold}%`;
    applyFilters();
  });

  btnToggleBridges.addEventListener("click", () => {
    spotlightBridges = !spotlightBridges;
    btnToggleBridges.classList.toggle("active", spotlightBridges);
  });

  btnCloseInspector.addEventListener("click", () => {
    inspectorPanel.classList.remove("open");
    selectedNode = null;
  });

  btnInfoModal.addEventListener("click", () => infoModal.classList.add("open"));
  btnCloseModal.addEventListener("click", () => infoModal.classList.remove("open"));
  infoModal.addEventListener("click", e => {
    if (e.target === infoModal) infoModal.classList.remove("open");
  });
}

function getGraphCoordinates(e) {
  const rect = container.getBoundingClientRect();
  const screenX = e.clientX - rect.left;
  const screenY = e.clientY - rect.top;
  return {
    x: (screenX - panX) / zoom,
    y: (screenY - panY) / zoom
  };
}

function findNodeAt(x, y) {
  const visible = graphNodes.filter(n => n.visible);
  for (let i = visible.length - 1; i >= 0; i--) {
    const node = visible[i];
    const dx = node.x - x;
    const dy = node.y - y;
    if (dx * dx + dy * dy <= (node.radius + 6) * (node.radius + 6)) {
      return node;
    }
  }
  return null;
}

function onMouseDown(e) {
  const coords = getGraphCoordinates(e);
  const clicked = findNodeAt(coords.x, coords.y);

  if (clicked) {
    draggedNode = clicked;
    openInspector(clicked);
  } else {
    isPanning = true;
    startPanX = e.clientX - panX;
    startPanY = e.clientY - panY;
  }
}

function onMouseMove(e) {
  if (draggedNode) {
    const coords = getGraphCoordinates(e);
    draggedNode.x = coords.x;
    draggedNode.y = coords.y;
    draggedNode.vx = 0;
    draggedNode.vy = 0;
    return;
  }

  if (isPanning) {
    panX = e.clientX - startPanX;
    panY = e.clientY - startPanY;
    return;
  }

  const coords = getGraphCoordinates(e);
  const hovered = findNodeAt(coords.x, coords.y);
  hoveredNode = hovered;
  container.style.cursor = hovered ? "pointer" : (isPanning ? "grabbing" : "grab");
}

function onMouseUp() {
  draggedNode = null;
  isPanning = false;
}

function onWheel(e) {
  e.preventDefault();
  const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
  const newZoom = Math.max(0.3, Math.min(3.0, zoom * zoomFactor));

  const rect = container.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  panX = mouseX - (mouseX - panX) * (newZoom / zoom);
  panY = mouseY - (mouseY - panY) * (newZoom / zoom);
  zoom = newZoom;
}

// ==========================================================
// Inspector Card Details
// ==========================================================
function openInspector(node) {
  selectedNode = node;
  inspName.textContent = node.label;
  inspHandle.textContent = node.handle || `@${node.id}`;
  inspTier.textContent = `Tier ${node.priority}`;
  inspAgency.textContent = node.agency;
  inspSubs.textContent = `${node.subscribers.toLocaleString()} Subs`;

  inspDegree.textContent = node.degree.toFixed(3);
  inspBetweenness.textContent = node.betweenness.toFixed(4);
  inspPageRank.textContent = node.pagerank ? node.pagerank.toFixed(3) : "0.000";

  // Find all overlaps connected to this VTuber
  const connections = [];
  graphEdges.forEach(e => {
    if (e.sourceNode.id === node.id) {
      connections.push({ partner: e.targetNode, shared: e.shared_viewers, jaccard: e.jaccard });
    } else if (e.targetNode.id === node.id) {
      connections.push({ partner: e.sourceNode, shared: e.shared_viewers, jaccard: e.jaccard });
    }
  });

  connections.sort((a, b) => b.shared - a.shared);

  inspConnectionsList.innerHTML = "";
  if (connections.length === 0) {
    inspConnectionsList.innerHTML = `<div style="font-size:0.8rem; color: var(--text-muted);">No recorded stream overlap yet.</div>`;
  } else {
    const maxShared = connections[0].shared || 1;
    connections.slice(0, 6).forEach(c => {
      const pct = Math.min(100, Math.round((c.shared / maxShared) * 100));
      const item = document.createElement("div");
      item.className = "connection-item";
      item.innerHTML = `
        <div class="connection-head">
          <span class="connection-name">${c.partner.label}</span>
          <span class="connection-shared">${c.shared} Viewers (${(c.jaccard * 100).toFixed(1)}%)</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${pct}%"></div>
        </div>
      `;
      item.addEventListener("click", () => {
        openInspector(c.partner);
        // Center camera smoothly
        panX = container.clientWidth / 2 - c.partner.x * zoom;
        panY = container.clientHeight / 2 - c.partner.y * zoom;
      });
      inspConnectionsList.appendChild(item);
    });
  }

  inspectorPanel.classList.add("open");
}

// Start
window.addEventListener("DOMContentLoaded", initApp);
