const enemyContainer = document.getElementById("enemy-units");
const playerContainer = document.getElementById("player-units");

function createUnitRow(index, faction) {
    // Player and enemy unit type options
    const playerTypes = ["Swordman", "Nun", "Archer", "Peasant"];
    const enemyTypes = ["Grunt", "Brute", "Archer"];

    // Build type options based on faction
    const types = faction === "player" ? playerTypes : enemyTypes;
    const typeOptions = types.map(type => `<option value="${type}">${type}</option>`).join("");

    // Movement select only for enemies
    const movementSelect = faction === "enemy" ? `
    <select name="unit_${faction}_${index}_movement" required>
<!--      <option value="">&#45;&#45; Movement &#45;&#45;</option>-->
      <option value="Static">Static</option>
      <option value="One Way">One Way</option>
      <option value="Loop">Loop</option>
    </select>` : "";

    // Combine into a single row
    return `
    <div class="unit-row">
      <label>${faction} ${index + 1}:</label>
      <select name="unit_${faction}_${index}_type" required>
        <option value="">-- Type --</option>
        ${typeOptions}
      </select>
      ${movementSelect}
    </div>`;
}

// Enemy unit count input listener
document.getElementById("enemy_count").addEventListener("input", (e) => {
    const count = parseInt(e.target.value) || 0;
    enemyContainer.innerHTML = "";
    for (let i = 0; i < count; i++) {
        enemyContainer.innerHTML += createUnitRow(i, "enemy");
    }
});

// Player unit count input listener
document.getElementById("player_unit_count").addEventListener("input", (e) => {
    const count = parseInt(e.target.value) || 0;
    playerContainer.innerHTML = "";
    for (let i = 0; i < count; i++) {
        playerContainer.innerHTML += createUnitRow(i, "player");
    }
});



// =======================
// Dynamic Nodes & Edges
// =======================

// Containers
const nodesContainer = document.getElementById("nodes-container");
const edgesContainer = document.getElementById("edges-container");

// Inputs
const nodeCountInput = document.getElementById("node_count");
const edgeCountInput = document.getElementById("edge_count");

// Track current node count for edge dropdowns
let currentNodeCount = 0;

// =======================
// Node Logic
// =======================
nodeCountInput.addEventListener("input", (e) => {
  currentNodeCount = parseInt(e.target.value) || 0;
  nodesContainer.innerHTML = "";

  // Generate node input rows
  for (let i = 0; i < currentNodeCount; i++) {
    nodesContainer.innerHTML += createNodeRow(i);
  }

  // Update edges dropdowns so they match current nodes
  refreshEdgeDropdowns();
});

// Create a single node input row
function createNodeRow(index) {
  return `
    <div class="node-row">
      <label>Node ${index}:</label>
      <input type="number" name="node_${index}_x" placeholder="x" required>
      <input type="number" name="node_${index}_y" placeholder="y" required>
    </div>
  `;
}

// =======================
// Edge Logic
// =======================
edgeCountInput.addEventListener("input", (e) => {
  const edgeCount = parseInt(e.target.value) || 0;
  edgesContainer.innerHTML = "";

  // Generate edge rows
  for (let i = 0; i < edgeCount; i++) {
    edgesContainer.innerHTML += createEdgeRow(i);
  }

  // Fill dropdowns with current node list
  refreshEdgeDropdowns();
});

// Build a single edge row (with placeholder selects)
function createEdgeRow(index) {
  return `
    <div class="edge-row">
      <label>Edge ${index}:</label>
      <select name="edge_${index}_start" required></select>
      →
      <select name="edge_${index}_end" required></select>
    </div>
  `;
}

// =======================
// Dropdown Refresh Logic
// =======================
function refreshEdgeDropdowns() {
  const nodeOptions = buildNodeOptions();
  const allEdgeSelects = edgesContainer.querySelectorAll("select");

  // Update all start/end dropdowns with the same node list
  allEdgeSelects.forEach(select => {
    select.innerHTML = nodeOptions;
  });
}

// Build dropdown options — Node 0, Node 1, Node 2, ...
function buildNodeOptions() {
  let options = "";
  for (let i = 0; i < currentNodeCount; i++) {
    options += `<option value="${i}">Node ${i}</option>`;
  }
  return options;
}





// DELETE puzzle
async function deletePuzzle(event, puzzleId) {
    event.preventDefault(); // prevent form from reloading page

    if (!confirm("Are you sure you want to delete this puzzle?")) return;

    const response = await fetch(`/puzzles/${puzzleId}`, {method: "DELETE"});

    if (response.ok) {
        // remove deleted row from page or reload

        window.location.reload();
        alert("Puzzle deleted!");
    } else {
        alert("Error deleting puzzle");
    }
}
