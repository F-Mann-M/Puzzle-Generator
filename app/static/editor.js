// ======================================================
// Puzzle Editor – Complete Updated Version
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

// Internal state
let nodes = [];
let edges = [];
let units = [];
let currentTool = null;
let isEditMode = false;
let puzzleId = null;

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

    if (!svg) return; // Exit if no editor found

    // Reset state
    currentTool = null;
    pendingEdgeStart = null;
    selectedUnit = null;
    isEditMode = false; // Reset edit mode
    puzzleId = null; // Reset puzzle ID

    // Setup Toolbar Listeners
    if (addNodeBtn) addNodeBtn.onclick = () => { selectTool("add-node"); };
    if (addEdgeBtn) addEdgeBtn.onclick = () => { selectTool("add-edge"); };
    if (placeUnitBtn) placeUnitBtn.onclick = () => { selectTool("place-unit"); };
    if (editPathBtn) editPathBtn.onclick = () => { selectTool("edit-path"); };

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
    if (newPuzzleId) {
        console.log("Editor initialized for Puzzle ID:", newPuzzleId);
        isEditMode = true;
        puzzleId = newPuzzleId;
        await loadPuzzleData(newPuzzleId);
    } else {
        render(); // Render empty grid
    }
}

function selectTool(tool) {
    currentTool = tool;
    pendingEdgeStart = null;
    selectedUnit = null;
    console.log("Tool selected:", tool);
    render(); // Re-render to show/hide helpers if needed
}

