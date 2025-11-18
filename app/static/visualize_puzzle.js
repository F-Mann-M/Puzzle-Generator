// ======================================================
// Puzzle Visualization – Interactive Display
// ======================================================

// Store puzzle data and selected unit for interactivity
let storedPuzzleData = null;
let selectedUnitId = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    // --- GET ELEMENTS ---
    const svg = document.getElementById("puzzle-visualization-svg");

    if (!svg) {
        console.error("Puzzle visualization SVG element not found");
        return;
    }

    // Get puzzle ID from the page (you'll need to pass it somehow)
    // Option 1: From a data attribute on the SVG element
    const puzzleId = svg.getAttribute("data-puzzle-id");
    
    // Option 2: Extract from URL
    // const puzzleId = window.location.pathname.split('/').filter(p => p).pop();
    
    if (!puzzleId) {
        console.error("Puzzle ID not found");
        return;
    }

    // Fetch puzzle data from API
    fetch(`/puzzles/${puzzleId}/data`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(puzzleData => {
            storedPuzzleData = puzzleData;
            renderPuzzle(puzzleData, null);
        })
        .catch(err => {
            console.error("Error fetching puzzle data:", err);
        });
});

// ======================================================
// Utility Functions
// ======================================================
function randomColor() {
    return "#" + Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, "0");
}

// Predefined colors for units
const unitColors = ["#ff0000", "#0000ff", "#00ff00", "#ff8800", "#8800ff", "#00ffff", "#ff00ff"];

function getUnitColor(index) {
    return unitColors[index % unitColors.length];
}

