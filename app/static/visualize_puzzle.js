// ======================================================
// Puzzle Visualization – Interactive Display
// ======================================================

// Store puzzle data and selected unit for interactivity
let storedPuzzleData = null;
let selectedUnitId = null;
let initializedSvgs = new Set(); // Track which SVGs have been initialized

// Zoom state
let currentViewBox = { x: 0, y: 0, width: 100, height: 100 };
let zoomLevel = 1.0;

// Pan state
let panning = false;
let panStartX = null;
let panStartY = null;
let panStartViewBoxX = null;
let panStartViewBoxY = null;

// Initialize puzzle visualization for a given SVG element
function initializePuzzleVisualization(svg) {
    // Check if this SVG has already been initialized
    const svgId = svg.id || `svg-${Math.random()}`;
    if (initializedSvgs.has(svgId)) {
        console.log("SVG already initialized, skipping:", svgId);
        return;
    }
    
    // Mark as initialized
    initializedSvgs.add(svgId);

    // Get puzzle ID from the data attribute
    const puzzleId = svg.getAttribute("data-puzzle-id");
    
    if (!puzzleId) {
        console.warn("Puzzle ID not found in data-puzzle-id attribute");
        return;
    }

    console.log("Initializing puzzle visualization for puzzle ID:", puzzleId);

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
            renderPuzzle(puzzleData, null, svg);
            // Setup zoom and panning after rendering
            setupZoom(svg);
            setupPanning(svg);
        })
        .catch(err => {
            console.error("Error fetching puzzle data:", err);
        });
}

// Find and initialize all puzzle SVG elements on the page
function findAndInitializeSvgs() {
    const svgs = document.querySelectorAll("#puzzle-visualization-svg");
    svgs.forEach(svg => {
        // Only initialize if it has a puzzle ID and hasn't been initialized yet
        const puzzleId = svg.getAttribute("data-puzzle-id");
        if (puzzleId && !initializedSvgs.has(svg.id || svg.getAttribute("data-puzzle-id"))) {
            initializePuzzleVisualization(svg);
        }
    });
}

// Initialize when DOM is ready (for static pages like puzzle-details.html)
document.addEventListener("DOMContentLoaded", () => {
    findAndInitializeSvgs();
});

// Initialize after HTMX swaps content (for dynamic pages like chat.html)
document.body.addEventListener("htmx:afterSwap", (event) => {
    // Check if the swapped content contains a puzzle SVG
    const target = event.detail.target;
    if (target && (target.id === "puzzle-visualization-container" || target.querySelector("#puzzle-visualization-svg"))) {
        // Small delay to ensure DOM is fully updated
        setTimeout(() => {
            findAndInitializeSvgs();
        }, 10);
    }
});

// Also listen for htmx:load in case the container itself is replaced
document.body.addEventListener("htmx:load", (event) => {
    setTimeout(() => {
        findAndInitializeSvgs();
    }, 10);
});

// ======================================================
// Utility Functions
// ======================================================
function randomColor() {
    return "#" + Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, "0");
}