// --- 4. INTERACTION LOGIC (The Core Fix) ---
function setupInteractions() {
    if (!svg) return;

    // Prevent context menu on SVG (for right-click panning)
    svg.oncontextmenu = (e) => e.preventDefault();

    // MOUSE DOWN: Start Drag or Pan
    svg.onmousedown = (evt) => {
        const pt = screenToSVG(evt.clientX, evt.clientY);
        didDrag = false;

        // Right-click Pan (Button 2)
        if (evt.button === 2) {
            // Check if clicking on a node (ignore pan if so)
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
        // Panning
        if (panning) {
            const dx = evt.clientX - panStartX;
            const dy = evt.clientY - panStartY;
            const svgRect = svg.getBoundingClientRect();
            // Calculate scale to match mouse movement to SVG units
            const scaleX = currentViewBox.width / svgRect.width;
            const scaleY = currentViewBox.height / svgRect.height;

            currentViewBox.x = panStartViewBoxX - dx * scaleX;
            currentViewBox.y = panStartViewBoxY - dy * scaleY;
            updateViewBox();
            return;
        }

        // Node Dragging Check
        if (potentialDrag && !dragging) {
            const dx = evt.clientX - dragStartX;
            const dy = evt.clientY - dragStartY;
            if (Math.sqrt(dx * dx + dy * dy) > DRAG_THRESHOLD) {
                dragging = true;
                didDrag = true;
                potentialDrag = false;
            }
        }

        // Actual Node Dragging
        if (dragging) {
            const n = getNode(draggingNodeId);
            if (n) {
                // We need to convert screen coordinates to SVG coordinates dynamically here
                // Note: screenToSVG uses the SVG element, so we call it locally
                const pt = screenToSVG(evt.clientX, evt.clientY);
                n.x = Math.round(pt.x);
                n.y = Math.round(pt.y);
                render();
            }
        }
    };

    // MOUSE UP: Stop Drag or Pan
    window.onmouseup = () => {
        panning = false;
        dragging = false;
        potentialDrag = false;
        draggingNodeId = null;
    };

    // CLICK: Tool Actions (Add Node, Edge, Unit)
    svg.onclick = (evt) => {
        if (panning || didDrag) return;

        const pt = screenToSVG(evt.clientX, evt.clientY);

        // A. Add Node
        if (currentTool === "add-node") {
            // Determine a safe ID (max existing ID + 1)
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

        // Center zoom on mouse
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

        // Map Backend Data (x_position) to Frontend Data (x)
        nodes = data.nodes.map(n => ({
            id: n.node_index,
            x: n.x_position, // MAPPING FIX
            y: n.y_position, // MAPPING FIX
            deleted: false
        }));

        // Map IDs to Indices for Edges
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

        // Update ID counters
        nextNodeId = (nodes.length > 0 ? Math.max(...nodes.map(n => n.id)) : -1) + 1;
        nextEdgeId = (edges.length > 0 ? Math.max(...edges.map(e => e.id)) : -1) + 1;
        nextUnitId = units.length;

        // Populate Form Fields if available
        if (editorForm) {
            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
            const getMeta = (key) => document.querySelector(`[data-puzzle-${key}]`)?.getAttribute(`data-puzzle-${key}`);

            setVal("name", getMeta("name"));
            setVal("game_mode", getMeta("game-mode"));
            setVal("coins", getMeta("coins"));
            setVal("description", getMeta("description"));
        }

        // Fit View
        zoomLevel = 1.0;
        currentViewBox = { x: 0, y: 0, width: 1000, height: 1000 };
        render();

    } catch (e) {
        console.error("Error loading puzzle:", e);
    }
}

async function exportPuzzle(evt) {
    evt?.preventDefault();
    if (!editorForm) return;

    const formData = new FormData(editorForm);

    // Construct payload strictly matching schema
    const payload = {
        name: formData.get("name") || "Untitled",
        model: "Updated Manually",
        game_mode: formData.get("game_mode"),
        coins: Number(formData.get("coins") || 0),
        description: formData.get("description") || "",
        is_working: formData.get("is_working") === "False",

        // Map Frontend (x) back to Backend expected format
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
        const url = isEditMode ? `/puzzles/${puzzleId}` : "/puzzles";
        
        // Check if we're in chat context
        const isChatContext = document.getElementById("chat-container") !== null;
        
        // Prepare headers
        const headers = { "Content-Type": "application/json" };
        
        // If creating new puzzle in chat context, add header to get session_id back
        if (!isEditMode && isChatContext) {
            headers["X-From-Chat"] = "true";
        }

        const response = await fetch(url, {
            method: method,
            headers: headers,
            body: JSON.stringify(payload)
        });

        // Handle JSON response from chat context (new puzzle creation)
        if (!isEditMode && isChatContext && response.ok) {
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const data = await response.json();
                if (data.success && data.session_id) {
                    console.log("Puzzle created in chat context. Session ID:", data.session_id);
                    
                    // Update session_id input
                    const sessionInput = document.getElementById("session_id_input");
                    if (sessionInput) {
                        sessionInput.value = data.session_id;
                    }
                    
                    // Trigger refreshSidebar first to show new session
                    if (window.htmx) {
                        htmx.trigger("body", "refreshSidebar");
                    }
                    
                    // Load the session in chat container (this will also trigger refreshPuzzle via HX-Trigger header)
                    const chatContainer = document.getElementById("chat-container");
                    if (chatContainer && window.htmx) {
                        // Wait a bit for sidebar to update, then load session
                        setTimeout(() => {
                            htmx.ajax("GET", `/puzzles/chat/${data.session_id}`, {
                                target: "#chat-container",
                                swap: "innerHTML"
                            });

                        // Also explicitly trigger refreshPuzzle after a delay to ensure editor reloads
                        setTimeout(() => {
                            if (window.htmx) {
                                htmx.trigger("body", "refreshPuzzle");
                            }
                        }, 200);
                    }, 100);
                }
                    
                    return; // Exit early, don't redirect
                }
            }
        }

        // Handle update (PUT request) in chat context
        if (isEditMode && isChatContext && response.ok) {
            console.log("Puzzle updated in chat context");
            
            // Trigger refreshSidebar and refreshPuzzle to update editor
            if (window.htmx) {
                htmx.trigger("body", "refreshSidebar");
                // Wait a bit then refresh editor to reload updated puzzle
                setTimeout(() => {
                    htmx.trigger("body", "refreshPuzzle");
                }, 100);
            }
            
            return; // Stay in chat context
        }

        if (response.redirected) {
            // --- FIX: Check context before redirecting ---
            if (isChatContext) {
                console.log("Puzzle updated. Staying in chat context.");

                if (window.htmx) {
                    htmx.trigger("body", "refreshSidebar");
                    htmx.trigger("body", "refreshPuzzle");
                }

                console.log("Puzzle updated. Staying in chat context.");
            } else {
                // Normal behavior for 'update-puzzle.html': Follow the redirect
                window.location.href = response.url;
            }
        } else if (!response.ok) {
            alert("Error saving puzzle: " + await response.text());
        } else {
            // Fallback for non-redirecting success codes
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
        line.setAttribute("stroke", "#666");
        line.setAttribute("stroke-width", 4);

        // Right-click Edge to delete
        line.addEventListener("contextmenu", (evt) => {
            evt.preventDefault();
            evt.stopPropagation();
            deleteEdge(e.id);
        });

        svg.appendChild(line);
    });

    // B. Draw Units (Paths)
    // (Simplified rendering for brevity, can copy complex offset logic if needed)
    units.filter(u => !u.deleted).forEach(u => {
         // Draw connections between nodes in path
         for (let i = 0; i < u.path.length - 1; i++) {
             const a = getNode(u.path[i]);
             const b = getNode(u.path[i+1]);
             if (a && b) {
                 const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                 line.setAttribute("x1", a.x);
                 line.setAttribute("y1", a.y);
                 line.setAttribute("x2", b.x);
                 line.setAttribute("y2", b.y);
                 line.setAttribute("stroke", u.color);
                 line.setAttribute("stroke-width", 3);
                 line.setAttribute("opacity", "0.7");
                 line.style.pointerEvents = "none"; // Let clicks pass through to edges
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

        // Tooltip
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `Node ${n.id}\n(${n.x}, ${n.y})`;
        c.appendChild(title);

        // Right-click Node to delete
        c.addEventListener("contextmenu", (evt) => {
            if (!panning) {
                evt.preventDefault();
                evt.stopPropagation();
                deleteNode(n.id);
            }
        });

        g.appendChild(c);

        // Draw Index Label
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("dy", ".3em");
        text.textContent = n.id;
        text.style.pointerEvents = "none";
        g.appendChild(text);

        svg.appendChild(g);
    });

    // D. Draw Unit Markers (Circles)
    units.filter(u => !u.deleted && u.path.length > 0).forEach(u => {
        const startNode = getNode(u.path[0]);
        if (startNode) {
            const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            c.setAttribute("cx", startNode.x + 15); // Offset slightly
            c.setAttribute("cy", startNode.y - 15);
            c.setAttribute("r", 10);
            c.setAttribute("fill", u.color);
            c.setAttribute("stroke", "white");

            // Interaction: Select unit for path editing
            c.onclick = (evt) => {
                evt.stopPropagation();
                selectedUnit = u.id;
                console.log("Unit selected:", u.id);
                render();
            };

            // Visual indicator if selected
            if (selectedUnit === u.id) {
                c.setAttribute("stroke", "gold");
                c.setAttribute("stroke-width", 3);
            }

            // Right-click Unit to delete
            c.addEventListener("contextmenu", (evt) => {
                evt.preventDefault();
                evt.stopPropagation();
                deleteUnit(u.id);
            });

            svg.appendChild(c);
        }
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