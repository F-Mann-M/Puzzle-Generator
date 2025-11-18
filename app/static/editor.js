// ======================================================
// Puzzle Editor – Clean Working Version (Create-Only)
// ======================================================

// --- GET ELEMENTS ---
const svg = document.getElementById("editor-svg");

const addNodeBtn = document.getElementById("add-node-btn");
const addEdgeBtn = document.getElementById("add-edge-btn");
const placeUnitBtn = document.getElementById("place-unit-btn");
const editPathBtn = document.getElementById("edit-path-btn");
const exportBtn = document.getElementById("export-btn");

const factionSelect = document.getElementById("faction-select");
const unitTypeSelect = document.getElementById("unit-type-select");

const nodesField = document.getElementById("nodes-field");
const edgesField = document.getElementById("edges-field");
const unitsField = document.getElementById("units-field");
const editorForm = document.getElementById("editor-form");

// --- INTERNAL STATE ---
let nodes = [];
let edges = [];
let units = [];

let currentTool = null;

let nextNodeId = 0;
let nextEdgeId = 0;
let nextUnitId = 0;

let pendingEdgeStart = null;
let selectedUnit = null;

// ======================================================
// Utility
// ======================================================
function svgPoint(evt) {
    const p = svg.createSVGPoint();
    p.x = evt.clientX;
    p.y = evt.clientY;
    return p.matrixTransform(svg.getScreenCTM().inverse());
}

function getNode(id) {
    return nodes.find(n => n.id === id && !n.deleted);
}

function getUnit(id) {
    return units.find(u => u.id === id && !u.deleted);
}

function randomColor() {
    return "#" + Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, "0");
}

// ======================================================
// Tool selection
// ======================================================
function selectTool(tool) {
    currentTool = tool;
    pendingEdgeStart = null;
    selectedUnit = null;
}

addNodeBtn.onclick = () => selectTool("add-node");
addEdgeBtn.onclick = () => selectTool("add-edge");
placeUnitBtn.onclick = () => selectTool("place-unit");
editPathBtn.onclick = () => selectTool("edit-path");

// ======================================================
// Add Node
// ======================================================
svg.addEventListener("click", evt => {
    if (currentTool !== "add-node") return;

    const pt = svgPoint(evt);

    nodes.push({
        id: nextNodeId++,
        x: pt.x,
        y: pt.y,
        deleted: false
    });

    render();
});

// Right-click delete
function deleteNode(id) {
    const n = getNode(id);
    if (!n) return;

    n.deleted = true;

    // delete edges connected to node
    edges.forEach(e => {
        if (e.start === id || e.end === id) e.deleted = true;
    });

    // remove node from all unit paths
    units.forEach(u => {
        u.path = u.path.filter(pid => pid !== id);
    });

    render();
}

// ======================================================
// Dragging nodes
// ======================================================
let dragging = false;
let draggingNodeId = null;
let potentialDrag = false;
let dragStartX = null;
let dragStartY = null;
let didDrag = false; // Track if we actually dragged (moved beyond threshold)
const DRAG_THRESHOLD = 5; // pixels

svg.addEventListener("mousedown", evt => {
    const pt = svgPoint(evt);
    didDrag = false; // Reset drag flag on new mousedown

    for (const n of nodes) {
        if (n.deleted) continue;
        const dx = n.x - pt.x;
        const dy = n.y - pt.y;

        if (dx * dx + dy * dy < 20 * 20) {
            potentialDrag = true;
            draggingNodeId = n.id;
            dragStartX = evt.clientX;
            dragStartY = evt.clientY;
            return;
        }
    }
});

svg.addEventListener("mousemove", evt => {
    if (potentialDrag && !dragging) {
        // Check if mouse has moved beyond threshold
        const dx = evt.clientX - dragStartX;
        const dy = evt.clientY - dragStartY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > DRAG_THRESHOLD) {
            // Start actual dragging
            dragging = true;
            didDrag = true;
            potentialDrag = false;
        } else {
            // Still within threshold, don't start dragging yet
            return;
        }
    }
    
    if (!dragging) return;
    const n = getNode(draggingNodeId);
    if (!n) return;

    const pt = svgPoint(evt);
    n.x = pt.x;
    n.y = pt.y;

    render();
});

document.addEventListener("mouseup", () => {
    dragging = false;
    potentialDrag = false;
    draggingNodeId = null;
    dragStartX = null;
    dragStartY = null;
});