// ======================================================
// Render Puzzle
// ======================================================
function renderPuzzle(puzzleData, selectedUnitIdParam = null) {
    // Update module-level selectedUnitId if parameter provided
    if (selectedUnitIdParam !== undefined) {
        selectedUnitId = selectedUnitIdParam;
    }
    if (!puzzleData || !puzzleData.nodes || !puzzleData.edges || !puzzleData.units) {
        console.error("Invalid puzzle data structure");
        return;
    }

    // Get SVG element
    const svg = document.getElementById("puzzle-visualization-svg");
    if (!svg) {
        console.error("Puzzle visualization SVG element not found");
        return;
    }

    svg.innerHTML = "";

    // Create node ID to node mapping
    const nodeMap = {};
    puzzleData.nodes.forEach(node => {
        nodeMap[node.id] = node;
    });

    // Calculate bounding box for viewBox
    if (puzzleData.nodes.length === 0) {
        // Empty puzzle - set default viewBox
        svg.setAttribute("viewBox", "0 0 100 100");
        svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
        return;
    }

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    puzzleData.nodes.forEach(node => {
        minX = Math.min(minX, node.x_position);
        minY = Math.min(minY, node.y_position);
        maxX = Math.max(maxX, node.x_position);
        maxY = Math.max(maxY, node.y_position);
    });

    // Add padding (50 pixels on each side)
    const padding = 50;
    minX -= padding;
    minY -= padding;
    maxX += padding;
    maxY += padding;

    // Set viewBox for proper scaling
    svg.setAttribute("viewBox", `${minX} ${minY} ${maxX - minX} ${maxY - minY}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    // Create node ID to index mapping for edges
    const nodeIdToIndex = {};
    puzzleData.nodes.forEach(node => {
        nodeIdToIndex[node.id] = node.node_index;
    });

    // --- Draw edges (graph connections) ---
    puzzleData.edges.forEach(edge => {
        const startNode = nodeMap[edge.start_node_id];
        const endNode = nodeMap[edge.end_node_id];
        
        if (!startNode || !endNode) return;

        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", startNode.x_position);
        line.setAttribute("y1", startNode.y_position);
        line.setAttribute("x2", endNode.x_position);
        line.setAttribute("y2", endNode.y_position);
        line.setAttribute("stroke", "#666");
        line.setAttribute("stroke-width", 4);
        line.setAttribute("stroke-opacity", "0.5");

        svg.appendChild(line);
    });

    // --- Draw unit paths (draw BEFORE units so unit circles are on top) ---
    // Group edges (node pairs) by which units use them
    const edgeGroups = new Map(); // key: "nodeId1,nodeId2", value: array of {unit, unitIndex, currentNode, nextNode}
    
    // First pass: collect all edges from all units
    puzzleData.units.forEach((unit, unitIndex) => {
        if (!unit.path || !unit.path.path_node || unit.path.path_node.length === 0) return;
        
        // Sort path nodes by order_index
        const sortedPathNodes = [...unit.path.path_node].sort((a, b) => a.order_index - b.order_index);
        
        for (let i = 0; i < sortedPathNodes.length - 1; i++) {
            const currentNodeId = sortedPathNodes[i].node_id;
            const nextNodeId = sortedPathNodes[i + 1].node_id;
            
            const currentNode = nodeMap[currentNodeId];
            const nextNode = nodeMap[nextNodeId];
            
            if (!currentNode || !nextNode) continue;
            
            // Create normalized edge key (always smaller ID first)
            const edgeKey = currentNodeId < nextNodeId 
                ? `${currentNodeId},${nextNodeId}` 
                : `${nextNodeId},${currentNodeId}`;
            
            if (!edgeGroups.has(edgeKey)) {
                edgeGroups.set(edgeKey, []);
            }
            edgeGroups.get(edgeKey).push({ unit, unitIndex, currentNode, nextNode, edgeIndex: i });
        }
    });

    // Second pass: render paths with offsets for shared edges
    puzzleData.units.forEach((unit, unitIndex) => {
        if (!unit.path || !unit.path.path_node || unit.path.path_node.length === 0) return;
        
        // Sort path nodes by order_index
        const sortedPathNodes = [...unit.path.path_node].sort((a, b) => a.order_index - b.order_index);

        // Draw path lines
        for (let i = 0; i < sortedPathNodes.length - 1; i++) {
            const currentNodeId = sortedPathNodes[i].node_id;
            const nextNodeId = sortedPathNodes[i + 1].node_id;

            const currentNode = nodeMap[currentNodeId];
            const nextNode = nodeMap[nextNodeId];

            if (!currentNode || !nextNode) continue;

            // Create normalized edge key
            const edgeKey = currentNodeId < nextNodeId 
                ? `${currentNodeId},${nextNodeId}` 
                : `${nextNodeId},${currentNodeId}`;
            
            // Find all units using this edge
            const edgeUsers = edgeGroups.get(edgeKey) || [];
            
            // Get unique units using this edge (to determine offset position)
            const uniqueUnits = [...new Map(edgeUsers.map(eu => [eu.unit.id, eu.unit])).values()];
            const unitPosition = uniqueUnits.findIndex(u => u.id === unit.id);
            
            // Calculate offset: alternate sides with increasing distance
            // Unit 0: -5px, Unit 1: +5px, Unit 2: -10px, Unit 3: +10px, etc.
            let offsetDistance = 0;
            if (uniqueUnits.length > 1 && unitPosition >= 0) {
                const side = (unitPosition % 2 === 0) ? -1 : 1;  // Alternate: negative for even, positive for odd
                const layer = Math.floor(unitPosition / 2) + 1;  // Layer: 1, 1, 2, 2, 3, 3, ...
                offsetDistance = side * layer * 5;  // 5px per layer
            }

            // Ensure consistent direction for perpendicular calculation
            // Always use smaller node ID -> larger node ID direction
            let x1, y1, x2, y2;
            if (currentNodeId < nextNodeId) {
                x1 = currentNode.x_position;
                y1 = currentNode.y_position;
                x2 = nextNode.x_position;
                y2 = nextNode.y_position;
            } else {
                // Reverse direction to maintain consistency
                x1 = nextNode.x_position;
                y1 = nextNode.y_position;
                x2 = currentNode.x_position;
                y2 = currentNode.y_position;
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
            pathLine.setAttribute("stroke", getUnitColor(unitIndex));
            pathLine.setAttribute("stroke-width", 2);

            svg.appendChild(pathLine);
        }
    });

    // --- Draw nodes ---
    puzzleData.nodes.forEach(node => {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", node.x_position);
        circle.setAttribute("cy", node.y_position);
        circle.setAttribute("r", 15);
        circle.setAttribute("fill", "white");
        circle.setAttribute("stroke", "black");
        circle.setAttribute("stroke-width", 3);

        // Add text label for node index
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", node.x_position);
        text.setAttribute("y", node.y_position);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("dominant-baseline", "central");
        text.setAttribute("font-size", "10");
        text.setAttribute("font-weight", "bold");
        text.setAttribute("fill", "black");
        text.textContent = node.node_index;

        svg.appendChild(circle);
        // svg.appendChild(text);
    });

    // --- Draw units (on their starting nodes) ---
    puzzleData.units.forEach((unit, unitIndex) => {
        if (!unit.path || !unit.path.path_node || unit.path.path_node.length === 0) return;

        // Sort path nodes by order_index
        const sortedPathNodes = [...unit.path.path_node].sort((a, b) => a.order_index - b.order_index);
        const startNodeId = sortedPathNodes[0].node_id;
        const startNode = nodeMap[startNodeId];

        if (!startNode) return;

        const unitCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        unitCircle.setAttribute("cx", startNode.x_position);
        unitCircle.setAttribute("cy", startNode.y_position);
        unitCircle.setAttribute("r", 10);
        unitCircle.setAttribute("fill", getUnitColor(unitIndex));
        unitCircle.setAttribute("stroke", "#000");
        unitCircle.setAttribute("stroke-width", 1);

        // Add title for hover tooltip
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `${unit.faction} ${unit.unit_type || 'Unit'}`;
        unitCircle.appendChild(title);

        // Add click handler for interactivity
        unitCircle.style.cursor = "pointer";
        unitCircle.addEventListener("click", () => {
            // Toggle selection: if same unit clicked, deselect; otherwise select new unit
            selectedUnitId = selectedUnitId === unit.id ? null : unit.id;
            renderPuzzle(storedPuzzleData, selectedUnitId);
        });

        svg.appendChild(unitCircle);

        // Add yellow highlight circle around selected unit
        if (selectedUnitId === unit.id) {
            const highlightCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            highlightCircle.setAttribute("cx", startNode.x_position);
            highlightCircle.setAttribute("cy", startNode.y_position);
            highlightCircle.setAttribute("r", 14);
            highlightCircle.setAttribute("fill", "none");
            highlightCircle.setAttribute("stroke", "yellow");
            highlightCircle.setAttribute("stroke-width", 3);
            highlightCircle.setAttribute("opacity", "0.8");
            svg.appendChild(highlightCircle);
        }
    });

    // --- Draw path index labels (render last so they appear on top) ---
    if (selectedUnitId !== null) {
        const selectedUnit = puzzleData.units.find(u => u.id === selectedUnitId);
        if (selectedUnit && selectedUnit.path && selectedUnit.path.path_node) {
            // Sort path nodes by order_index
            const sortedPathNodes = [...selectedUnit.path.path_node].sort((a, b) => a.order_index - b.order_index);
            
            // Collect all path indices for each node
            const nodeIndices = new Map();
            sortedPathNodes.forEach((pathNode, pathIndex) => {
                const nodeId = pathNode.node_id;
                if (!nodeIndices.has(nodeId)) {
                    nodeIndices.set(nodeId, []);
                }
                nodeIndices.get(nodeId).push(pathIndex);
            });

            // Render one label per node showing all its indices
            nodeIndices.forEach((indices, nodeId) => {
                const node = nodeMap[nodeId];
                if (node) {
                    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    text.setAttribute("x", node.x_position);
                    text.setAttribute("y", node.y_position);
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

