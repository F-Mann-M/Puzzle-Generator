// ======================================================
// Puzzle Editor – Complete Updated Version with Playback
// ======================================================

// --- 1. GLOBAL VARIABLES (Use 'let' to allow re-binding) ---
let svg = document.getElementById("editor-svg");
let addNodeBtn = document.getElementById("add-node-btn");
let addEdgeBtn = document.getElementById("add-edge-btn");
let placeUnitBtn = document.getElementById("place-unit-btn");
let editPathBtn = document.getElementById("edit-path-btn");
let exportBtn = document.getElementById("export-btn");
let factionSelect = document.getElementById("faction-select");
let unitTypeSelect = document.getElementById("unit-type-select");
let editorForm = document.getElementById("editor-form");

// Playback Controls
let prevTurnBtn = document.getElementById("prev-turn-btn");
let nextTurnBtn = document.getElementById("next-turn-btn");
let turnStatus = document.getElementById("turn-status");

// Internal state
let nodes = [];
let edges = [];
let units = [];
let currentTool = null;
let isEditMode = false;
let puzzleId = null;

// NEW: Playback State
let currentTurn = 0;

let nextNodeId = 0;
let nextEdgeId = 0;
let nextUnitId = 0;

let pendingEdgeStart = null;
let selectedUnit = null;

// Zoom/Pan state
let currentViewBox = { x: 0, y: 0, width: 1000, height: 1000 };
let zoomLevel = 1.0;
let panning = false;
let panStartX = null, panStartY = null;
let panStartViewBoxX = null, panStartViewBoxY = null;

// Dragging state
let dragging = false;
let draggingNodeId = null;
let potentialDrag = false;
let dragStartX = null;
let dragStartY = null;
let didDrag = false;
const DRAG_THRESHOLD = 5;

// --- 2. INITIALIZATION LOOPS ---

// A. Full Page Load
document.addEventListener("DOMContentLoaded", initEditor);

// B. HTMX Partial Load
document.body.addEventListener("htmx:afterSwap", (event) => {
    const target = event.detail.target;
    // Only re-init if the editor container or svg was updated
    if (target.id === "editor-integration-container" || target.querySelector("#editor-svg")) {
        initEditor();
    }
});

// --- 3. MAIN INIT FUNCTION ---
async function initEditor() {
    // Re-bind variables to the current DOM
    svg = document.getElementById("editor-svg");
    addNodeBtn = document.getElementById("add-node-btn");
    addEdgeBtn = document.getElementById("add-edge-btn");
    placeUnitBtn = document.getElementById("place-unit-btn");
    editPathBtn = document.getElementById("edit-path-btn");
    exportBtn = document.getElementById("export-btn");
    factionSelect = document.getElementById("faction-select");
    unitTypeSelect = document.getElementById("unit-type-select");
    editorForm = document.getElementById("editor-form");

    // NEW: Re-bind Playback Controls
    prevTurnBtn = document.getElementById("prev-turn-btn");
    nextTurnBtn = document.getElementById("next-turn-btn");
    turnStatus = document.getElementById("turn-status");

    if (!svg) return; // Exit if no editor found

    // Clear Data Arrays
    nodes = [];
    edges = [];
    units = [];
    nextNodeId = 0;
    nextEdgeId = 0;
    nextUnitId = 0;

    // Reset UI state
    currentTool = null;
    pendingEdgeStart = null;
    selectedUnit = null;
    isEditMode = false;
    puzzleId = null;
    currentTurn = 0; // Reset turn

    // Setup Toolbar Listeners
    if (addNodeBtn) addNodeBtn.onclick = () => { selectTool("add-node"); };
    if (addEdgeBtn) addEdgeBtn.onclick = () => { selectTool("add-edge"); };
    if (placeUnitBtn) placeUnitBtn.onclick = () => { selectTool("place-unit"); };
    if (editPathBtn) editPathBtn.onclick = () => { selectTool("edit-path"); };

    // NEW: Setup Playback Listeners
    if (prevTurnBtn) prevTurnBtn.onclick = () => { changeTurn(-1); };
    if (nextTurnBtn) nextTurnBtn.onclick = () => { changeTurn(1); };
    updateTurnStatus(); // Initialize text

    if (exportBtn) {
        // Prevent duplicate listeners
        exportBtn.replaceWith(exportBtn.cloneNode(true));
        exportBtn = document.getElementById("export-btn");
        exportBtn.addEventListener("click", exportPuzzle);
    }

    if (factionSelect) {
        factionSelect.onchange = loadUnitTypes;
        loadUnitTypes();
    }

    // Setup Canvas Interactions (Click, Drag, Pan, Zoom)
    setupInteractions();
    setupZoom();

    // Check for Edit Mode (Data Loading)
    const newPuzzleId = svg.getAttribute("data-puzzle-id");

    // Validate ID is not empty or "None" (string from Jinja)
    if (newPuzzleId && newPuzzleId !== "None" && newPuzzleId.trim() !== "") {
        console.log("Editor initialized for Puzzle ID:", newPuzzleId);
        isEditMode = true;
        puzzleId = newPuzzleId;
        await loadPuzzleData(newPuzzleId);
    } else {
        render(); // Render empty grid
    }
}