// ======================================================
// Edges
// ======================================================
svg.addEventListener("click", evt => {
    if (currentTool !== "add-edge") return;
    if (didDrag) return; // Don't process click if we dragged

    const pt = svgPoint(evt);

    let clickedNode = null;
    for (const n of nodes) {
        if (n.deleted) continue;

        const dx = n.x - pt.x;
        const dy = n.y - pt.y;

        if (dx * dx + dy * dy < 20 * 20) {
            clickedNode = n.id;
            break;
        }
    }

    if (clickedNode === null) return;

    // First click = start node
    if (pendingEdgeStart === null) {
        pendingEdgeStart = clickedNode;
    } else {
        // Second click = end node
        if (pendingEdgeStart !== clickedNode) {

            edges.push({
                id: nextEdgeId++,
                start: pendingEdgeStart,
                end: clickedNode,
                deleted: false
            });
        }
        pendingEdgeStart = null;
        render();
    }
});

// Delete edge
function deleteEdge(id) {
    let e = edges.find(e => e.id === id);
    if (!e) return;
    e.deleted = true;
    render();
}

// ======================================================
// Unit Initialization
// ======================================================
function loadUnitTypes() {
    const faction = factionSelect.value;

    unitTypeSelect.innerHTML = "";
    const options = faction === "enemy"
        ? ["Grunt", "Brute"]
        : ["Swordman", "Nun", "Archer"];

    for (const type of options) {
        const opt = document.createElement("option");
        opt.value = type;
        opt.textContent = type;
        unitTypeSelect.appendChild(opt);
    }
}

factionSelect.addEventListener("change", loadUnitTypes);
loadUnitTypes();

// ======================================================
// Place Unit
// ======================================================
svg.addEventListener("click", evt => {
    if (currentTool !== "place-unit") return;
    if (didDrag) return; // Don't process click if we dragged

    const pt = svgPoint(evt);

    for (const n of nodes) {
        if (n.deleted) continue;

        const dx = n.x - pt.x;
        const dy = n.y - pt.y;

        if (dx * dx + dy * dy < 20 * 20) {

            units.push({
                id: nextUnitId++,
                faction: factionSelect.value,
                type: unitTypeSelect.value,
                path: [n.id],
                color: randomColor(),
                deleted: false
            });

            render();
            return;
        }
    }
});

// Delete unit
function deleteUnit(id) {
    const u = getUnit(id);
    if (!u) return;

    u.deleted = true;
    render();
}

function appendNodeToSelectedPath(nodeId) {
    if (selectedUnit == null) return;
    const unit = getUnit(selectedUnit);
    if (!unit) return;
    unit.path.push(nodeId);
    render();
}

// ======================================================
// Edit Paths
// ======================================================
svg.addEventListener("click", evt => {
    if (currentTool !== "edit-path") return;
    if (selectedUnit == null) return;
    if (didDrag) return; // Don't process click if we dragged

    const pt = svgPoint(evt);

    for (const n of nodes) {
        if (n.deleted) continue;

        const dx = n.x - pt.x;
        const dy = n.y - pt.y;

        if (dx * dx + dy * dy < 20 * 20) {
            appendNodeToSelectedPath(n.id);
            return;
        }
    }
});