// Update SVG viewBox from currentViewBox (now accepts svg parameter)
function updateViewBox(svg) {
    if (!svg) return;
    svg.setAttribute("viewBox", `${currentViewBox.x} ${currentViewBox.y} ${currentViewBox.width} ${currentViewBox.height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
}

// Convert screen coordinates to SVG coordinates
function screenToSVG(svg, screenX, screenY) {
    const pt = svg.createSVGPoint();
    pt.x = screenX;
    pt.y = screenY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
}

// Handle mousewheel zoom (now accepts svg parameter)
function setupZoom(svg) {
    if (!svg) return;
    
    // Remove existing wheel listener if any (to prevent duplicates)
    const existingHandler = svg._zoomHandler;
    if (existingHandler) {
        svg.removeEventListener("wheel", existingHandler);
    }
    
    const zoomHandler = (evt) => {
        evt.preventDefault();
        
        // Convert mouse position to SVG coordinates
        const svgPoint = screenToSVG(svg, evt.clientX, evt.clientY);
        
        // Determine zoom factor (positive deltaY = scroll down = zoom out, negative = zoom in)
        const zoomFactor = evt.deltaY > 0 ? 0.9 : 1.1;
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
        
        updateViewBox(svg);
    };
    
    svg.addEventListener("wheel", zoomHandler);
    svg._zoomHandler = zoomHandler; // Store reference for potential cleanup
}

// Handle right-click panning (now accepts svg parameter)
function setupPanning(svg) {
    if (!svg) return;
    
    // Remove existing handlers if any (to prevent duplicates)
    if (svg._panMouseDownHandler) {
        svg.removeEventListener("mousedown", svg._panMouseDownHandler);
        svg.removeEventListener("mousemove", svg._panMouseMoveHandler);
        svg.removeEventListener("contextmenu", svg._panContextMenuHandler);
    }
    
    // Right-click detection for panning
    const mouseDownHandler = (evt) => {
        // Check for right-click pan (button 2 = right mouse button)
        if (evt.button === 2) {
            // Convert click position to SVG coordinates to check if clicking on a node
            const pt = screenToSVG(svg, evt.clientX, evt.clientY);
            
            // Check if clicking on a node - if so, don't pan (let other interactions work)
            if (storedPuzzleData && storedPuzzleData.nodes) {
                let clickedOnNode = false;
                for (const node of storedPuzzleData.nodes) {
                    const dx = node.x_position - pt.x;
                    const dy = node.y_position - pt.y;
                    if (dx * dx + dy * dy < 20 * 20) {
                        // Clicked on a node, don't start panning
                        clickedOnNode = true;
                        break;
                    }
                }
                if (clickedOnNode) {
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
        }
    };
    
    // Handle panning on mouse move
    const mouseMoveHandler = (evt) => {
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
            
            updateViewBox(svg);
        }
    };
    
    // Stop panning on mouse up
    const mouseUpHandler = (evt) => {
        // Stop panning on right mouse button release
        if (evt.button === 2) {
            panning = false;
            panStartX = null;
            panStartY = null;
            panStartViewBoxX = null;
            panStartViewBoxY = null;
        }
    };
    
    // Prevent context menu on SVG when right-clicking in empty area (for panning)
    const contextMenuHandler = (evt) => {
        // Only prevent if we're not clicking on a node
        const pt = screenToSVG(svg, evt.clientX, evt.clientY);
        let clickedOnNode = false;
        
        if (storedPuzzleData && storedPuzzleData.nodes) {
            for (const node of storedPuzzleData.nodes) {
                const dx = node.x_position - pt.x;
                const dy = node.y_position - pt.y;
                if (dx * dx + dy * dy < 20 * 20) {
                    clickedOnNode = true;
                    break;
                }
            }
        }
        
        // If not clicking on a node, prevent context menu to allow panning
        if (!clickedOnNode) {
            evt.preventDefault();
        }
    };
    
    svg.addEventListener("mousedown", mouseDownHandler);
    svg.addEventListener("mousemove", mouseMoveHandler);
    document.addEventListener("mouseup", mouseUpHandler);
    svg.addEventListener("contextmenu", contextMenuHandler);
    
    // Store references for cleanup
    svg._panMouseDownHandler = mouseDownHandler;
    svg._panMouseMoveHandler = mouseMoveHandler;
    svg._panContextMenuHandler = contextMenuHandler;
}

// Predefined colors for units
const unitColors = ["#ff0000", "#0000ff", "#00ff00", "#ff8800", "#8800ff", "#00ffff", "#ff00ff"];

function getUnitColor(index) {
    return unitColors[index % unitColors.length];
}

// ======================================================
// Render Puzzle (now accepts svg parameter)
// ======================================================
function renderPuzzle(puzzleData, selectedUnitIdParam = null, svg = null) {
    // Update module-level selectedUnitId if parameter provided
    if (selectedUnitIdParam !== undefined) {
        selectedUnitId = selectedUnitIdParam;
    }
    
    // Use provided svg or try to find it
    if (!svg) {
        svg = document.getElementById("puzzle-visualization-svg");
    }
    
    if (!svg) {
        console.error("Puzzle visualization SVG element not found");
        return;
    }
    
    if (!puzzleData || !puzzleData.nodes || !puzzleData.edges || !puzzleData.units) {
        console.error("Invalid puzzle data structure");
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
        currentViewBox = { x: 0, y: 0, width: 100, height: 100 };
        zoomLevel = 1.0;
        updateViewBox(svg);
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

    // Set initial viewBox for proper scaling
    currentViewBox = { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    zoomLevel = 1.0;
    updateViewBox(svg);

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
        const unitsOnNode = puzzleData.units.filter(u => {
            if (!u.path || !u.path.path_node || u.path.path_node.length === 0) return false;
            const sortedPathNodes = [...u.path.path_node].sort((a, b) => a.order_index - b.order_index);
            return sortedPathNodes[0].node_id === node.id;
        });
        const unitTypes = unitsOnNode.map(u => `${u.faction} ${u.unit_type || 'Unit'}`).join(', ');

        // Tooltip text
        const tooltipText = document.createElementNS("http://www.w3.org/2000/svg", "text");
        tooltipText.setAttribute("font-size", "11");
        tooltipText.setAttribute("fill", "black");
        tooltipText.setAttribute("font-family", "monospace");
        
        let textContent = `Node: ${node.node_index}\nX: ${node.x_position}\nY: ${node.y_position}`;
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
        tooltipGroup.setAttribute("transform", `translate(${node.x_position}, ${node.y_position})`);

        // Mouseover/mouseout handlers
        circle.addEventListener("mouseenter", () => {
            tooltipGroup.style.display = "block";
        });
        circle.addEventListener("mouseleave", () => {
            tooltipGroup.style.display = "none";
        });

        svg.appendChild(circle);
        svg.appendChild(tooltipGroup);
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
            renderPuzzle(storedPuzzleData, selectedUnitId, svg);
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
                    text.setAttribute("text-anchor", "left");
                    text.setAttribute("dominant-baseline", "left");
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