// --- NEW: Playback Logic ---
function changeTurn(delta) {
    // Find the maximum path length among all units to determine the max turn
    const maxTurn = units.length > 0
        ? Math.max(...units.map(u => u.path.length - 1))
        : 0;

    // Update currentTurn, clamped between 0 and maxTurn
    currentTurn = Math.max(0, Math.min(maxTurn, currentTurn + delta));

    updateTurnStatus();
    render();
}

function updateTurnStatus() {
    if (turnStatus) {
        turnStatus.textContent = `Turn: ${currentTurn}`;
    }
}

function selectTool(tool) {
    currentTool = tool;
    pendingEdgeStart = null;
    selectedUnit = null;
    console.log("Tool selected:", tool);
    render();
}

// --- 4. INTERACTION LOGIC ---
function setupInteractions() {
    if (!svg) return;

    svg.oncontextmenu = (e) => e.preventDefault();

    // MOUSE DOWN: Start Drag or Pan
    svg.onmousedown = (evt) => {
        const pt = screenToSVG(evt.clientX, evt.clientY);
        didDrag = false;

        // Right-click Pan (Button 2)
        if (evt.button === 2) {
            for (const n of nodes) {
                if (n.deleted) continue;
                const dx = n.x - pt.x;
                const dy = n.y - pt.y;
                if (dx * dx + dy * dy < 20 * 20) return;
            }
            panning = true;
            panStartX = evt.clientX;
            panStartY = evt.clientY;
            panStartViewBoxX = currentViewBox.x;
            panStartViewBoxY = currentViewBox.y;
            evt.preventDefault();
            return;
        }

        // Left-click Node Dragging
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
    };

    // MOUSE MOVE: Perform Drag or Pan
    window.onmousemove = (evt) => {
        if (panning) {
            const dx = evt.clientX - panStartX;
            const dy = evt.clientY - panStartY;
            const svgRect = svg.getBoundingClientRect();
            const scaleX = currentViewBox.width / svgRect.width;
            const scaleY = currentViewBox.height / svgRect.height;

            currentViewBox.x = panStartViewBoxX - dx * scaleX;
            currentViewBox.y = panStartViewBoxY - dy * scaleY;
            updateViewBox();
            return;
        }

        if (potentialDrag && !dragging) {
            const dx = evt.clientX - dragStartX;
            const dy = evt.clientY - dragStartY;
            if (Math.sqrt(dx * dx + dy * dy) > DRAG_THRESHOLD) {
                dragging = true;
                didDrag = true;
                potentialDrag = false;
            }
        }

        if (dragging) {
            const n = getNode(draggingNodeId);
            if (n) {
                const pt = screenToSVG(evt.clientX, evt.clientY);
                n.x = Math.round(pt.x);
                n.y = Math.round(pt.y);
                render();
            }
        }
    };

    window.onmouseup = () => {
        panning = false;
        dragging = false;
        potentialDrag = false;
        draggingNodeId = null;
    };

    // CLICK: Tool Actions
    svg.onclick = (evt) => {
        if (panning || didDrag) return;

        const pt = screenToSVG(evt.clientX, evt.clientY);

        // A. Add Node
        if (currentTool === "add-node") {
            const maxIndex = nodes.length > 0
                ? Math.max(...nodes.map(n => typeof n.id === 'number' ? n.id : -1))
                : -1;
            let newId = Math.max(nextNodeId, maxIndex + 1);
            nextNodeId = newId + 1;

            nodes.push({
                id: newId,
                x: Math.round(pt.x),
                y: Math.round(pt.y),
                deleted: false
            });
            render();
            return;
        }

        // B. Add Edge
        if (currentTool === "add-edge") {
            let clickedNode = findClickedNode(pt);
            if (clickedNode === null) return;

            if (pendingEdgeStart === null) {
                pendingEdgeStart = clickedNode;
            } else {
                if (pendingEdgeStart !== clickedNode) {
                    edges.push({
                        id: nextEdgeId++,
                        start: pendingEdgeStart,
                        end: clickedNode,
                        deleted: false
                    });
                }
                pendingEdgeStart = null;
            }
            render();
            return;
        }

        // C. Place Unit
        if (currentTool === "place-unit") {
            let clickedNode = findClickedNode(pt);
            if (clickedNode !== null) {
                units.push({
                    id: nextUnitId++,
                    faction: factionSelect.value,
                    type: unitTypeSelect.value,
                    path: [clickedNode],
                    color: randomColor(),
                    deleted: false
                });
                render();
            }
            return;
        }

        // D. Edit Path
        if (currentTool === "edit-path") {
            if (selectedUnit == null) return;
            let clickedNode = findClickedNode(pt);
            if (clickedNode !== null) {
                appendNodeToSelectedPath(clickedNode);
            }
        }
    };
}

