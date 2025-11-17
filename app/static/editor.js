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
        ? ["Grunt", "Archer", "Mage"]
        : ["Swordman", "Knight", "Healer"];

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
    units.filter(u => !u.deleted).forEach(u => {
        const pts = u.path.map(pid => getNode(pid)).filter(Boolean);

        for (let i = 0; i < pts.length - 1; i++) {
            const a = pts[i];
            const b = pts[i + 1];

            const pathLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
            pathLine.setAttribute("x1", a.x);
            pathLine.setAttribute("y1", a.y);
            pathLine.setAttribute("x2", b.x);
            pathLine.setAttribute("y2", b.y);
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
        c.setAttribute("r", 30);
        c.setAttribute("fill", "white");
        c.setAttribute("stroke", "black");
        c.setAttribute("stroke-width", 3);

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

        // Select for editing path
        unitCircle.addEventListener("click", evt => {
            if (currentTool === "edit-path" && selectedUnit != null && selectedUnit !== u.id) {
                evt.stopPropagation();
                appendNodeToSelectedPath(u.path[0]);
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
}

// ======================================================
// Submit PuzzleCreate JSON to FastAPI
// ======================================================

async function exportPuzzle(evt) {
    evt?.preventDefault();

    const formData = new FormData(editorForm);
    const name = (formData.get("name") || "").toString().trim();
    const model = (formData.get("model") || "").toString().trim();
    const game_mode = formData.get("game_mode") || "";
    const coins = Number(formData.get("coins") || 0);
    const description = (formData.get("description") || "").toString().trim();

    if (!name || !model || !game_mode) {
        alert("Name, Model, and Game Mode are required!");
        return;
    }

    const payload = {
        name,
        model,
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



// // ======================================================
// // Export Puzzle -> FastAPI
// // ======================================================
// function exportPuzzle() {
//     const payload = {
//         nodes: nodes.filter(n => !n.deleted).map(n => ({
//             index: n.id,
//             x: n.x,
//             y: n.y
//         })),
//         edges: edges.filter(e => !e.deleted).map(e => ({
//             index: e.id,
//             start: e.start,
//             end: e.end
//         })),
//         units: units.filter(u => !u.deleted).map(u => ({
//             unit_type: u.unit_type,
//             faction: u.faction,
//             path: u.path
//         }))
//     };
//
//     nodesField.value = JSON.stringify(payload.nodes);
//     edgesField.value = JSON.stringify(payload.edges);
//     unitsField.value = JSON.stringify(payload.units);
//
//     async function exportPuzzle() {
//         const payload = {
//             name: document.getElementById("name").value,
//             model: document.getElementById("model").value,
//             game_mode: document.getElementById("game_mode").value,
//             coins: Number(document.getElementById("coins").value || 0),
//             description: document.getElementById("description").value,
//
//             nodes: nodes.filter(n => !n.deleted).map(n => ({
//                 index: n.id,
//                 x: n.x,
//                 y: n.y
//             })),
//
//             edges: edges.filter(e => !e.deleted).map(e => ({
//                 index: e.id,
//                 start: e.start,
//                 end: e.end
//             })),
//
//             units: units.filter(u => !u.deleted).map(u => ({
//                 unit_type: u.unit_type,
//                 faction: u.faction,
//                 path: u.path
//             }))
//         };
//
//         const response = await fetch("/puzzles/", {
//             method: "POST",
//             headers: {"Content-Type": "application/json"},
//             body: JSON.stringify(payload)
//         });
//
//         if (response.redirected) {
//             window.location.href = response.url;
//         } else {
//             const error = await response.text();
//             alert("Puzzle creation failed:\n" + error);
//         }
//     }
//
// }
