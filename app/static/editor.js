// ======================================================
// Puzzle Editor – Create and Update Version
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

// Zoom state
let currentViewBox = { x: 0, y: 0, width: 1000, height: 1000 };
let zoomLevel = 1.0;

// Pan state
let panning = false;
let panStartX = null;
let panStartY = null;
let panStartViewBoxX = null;
let panStartViewBoxY = null;

// --- EDIT MODE DETECTION ---
let isEditMode = false;
let puzzleId = null;

// ======================================================
// Utility
// ======================================================
function svgPoint(evt) {
    const p = svg.createSVGPoint();
    p.x = evt.clientX;
    p.y = evt.clientY;
    return p.matrixTransform(svg.getScreenCTM().inverse());
}

// Update SVG viewBox from currentViewBox
function updateViewBox() {
    if (!svg) return;
    svg.setAttribute("viewBox", `${currentViewBox.x} ${currentViewBox.y} ${currentViewBox.width} ${currentViewBox.height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
}

// Convert screen coordinates to SVG coordinates
function screenToSVG(svgElement, screenX, screenY) {
    const pt = svgElement.createSVGPoint();
    pt.x = screenX;
    pt.y = screenY;
    return pt.matrixTransform(svgElement.getScreenCTM().inverse());
}

// Handle mousewheel zoom
function setupZoom() {
    if (!svg) return;
    
    svg.addEventListener("wheel", (evt) => {
        evt.preventDefault();
        
        // Convert mouse position to SVG coordinates
        const svgPoint = screenToSVG(svg, evt.clientX, evt.clientY);
        
        // Determine zoom factor (positive deltaY = scroll down = zoom out, negative = zoom in)
        const zoomFactor = evt.deltaY > 0 ? 1.1 : 0.9;
        const minZoom = 0.1;
        const maxZoom = 10.0;
        
        // Calculate new zoom level
        const newZoom = zoomLevel * zoomFactor;
        if (newZoom < minZoom || newZoom > maxZoom) return;
        
        // Calculate the ratio of the mouse point within the current viewBox
        const ratioX = (svgPoint.x - currentViewBox.x) / currentViewBox.width;
        const ratioY = (svgPoint.y - currentViewBox.y) / currentViewBox.height;
        
        // Calculate new viewBox dimensions
        const newWidth = currentViewBox.width / zoomFactor;
        const newHeight = currentViewBox.height / zoomFactor;
        
        // Adjust viewBox origin to keep the point under cursor fixed
        const newX = svgPoint.x - ratioX * newWidth;
        const newY = svgPoint.y - ratioY * newHeight;
        
        // Update state
        zoomLevel = newZoom;
        currentViewBox = {
            x: newX,
            y: newY,
            width: newWidth,
            height: newHeight
        };
        
        updateViewBox();
    });
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

    // Check for right-click pan (button 2 = right mouse button)
    if (evt.button === 2) {
        // Check if clicking on a node - if so, don't pan (let context menu work)
        for (const n of nodes) {
            if (n.deleted) continue;
            const dx = n.x - pt.x;
            const dy = n.y - pt.y;
            if (dx * dx + dy * dy < 20 * 20) {
                // Clicked on a node, don't start panning
                return;
            }
        }
        
        // Right-click in empty area - start panning
        panning = true;
        panStartX = evt.clientX;
        panStartY = evt.clientY;
        panStartViewBoxX = currentViewBox.x;
        panStartViewBoxY = currentViewBox.y;
        evt.preventDefault(); // Prevent context menu
        return;
    }

    // Left-click node dragging
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
    // Handle panning (right-click drag)
    if (panning) {
        const dx = evt.clientX - panStartX;
        const dy = evt.clientY - panStartY;
        
        // Convert screen pixel movement to SVG coordinate movement
        // Calculate scale based on viewBox dimensions vs SVG element size
        const svgRect = svg.getBoundingClientRect();
        const scaleX = currentViewBox.width / svgRect.width;
        const scaleY = currentViewBox.height / svgRect.height;
        
        // Calculate pan offset in SVG coordinates
        // Negative because dragging right should move viewBox left (content appears to move right)
        const panOffsetX = -dx * scaleX;
        const panOffsetY = -dy * scaleY;
        
        // Update viewBox
        currentViewBox.x = panStartViewBoxX + panOffsetX;
        currentViewBox.y = panStartViewBoxY + panOffsetY;
        
        updateViewBox();
        return;
    }
    
    // Handle node dragging
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

document.addEventListener("mouseup", (evt) => {
    // Stop panning on right mouse button release
    if (evt.button === 2) {
        panning = false;
        panStartX = null;
        panStartY = null;
        panStartViewBoxX = null;
        panStartViewBoxY = null;
    }
    
    // Stop node dragging
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
        : ["Swordsman", "Nun", "Archer"];

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
    
    // Update viewBox to fit all nodes if we have any (only on first render or if nodes are outside)
    const activeNodes = nodes.filter(n => !n.deleted);
    if (activeNodes.length > 0) {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        activeNodes.forEach(n => {
            minX = Math.min(minX, n.x);
            minY = Math.min(minY, n.y);
            maxX = Math.max(maxX, n.x);
            maxY = Math.max(maxY, n.y);
        });
        
        // Add padding
        const padding = 100;
        minX -= padding;
        minY -= padding;
        maxX += padding;
        maxY += padding;
        
        // Only update viewBox if it hasn't been set yet (initial state) or if nodes are outside current viewBox
        const nodesOutside = minX < currentViewBox.x || minY < currentViewBox.y || 
            maxX > currentViewBox.x + currentViewBox.width || maxY > currentViewBox.y + currentViewBox.height;
        
        if (currentViewBox.width === 1000 && currentViewBox.height === 1000 && currentViewBox.x === 0 && currentViewBox.y === 0) {
            // Initial state - set viewBox to fit nodes
            currentViewBox = { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
            zoomLevel = 1.0;
            updateViewBox();
        } else if (nodesOutside && zoomLevel === 1.0) {
            // Nodes are outside and we're at default zoom - expand viewBox
            const newMinX = Math.min(currentViewBox.x, minX);
            const newMinY = Math.min(currentViewBox.y, minY);
            const newMaxX = Math.max(currentViewBox.x + currentViewBox.width, maxX);
            const newMaxY = Math.max(currentViewBox.y + currentViewBox.height, maxY);
            currentViewBox = { x: newMinX, y: newMinY, width: newMaxX - newMinX, height: newMaxY - newMinY };
            updateViewBox();
        }
    } else {
        // No nodes - ensure viewBox is set
        updateViewBox();
    }

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

        // Create tooltip group
        const tooltipGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        tooltipGroup.setAttribute("class", "node-tooltip");
        tooltipGroup.style.display = "none";
        tooltipGroup.style.pointerEvents = "none";

        // Tooltip background rectangle
        const tooltipRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        tooltipRect.setAttribute("fill", "white");
        tooltipRect.setAttribute("stroke", "black");
        tooltipRect.setAttribute("stroke-width", "1");
        tooltipRect.setAttribute("rx", "3");
        tooltipRect.setAttribute("ry", "3");

        // Find units placed on this node (units that start here)
        const unitsOnNode = units.filter(u => !u.deleted && u.path.length > 0 && u.path[0] === n.id);
        const unitTypes = unitsOnNode.map(u => `${u.faction} ${u.type || 'Unit'}`).join(', ');

        // Tooltip text
        const tooltipText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        tooltipText.setAttribute("font-size", "11");
        tooltipText.setAttribute("fill", "black");
        tooltipText.setAttribute("font-family", "monospace");
        
        let textContent = `Node: ${n.id}\nX: ${Math.round(n.x)}\nY: ${Math.round(n.y)}`;
        if (unitTypes) {
            textContent += `\nUnits: ${unitTypes}`;
        }
        const lines = textContent.split('\n');
        
        // Calculate tooltip size and position first
        const textWidth = Math.max(120, lines.reduce((max, line) => Math.max(max, line.length * 6), 0));
        const textHeight = lines.length * 14;
        const padding = 6;
        const offsetLeft = 25; // Distance from node center to tooltip
        
        // Rectangle position (to the left of node)
        const rectX = -textWidth - padding * 2 - offsetLeft;
        const rectY = -textHeight / 2 - padding;
        
        tooltipRect.setAttribute("width", textWidth + padding * 2);
        tooltipRect.setAttribute("height", textHeight + padding * 2);
        tooltipRect.setAttribute("x", rectX);
        tooltipRect.setAttribute("y", rectY);

        // Text position (inside rectangle, with padding)
        const textX = rectX + padding;
        const textY = rectY + padding + 11; // 11 is half font size for baseline
        
        tooltipText.setAttribute("x", textX);
        tooltipText.setAttribute("y", textY);
        tooltipText.setAttribute("text-anchor", "start");
        
        // Create tspan elements with correct positioning
        lines.forEach((line, i) => {
            const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
            tspan.setAttribute("x", textX);
            tspan.setAttribute("dy", i === 0 ? "0" : "14");
            tspan.textContent = line;
            tooltipText.appendChild(tspan);
        });

        tooltipGroup.appendChild(tooltipRect);
        tooltipGroup.appendChild(tooltipText);
        tooltipGroup.setAttribute("transform", `translate(${n.x}, ${n.y})`);

        // Mouseover/mouseout handlers
        c.addEventListener("mouseenter", () => {
            tooltipGroup.style.display = "block";
        });
        c.addEventListener("mouseleave", () => {
            tooltipGroup.style.display = "none";
        });

        // Click on node to add to path when in edit-path mode
        c.addEventListener("click", evt => {
            if (currentTool === "edit-path" && selectedUnit != null) {
                evt.stopPropagation();
                appendNodeToSelectedPath(n.id);
                return;
            }
        });

        // Right click = delete (only if not panning)
        c.addEventListener("contextmenu", evt => {
            if (!panning) {
                evt.preventDefault();
                deleteNode(n.id);
            }
        });

        svg.appendChild(c);
        svg.appendChild(tooltipGroup);
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
        const method = isEditMode ? "PUT" : "POST";
        const url = isEditMode ? `/puzzles/${puzzleId}` : "/puzzles";
        
        const response = await fetch(url, {
            method: method,
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

// ======================================================
// Initialize Editor (Load existing puzzle if in edit mode)
// ======================================================
document.addEventListener("DOMContentLoaded", async () => {
    // Setup zoom functionality
    setupZoom();
    
    // Prevent context menu on SVG when right-clicking in empty area (for panning)
    if (svg) {
        svg.addEventListener("contextmenu", (evt) => {
            // Only prevent if we're not clicking on a node (nodes handle their own context menu)
            const pt = svgPoint(evt);
            let clickedOnNode = false;
            for (const n of nodes) {
                if (n.deleted) continue;
                const dx = n.x - pt.x;
                const dy = n.y - pt.y;
                if (dx * dx + dy * dy < 20 * 20) {
                    clickedOnNode = true;
                    break;
                }
            }
            // If not clicking on a node, prevent context menu to allow panning
            if (!clickedOnNode) {
                evt.preventDefault();
            }
        });
    }
    
    // Set initial viewBox
    updateViewBox();
    
    // Check for edit mode via data-puzzle-id attribute
    const puzzleIdAttr = svg?.getAttribute("data-puzzle-id");
    if (puzzleIdAttr) {
        isEditMode = true;
        puzzleId = puzzleIdAttr;
        
        // Update button text
        if (exportBtn) {
            exportBtn.textContent = "Update Puzzle";
        }
        
        // Load existing puzzle data
        await loadPuzzleData(puzzleId);
    }
});

// ======================================================
// Load Puzzle Data for Editing
// ======================================================
async function loadPuzzleData(puzzleId) {
    try {
        const response = await fetch(`/puzzles/${puzzleId}/data`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const puzzleData = await response.json();
        
        // Clear existing data
        nodes = [];
        edges = [];
        units = [];
        
        // Find max indices to set nextNodeId, nextEdgeId, nextUnitId
        let maxNodeIndex = -1;
        let maxEdgeIndex = -1;
        
        // Load nodes
        puzzleData.nodes.forEach(node => {
            nodes.push({
                id: node.node_index,
                x: node.x_position,
                y: node.y_position,
                deleted: false
            });
            maxNodeIndex = Math.max(maxNodeIndex, node.node_index);
        });
        
        // Create a map from node UUID to node_index for edge loading
        const nodeIdToIndexMap = {};
        puzzleData.nodes.forEach(node => {
            nodeIdToIndexMap[node.id] = node.node_index;
        });
        
        // Load edges
        puzzleData.edges.forEach(edge => {
            const startNodeIndex = nodeIdToIndexMap[edge.start_node_id];
            const endNodeIndex = nodeIdToIndexMap[edge.end_node_id];
            
            if (startNodeIndex !== undefined && endNodeIndex !== undefined) {
                edges.push({
                    id: edge.edge_index,
                    start: startNodeIndex,
                    end: endNodeIndex,
                    deleted: false
                });
                maxEdgeIndex = Math.max(maxEdgeIndex, edge.edge_index);
            }
        });
        
        // Load units
        let unitCounter = 0;
        puzzleData.units.forEach(unit => {
            // Extract path as array of node indices
            const path = [];
            if (unit.path && unit.path.path_node) {
                const sortedPathNodes = [...unit.path.path_node].sort((a, b) => a.order_index - b.order_index);
                sortedPathNodes.forEach(pathNode => {
                    // Use the nodeIdToIndexMap to get node_index
                    const nodeIndex = nodeIdToIndexMap[pathNode.node_id];
                    if (nodeIndex !== undefined) {
                        path.push(nodeIndex);
                    }
                });
            }
            
            units.push({
                id: unitCounter++,
                faction: unit.faction,
                type: unit.unit_type,
                path: path,
                color: randomColor(),
                deleted: false
            });
        });
        
        // Set next IDs to be higher than existing ones
        nextNodeId = maxNodeIndex + 1;
        nextEdgeId = maxEdgeIndex + 1;
        nextUnitId = unitCounter;
        
        // Pre-fill form fields
        if (editorForm) {
            const nameField = document.getElementById("name");
            const gameModeField = document.getElementById("game_mode");
            const coinsField = document.getElementById("coins");
            const descriptionField = document.getElementById("description");
            
            // Get puzzle metadata from the page (passed via template)
            const puzzleName = document.querySelector('[data-puzzle-name]')?.getAttribute('data-puzzle-name');
            const puzzleGameMode = document.querySelector('[data-puzzle-game-mode]')?.getAttribute('data-puzzle-game-mode');
            const puzzleCoins = document.querySelector('[data-puzzle-coins]')?.getAttribute('data-puzzle-coins');
            const puzzleDescription = document.querySelector('[data-puzzle-description]')?.getAttribute('data-puzzle-description');
            
            if (nameField && puzzleName) nameField.value = puzzleName;
            if (gameModeField && puzzleGameMode) gameModeField.value = puzzleGameMode;
            if (coinsField && puzzleCoins) coinsField.value = puzzleCoins;
            if (descriptionField && puzzleDescription) descriptionField.value = puzzleDescription;
        }
        
        // Reset zoom and viewBox to fit loaded puzzle
        zoomLevel = 1.0;
        currentViewBox = { x: 0, y: 0, width: 1000, height: 1000 }; // Reset to trigger auto-fit in render()
        
        // Render the loaded puzzle
        render();
    } catch (err) {
        console.error("Error loading puzzle data:", err);
        alert("Failed to load puzzle data: " + err.message);
    }
}