// --- 5. HELPER FUNCTIONS ---

function screenToSVG(screenX, screenY) {
    if (!svg) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = screenX;
    pt.y = screenY;
    try {
        return pt.matrixTransform(svg.getScreenCTM().inverse());
    } catch (e) {
        return { x: 0, y: 0 };
    }
}

function updateViewBox() {
    if (!svg) return;
    svg.setAttribute("viewBox", `${currentViewBox.x} ${currentViewBox.y} ${currentViewBox.width} ${currentViewBox.height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
}

function setupZoom() {
    if (!svg) return;
    svg.onwheel = (evt) => {
        evt.preventDefault();
        const pt = screenToSVG(evt.clientX, evt.clientY);
        const zoomFactor = evt.deltaY > 0 ? 0.9 : 1.1;

        const newWidth = currentViewBox.width / zoomFactor;
        const newHeight = currentViewBox.height / zoomFactor;

        const dx = (pt.x - currentViewBox.x) * (1 - 1/zoomFactor);
        const dy = (pt.y - currentViewBox.y) * (1 - 1/zoomFactor);

        currentViewBox.x += dx;
        currentViewBox.y += dy;
        currentViewBox.width = newWidth;
        currentViewBox.height = newHeight;

        zoomLevel *= zoomFactor;
        updateViewBox();
    };
}

function findClickedNode(pt) {
    for (const n of nodes) {
        if (n.deleted) continue;
        const dx = n.x - pt.x;
        const dy = n.y - pt.y;
        if (dx * dx + dy * dy < 20 * 20) {
            return n.id;
        }
    }
    return null;
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

function loadUnitTypes() {
    if (!factionSelect || !unitTypeSelect) return;
    const faction = factionSelect.value;
    unitTypeSelect.innerHTML = "";
    const options = faction === "enemy" ? ["Grunt", "Brute"] : ["Swordsman", "Nun", "Archer"];
    for (const type of options) {
        const opt = document.createElement("option");
        opt.value = type;
        opt.textContent = type;
        unitTypeSelect.appendChild(opt);
    }
}

function appendNodeToSelectedPath(nodeId) {
    if (selectedUnit == null) return;
    const unit = getUnit(selectedUnit);
    if (unit) {
        unit.path.push(nodeId);
        // If we modify paths, we might need to update the turn status max limit
        updateTurnStatus();
        render();
    }
}

function deleteNode(id) {
    const n = getNode(id);
    if (!n) return;
    n.deleted = true;
    edges.forEach(e => {
        if (e.start === id || e.end === id) e.deleted = true;
    });
    units.forEach(u => {
        u.path = u.path.filter(pid => pid !== id);
    });
    render();
}

function deleteEdge(id) {
    const e = edges.find(ed => ed.id === id);
    if (e) {
        e.deleted = true;
        render();
    }
}

function deleteUnit(id) {
    const u = getUnit(id);
    if (u) {
        u.deleted = true;
        render();
    }
}

// --- 6. DATA LOADING & EXPORT ---

async function loadPuzzleData(puzzleId) {
    try {
        const response = await fetch(`/puzzles/${puzzleId}/data`);
        if (!response.ok) throw new Error("Failed to fetch data");
        const data = await response.json();

        nodes = data.nodes.map(n => ({
            id: n.node_index,
            x: n.x_position,
            y: n.y_position,
            deleted: false
        }));

        const idMap = {};
        data.nodes.forEach(n => idMap[n.id] = n.node_index);

        edges = data.edges.map(e => ({
            id: e.edge_index,
            start: idMap[e.start_node_id],
            end: idMap[e.end_node_id],
            deleted: false
        })).filter(e => e.start !== undefined && e.end !== undefined);

        units = data.units.map((u, index) => ({
            id: index,
            faction: u.faction,
            type: u.unit_type,
            path: u.path?.path_node
                ? u.path.path_node.sort((a,b) => a.order_index - b.order_index).map(pn => idMap[pn.node_id])
                : [],
            color: randomColor(),
            deleted: false
        }));

        // Reset IDs
        nextNodeId = (nodes.length > 0 ? Math.max(...nodes.map(n => n.id)) : -1) + 1;
        nextEdgeId = (edges.length > 0 ? Math.max(...edges.map(e => e.id)) : -1) + 1;
        nextUnitId = units.length;

        // Populate Form
        if (editorForm) {
            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
            const getMeta = (key) => document.querySelector(`[data-puzzle-${key}]`)?.getAttribute(`data-puzzle-${key}`);

            setVal("name", getMeta("name"));
            setVal("game_mode", getMeta("game-mode"));
            setVal("coins", getMeta("coins"));
            setVal("description", getMeta("description"));
        }

        // Reset View & Playback
        zoomLevel = 1.0;
        currentViewBox = { x: 0, y: 0, width: 1000, height: 1000 };
        currentTurn = 0; // Start at beginning
        updateTurnStatus();
        render();

    } catch (e) {
        console.error("Error loading puzzle:", e);
    }
}

async function exportPuzzle(evt) {
    evt?.preventDefault();
    if (!editorForm) return;

    const formData = new FormData(editorForm);

    const payload = {
        name: formData.get("name") || "Untitled",
        model: "Updated Manually",
        game_mode: formData.get("game_mode"),
        coins: Number(formData.get("coins") || 0),
        description: formData.get("description") || "",
        is_working: formData.get("is_working") === "False",

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

    console.log("Exporting:", payload);

    try {
        const method = isEditMode ? "PUT" : "POST";

        // CHANGED: Use 'let' so we can modify the URL
        let url = isEditMode ? `/puzzles/${puzzleId}` : "/puzzles";

        const isChatContext = document.getElementById("chat-container") !== null;
        const headers = { "Content-Type": "application/json" };

        if (!isEditMode && isChatContext) {
            headers["X-From-Chat"] = "true";

            // NEW: Get the current session ID and add it to the URL
            const sessionInput = document.getElementById("session_id_input");
            if (sessionInput && sessionInput.value) {
                url += `?session_id=${sessionInput.value}`;
            }
        }

        const response = await fetch(url, {
            method: method,
            headers: headers,
            body: JSON.stringify(payload)
        });

        if (!isEditMode && isChatContext && response.ok) {
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const data = await response.json();
                if (data.success && data.session_id) {
                    console.log("Puzzle created in chat context. Session ID:", data.session_id);
                    const sessionInput = document.getElementById("session_id_input");
                    if (sessionInput) sessionInput.value = data.session_id;

                    if (window.htmx) {
                        htmx.trigger("body", "refreshSidebar");
                    }

                    const chatContainer = document.getElementById("chat-container");
                    if (chatContainer && window.htmx) {
                        setTimeout(() => {
                            htmx.ajax("GET", `/puzzles/chat/${data.session_id}`, {
                                target: "#chat-container",
                                swap: "innerHTML"
                            });
                        setTimeout(() => {
                            if (window.htmx) {
                                htmx.trigger("body", "refreshPuzzle");
                            }
                        }, 200);
                    }, 100);
                }
                    return;
                }
            }
        }

        if (isEditMode && isChatContext && response.ok) {
            console.log("Puzzle updated in chat context");
            if (window.htmx) {
                htmx.trigger("body", "refreshSidebar");
                setTimeout(() => { htmx.trigger("body", "refreshPuzzle"); }, 100);
            }
            return;
        }

        if (response.redirected) {
            if (isChatContext) {
                if (window.htmx) {
                    htmx.trigger("body", "refreshSidebar");
                    htmx.trigger("body", "refreshPuzzle");
                }
            } else {
                window.location.href = response.url;
            }
        } else if (!response.ok) {
            alert("Error saving puzzle: " + await response.text());
        } else {
            if (isChatContext) {
                 if (window.htmx) {
                     htmx.trigger("body", "refreshSidebar");
                     htmx.trigger("body", "refreshPuzzle");
                 }
            } else {
                 window.location.reload();
            }
        }
    } catch (e) {
        alert("Request failed: " + e);
    }
}

// --- 7. RENDER FUNCTION ---
function render() {
    if (!svg) return;
    svg.innerHTML = "";

    // A. Draw Edges
    edges.filter(e => !e.deleted).forEach(e => {
        const a = getNode(e.start);
        const b = getNode(e.end);
        if (!a || !b) return;

        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", a.x);
        line.setAttribute("y1", a.y);
        line.setAttribute("x2", b.x);
        line.setAttribute("y2", b.y);
        line.setAttribute("stroke", "#1e1e1e");
        line.setAttribute("stroke-width", 4);

        line.addEventListener("contextmenu", (evt) => {
            evt.preventDefault();
            evt.stopPropagation();
            deleteEdge(e.id);
        });

        svg.appendChild(line);
    });

    // B. Draw Units (Ghost Paths)
    units.filter(u => !u.deleted).forEach(u => {
        for (let i = 0; i < u.path.length - 1; i++) {
            const a = getNode(u.path[i]);
            const b = getNode(u.path[i + 1]);
            if (a && b) {
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", a.x);
                line.setAttribute("y1", a.y);
                line.setAttribute("x2", b.x);
                line.setAttribute("y2", b.y);
                line.setAttribute("stroke", u.color);
                line.setAttribute("stroke-width", 2);
                line.setAttribute("opacity", "0.3");
                line.style.pointerEvents = "none";
                svg.appendChild(line);
            }
        }
    });

    // C. Draw Nodes
    nodes.filter(n => !n.deleted).forEach(n => {
        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.setAttribute("transform", `translate(${n.x},${n.y})`);

        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("r", 20);
        c.setAttribute("fill", "white");
        c.setAttribute("stroke", "black");
        c.setAttribute("stroke-width", 2);

        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `Node ${n.id}\n(${n.x}, ${n.y})`;
        c.appendChild(title);

        c.addEventListener("contextmenu", (evt) => {
            if (!panning) {
                evt.preventDefault();
                evt.stopPropagation();
                deleteNode(n.id);
            }
        });

        g.appendChild(c);

        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("dy", ".3em");
        text.textContent = n.id;
        text.style.pointerEvents = "none";
        g.appendChild(text);

        svg.appendChild(g);
    });

    // D. Draw Unit Markers (With Squares/Triangles)

    // 1. Group units by their current node ID
    const unitsAtNode = {};

    units.filter(u => !u.deleted && u.path.length > 0).forEach(u => {
        const pathIndex = Math.min(currentTurn, u.path.length - 1);
        const nodeId = u.path[pathIndex];

        if (!unitsAtNode[nodeId]) {
            unitsAtNode[nodeId] = [];
        }
        unitsAtNode[nodeId].push(u);
    });

    // 2. Iterate over each node group
    Object.keys(unitsAtNode).forEach(nodeIdStr => {
        const nodeId = parseInt(nodeIdStr);
        const nodeUnits = unitsAtNode[nodeId];
        const currentNode = getNode(nodeId);

        if (!currentNode) return;

        const count = nodeUnits.length;
        const radius = 30;
        const startAngle = -Math.PI / 2;

        nodeUnits.forEach((u, index) => {
            let cx, cy;

            if (count === 1) {
                cx = currentNode.x + 15;
                cy = currentNode.y - 15;
            } else {
                const angle = startAngle + (2 * Math.PI * index) / count;
                cx = currentNode.x + Math.cos(angle) * radius;
                cy = currentNode.y + Math.sin(angle) * radius;
            }

            // Create a Group for the Unit (Circle + Icon)
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.setAttribute("transform", `translate(${cx},${cy})`);
            g.style.cursor = "pointer";

            // 1. Main Colored Circle
            const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            c.setAttribute("r", 15);
            c.setAttribute("fill", u.color);
            c.setAttribute("stroke", (selectedUnit === u.id) ? "gold" : "white");
            c.setAttribute("stroke-width", (selectedUnit === u.id) ? 3 : 1);
            g.appendChild(c);

            // 2. Unit Type Icon (Square or Triangle)
            // Icon color is white for contrast, semi-transparent
            const iconColor = "rgba(255, 255, 255, 1)";

            if (u.type === "Swordsman") {
                // Draw Square (Centered)
                const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                rect.setAttribute("x", -5);
                rect.setAttribute("y", -5);
                rect.setAttribute("width", 10);
                rect.setAttribute("height", 10);
                rect.setAttribute("fill", iconColor);
                rect.style.pointerEvents = "none"; // Let clicks hit the group
                g.appendChild(rect);
            } else if (u.type === "Grunt") {
                // Draw Triangle (Centered)
                // Points: Top(0, -5), BottomRight(5, 5), BottomLeft(-5, 5)
                const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
                poly.setAttribute("points", "0,-5 5,5 -5,5");
                poly.setAttribute("fill", iconColor);
                poly.style.pointerEvents = "none";
                g.appendChild(poly);
            }

            // 3. Interactions (Attached to Group)
            g.onclick = (evt) => {
                evt.stopPropagation();
                selectedUnit = u.id;
                console.log("Unit selected:", u.id);
                render();
            };

            const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
            title.textContent = `${u.faction} ${u.type}\nTurn ${currentTurn}`;
            g.appendChild(title);

            g.addEventListener("contextmenu", (evt) => {
                evt.preventDefault();
                evt.stopPropagation();
                deleteUnit(u.id);
            });

            svg.appendChild(g);
        });
    });

    // E. Pending Edge Helper
    if (pendingEdgeStart !== null) {
        const n = getNode(pendingEdgeStart);
        if (n) {
            const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            c.setAttribute("cx", n.x);
            c.setAttribute("cy", n.y);
            c.setAttribute("r", 15);
            c.setAttribute("fill", "none");
            c.setAttribute("stroke", "red");
            c.setAttribute("stroke-dasharray", "4");
            c.style.pointerEvents = "none";
            svg.appendChild(c);
        }
    }
}