// ======================================================
// Render SVG
// ======================================================
function render() {
    svg.innerHTML = "";

    // --- Draw edges ---
    edges.filter(e => !e.deleted).forEach(e => {
        const a = getNode(e.start);
        const b = getNode(e.end);
        if (!a || !b) return;

        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", a.x);
        line.setAttribute("y1", a.y);
        line.setAttribute("x2", b.x);
        line.setAttribute("y2", b.y);
        line.setAttribute("stroke", "#666");
        line.setAttribute("stroke-width", 4);

        line.addEventListener("contextmenu", evt => {
            evt.preventDefault();
            deleteEdge(e.id);
        });

        svg.appendChild(line);
    });

    // --- Unit Paths (draw BEFORE units so unit circle is on top) ---
    // Group edges (node pairs) by which units use them
    const edgeGroups = new Map(); // key: "nodeId1,nodeId2", value: array of {unit, edgeIndex}
    
    // First pass: collect all edges from all units
    units.filter(u => !u.deleted).forEach(u => {
        const pts = u.path.map(pid => getNode(pid)).filter(Boolean);
        
        for (let i = 0; i < pts.length - 1; i++) {
            const nodeA = pts[i];
            const nodeB = pts[i + 1];
            
            // Create normalized edge key (always smaller ID first)
            const edgeKey = nodeA.id < nodeB.id 
                ? `${nodeA.id},${nodeB.id}` 
                : `${nodeB.id},${nodeA.id}`;
            
            if (!edgeGroups.has(edgeKey)) {
                edgeGroups.set(edgeKey, []);
            }
            edgeGroups.get(edgeKey).push({ unit: u, nodeA, nodeB, edgeIndex: i });
        }
    });

    // Second pass: render paths with offsets for shared edges
    units.filter(u => !u.deleted).forEach(u => {
        const pts = u.path.map(pid => getNode(pid)).filter(Boolean);

        for (let i = 0; i < pts.length - 1; i++) {
            const nodeA = pts[i];
            const nodeB = pts[i + 1];
            
            // Create normalized edge key
            const edgeKey = nodeA.id < nodeB.id 
                ? `${nodeA.id},${nodeB.id}` 
                : `${nodeB.id},${nodeA.id}`;
            
            // Find all units using this edge
            const edgeUsers = edgeGroups.get(edgeKey) || [];
            const totalSharing = edgeUsers.length;
            
            // Find this unit's position in the group
            const unitIndex = edgeUsers.findIndex(eu => eu.unit.id === u.id);
            
            // Calculate offset: alternate sides with increasing distance
            // Unit 0: -5px, Unit 1: +5px, Unit 2: -10px, Unit 3: +10px, etc.
            let offsetDistance = 0;
            if (totalSharing > 1 && unitIndex >= 0) {
                const side = (unitIndex % 2 === 0) ? -1 : 1;  // Alternate: negative for even, positive for odd
                const layer = Math.floor(unitIndex / 2) + 1;  // Layer: 1, 1, 2, 2, 3, 3, ...
                offsetDistance = side * layer * 5;  // 5px per layer
            }

            // Ensure consistent direction for perpendicular calculation
            // Always use smaller node ID -> larger node ID direction
            let x1, y1, x2, y2;
            if (nodeA.id < nodeB.id) {
                x1 = nodeA.x;
                y1 = nodeA.y;
                x2 = nodeB.x;
                y2 = nodeB.y;
            } else {
                // Reverse direction to maintain consistency
                x1 = nodeB.x;
                y1 = nodeB.y;
                x2 = nodeA.x;
                y2 = nodeA.y;
            }

            // Apply perpendicular offset if needed
            if (offsetDistance !== 0) {
                const dx = x2 - x1;
                const dy = y2 - y1;
                const length = Math.sqrt(dx * dx + dy * dy);
                
                if (length > 0) {
                    // Perpendicular vector (normalized) - always use same direction
                    // Use consistent direction: rotate 90° counterclockwise
                    const perpX = -dy / length;
                    const perpY = dx / length;
                    // Apply offset
                    x1 += perpX * offsetDistance;
                    y1 += perpY * offsetDistance;
                    x2 += perpX * offsetDistance;
                    y2 += perpY * offsetDistance;
                }
            }

            const pathLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
            pathLine.setAttribute("x1", x1);
            pathLine.setAttribute("y1", y1);
            pathLine.setAttribute("x2", x2);
            pathLine.setAttribute("y2", y2);
            pathLine.setAttribute("stroke", u.color);
            pathLine.setAttribute("stroke-width", 4);

            svg.appendChild(pathLine);
        }
    });

    // --- Draw nodes ---
    nodes.filter(n => !n.deleted).forEach(n => {
        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("cx", n.x);
        c.setAttribute("cy", n.y);
        c.setAttribute("r", 20);
        c.setAttribute("fill", "white");
        c.setAttribute("stroke", "black");
        c.setAttribute("stroke-width", 3);

        // Click on node to add to path when in edit-path mode
        c.addEventListener("click", evt => {
            if (currentTool === "edit-path" && selectedUnit != null) {
                evt.stopPropagation();
                appendNodeToSelectedPath(n.id);
                return;
            }
        });

        // Right click = delete
        c.addEventListener("contextmenu", evt => {
            evt.preventDefault();
            deleteNode(n.id);
        });

        svg.appendChild(c);
    });

    // --- Draw Units ---
    units.filter(u => !u.deleted).forEach(u => {
        const start = getNode(u.path[0]);
        if (!start) return;

        const unitCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        unitCircle.setAttribute("cx", start.x);
        unitCircle.setAttribute("cy", start.y);
        unitCircle.setAttribute("r", 14);
        unitCircle.setAttribute("fill", u.color);
        unitCircle.setAttribute("stroke", "#000");
        unitCircle.setAttribute("stroke-width", 2);

        // Add yellow highlight circle around selected unit in edit-path mode
        if (currentTool === "edit-path" && selectedUnit === u.id) {
            const highlightCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            highlightCircle.setAttribute("cx", start.x);
            highlightCircle.setAttribute("cy", start.y);
            highlightCircle.setAttribute("r", 18);
            highlightCircle.setAttribute("fill", "none");
            highlightCircle.setAttribute("stroke", "yellow");
            highlightCircle.setAttribute("stroke-width", 3);
            highlightCircle.setAttribute("opacity", "0.8");
            svg.appendChild(highlightCircle);
        }

        // Select for editing path
        unitCircle.addEventListener("click", evt => {
            if (currentTool === "edit-path" && selectedUnit != null) {
                evt.stopPropagation();
                if (selectedUnit === u.id) {
                    // If clicking on the selected unit's circle, add the starting node to complete a circle
                    appendNodeToSelectedPath(u.path[0]);
                } else {
                    // If clicking on a different unit's circle, add that unit's starting node
                    appendNodeToSelectedPath(u.path[0]);
                }
                return;
            }

            evt.stopPropagation();
            selectedUnit = u.id;
            render();
        });

        // Right click delete
        unitCircle.addEventListener("contextmenu", evt => {
            evt.preventDefault();
            deleteUnit(u.id);
        });

        svg.appendChild(unitCircle);
    });

    // --- Draw path index labels (render last so they appear on top) ---
    if (currentTool === "edit-path" && selectedUnit != null) {
        const selectedUnitObj = getUnit(selectedUnit);
        if (selectedUnitObj) {
            // Collect all path indices for each node
            const nodeIndices = new Map();
            selectedUnitObj.path.forEach((nodeId, pathIndex) => {
                if (!nodeIndices.has(nodeId)) {
                    nodeIndices.set(nodeId, []);
                }
                nodeIndices.get(nodeId).push(pathIndex);
            });

            // Render one label per node showing all its indices
            nodeIndices.forEach((indices, nodeId) => {
                const node = getNode(nodeId);
                if (node) {
                    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    text.setAttribute("x", node.x);
                    text.setAttribute("y", node.y);
                    text.setAttribute("text-anchor", "middle");
                    text.setAttribute("dominant-baseline", "central");
                    text.setAttribute("font-size", "12");
                    text.setAttribute("font-weight", "bold");
                    text.setAttribute("fill", "black");
                    text.textContent = indices.join(", ");
                    svg.appendChild(text);
                }
            });
        }
    }
}

// ======================================================
// Submit PuzzleCreate JSON to FastAPI
// ======================================================

async function exportPuzzle(evt) {
    evt?.preventDefault();

    const formData = new FormData(editorForm);
    const name = (formData.get("name") || "").toString().trim();
    const game_mode = formData.get("game_mode") || "";
    const coins = Number(formData.get("coins") || 0);
    const description = (formData.get("description") || "").toString().trim();

    if (!name || !game_mode) {
        alert("Name and Game Mode are required!");
        return;
    }

    const payload = {
        name,
        model: "Created Manually",
        game_mode,
        coins,
        description,
        nodes: nodes.filter(n => !n.deleted).map(n => ({
            index: n.id,
            x: n.x,
            y: n.y
        })),
        edges: edges.filter(e => !e.deleted).map(e => ({
            index: e.id,
            start: e.start,
            end: e.end
        })),
        units: units.filter(u => !u.deleted).map(u => ({
            type: u.type,
            faction: u.faction,
            path: u.path
        }))
    };

    console.log("Sending PuzzleCreate payload:", payload);

    try {
        const response = await fetch("/puzzles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.redirected) {
            window.location.href = response.url;
        } else {
            const err = await response.text();
            alert("Server error:\n" + err);
        }
    } catch (err) {
        alert("Request failed: " + err);
    }
}

exportBtn.addEventListener("click", exportPuzzle);

