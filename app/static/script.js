// =======================
// Containers
// =======================
const enemyContainer = document.getElementById("enemy-units");
const playerContainer = document.getElementById("player-units");
const nodesContainer = document.getElementById("nodes-container");
const edgesContainer = document.getElementById("edges-container");

const enemyCountInput = document.getElementById("enemy_count");
const playerCountInput = document.getElementById("player_unit_count");
const nodeCountInput = document.getElementById("node_count");
const edgeCountInput = document.getElementById("edge_count");
const turnsInput = document.getElementById("turns");

let currentNodeCount = 0;
let maxTurns = parseInt(turnsInput?.value || 3);

// =======================
// Updates
// =======================
// Only attach create-page handlers when those elements/containers exist
if (nodesContainer && nodeCountInput) {
  nodeCountInput.addEventListener("input", handleNodeChange);
}
if (edgesContainer && edgeCountInput) {
  edgeCountInput.addEventListener("input", handleEdgeChange);
}
if (enemyContainer && enemyCountInput) {
  enemyCountInput.addEventListener("input", handleEnemyChange);
}
if (playerContainer && playerCountInput) {
  playerCountInput.addEventListener("input", handlePlayerChange);
}

// =======================
// Nodes
// =======================
function handleNodeChange(e) {
  currentNodeCount = parseInt(e.target.value) || 0;
  nodesContainer.innerHTML = "";

  // if user selects 0, clear list and stop
  if (currentNodeCount <= 0) {
    refreshEdgeDropdowns();
    return;
  }

  for (let i = 0; i < currentNodeCount; i++) {
    nodesContainer.innerHTML += `
      <div class="node-row">
        <label>Node ${i}:</label>
        <input type="number" name="node_${i}_x" placeholder="x" required>
        <input type="number" name="node_${i}_y" placeholder="y" required>
      </div>
    `;
  }
  refreshEdgeDropdowns();
}

// =======================
// Edges
// =======================
function handleEdgeChange(e) {
  const edgeCount = parseInt(e.target.value) || 0;
  edgesContainer.innerHTML = "";

  for (let i = 0; i < edgeCount; i++) {
    edgesContainer.innerHTML += `
      <div class="edge-row">
        <label>Edge ${i}:</label>
        <select name="edge_${i}_start" required></select>
        →
        <select name="edge_${i}_end" required></select>
      </div>
    `;
  }
  refreshEdgeDropdowns();
}

function refreshEdgeDropdowns() {
  const nodeOptions = Array.from(
    { length: currentNodeCount },
    (_, i) => `<option value="${i}">Node ${i}</option>`
  ).join("");

  edgesContainer.querySelectorAll("select").forEach(sel => (sel.innerHTML = nodeOptions));
}

// =======================
// Build edge list dynamically (connections)
// =======================
function getEdgeList() {
  const edges = [];
  edgesContainer.querySelectorAll(".edge-row").forEach(row => {
    const start = parseInt(row.querySelector(`[name$='_start']`).value);
    const end = parseInt(row.querySelector(`[name$='_end']`).value);
    if (!isNaN(start) && !isNaN(end)) edges.push([start, end]);
  });
  return edges;
}

// =======================
// Unit creation
// =======================
function handleEnemyChange(e) {
  const count = parseInt(e.target.value) || 0;
  enemyContainer.innerHTML = "<h3>Enemy Units</h3>";
  for (let i = 0; i < count; i++) {
    enemyContainer.insertAdjacentHTML("beforeend", createUnitRow(i, "enemy"));
    initUnitPath("enemy", i);
  }
}

function handlePlayerChange(e) {
  const count = parseInt(e.target.value) || 0;
  playerContainer.innerHTML = "<h3>Player Units</h3>";
  for (let i = 0; i < count; i++) {
    playerContainer.insertAdjacentHTML("beforeend", createUnitRow(i, "player"));
    initUnitPath("player", i);
  }
}

function createUnitRow(index, faction) {
  const types = faction === "enemy" ? ["Grunt"] : ["Swordman"];
  const typeOptions = types.map(t => `<option value="${t}">${t}</option>`).join("");

  return `
    <div class="unit-row" id="${faction}-unit-${index}">
      <label>${faction} ${index}:</label>
      <select name="unit_${faction}_${index}_type" required>
        <option value="">-- Type --</option>
        ${typeOptions}
      </select>
      <div id="${faction}-unit-${index}-path" class="path-container"></div>
    </div>
  `;
}

// =======================
// Path logic (One Way)
// =======================
function initUnitPath(faction, index) {
  const pathContainer = document.getElementById(`${faction}-unit-${index}-path`);
  pathContainer.innerHTML = "";

  const label = document.createElement("label");
  label.textContent = "Path:";

  const startSelect = document.createElement("select");
  startSelect.name = `unit_${faction}_${index}_path_0`;
  startSelect.required = false;
  startSelect.innerHTML = buildNodeOptions(true);

  startSelect.addEventListener("change", e => {
    const edges = getEdgeList();
    addNextPathDropdown(faction, index, 1, parseInt(e.target.value), edges);
  });

  pathContainer.appendChild(label);
  pathContainer.appendChild(startSelect);
}

function addNextPathDropdown(faction, index, step, fromNode, edges) {
  const pathContainer = document.getElementById(`${faction}-unit-${index}-path`);
  Array.from(
    pathContainer.querySelectorAll(`select[name^='unit_${faction}_${index}_path_']`)
  )
    .slice(step)
    .forEach(el => el.remove());

  const connected = getConnectedNodes(fromNode, edges);
  if (connected.length === 0) return;

  const select = document.createElement("select");
  select.name = `unit_${faction}_${index}_path_${step}`;
  select.required = false;
  select.innerHTML =
    `<option value="">-- Next Node --</option>` +
    connected.map(n => `<option value="${n}">Node ${n}</option>`).join("");

  select.addEventListener("change", e => {
    if (step < maxTurns) {
      addNextPathDropdown(faction, index, step + 1, parseInt(e.target.value), edges);
    }
  });

  pathContainer.appendChild(select);
}

// =======================
// Helpers
// =======================
function getConnectedNodes(nodeId, edges) {
  const connected = [];
  for (const [a, b] of edges) {
    if (a === nodeId) connected.push(b);
    else if (b === nodeId) connected.push(a);
  }
  return connected;
}

function buildNodeOptions(includePlaceholder = false) {
  const opts = Array.from(
    { length: currentNodeCount },
    (_, i) => `<option value="${i}">Node ${i}</option>`
  ).join("");
  return includePlaceholder
    ? `<option value="">-- Select Node --</option>${opts}`
    : opts;
}

// =======================
// Delete puzzle (unchanged)
// =======================
async function deletePuzzle(event, puzzleId) {
  event.preventDefault();
  if (!confirm("Are you sure you want to delete this puzzle?")) return;

  const response = await fetch(`/puzzles/${puzzleId}`, { method: "DELETE" });
  if (response.ok) {
    window.location.reload();
    alert("Puzzle deleted!");
  } else {
    alert("Error deleting puzzle");
  }
}

// // =======================
// // Edit puzzle (unchanged behavior)
// // =======================
// document.getElementById("refresh-btn")?.addEventListener("click", () => {
//   const data = collectPuzzleData();
//   fetch(`/puzzles/preview`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(data)
//   })
//     .then(r => r.text())
//     .then(html => {
//       document.getElementById("puzzle-visualization").innerHTML = html;
//     });
// });
//
// document.getElementById("save-btn")?.addEventListener("click", e => {
//   e.preventDefault();
//   const data = collectPuzzleData();
//   fetch(`/puzzles/${puzzleId}`, {
//     method: "PUT",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(data)
//   }).then(() => alert("Puzzle updated!"));
// });
//
// function collectPuzzleData() {
//   return {
//     name: document.querySelector('[name="name"]').value,
//     enemy_count: Number(document.querySelector('[name="enemy_count"]').value),
//     player_unit_count: Number(document.querySelector('[name="player_unit_count"]').value),
//     turns: Number(document.querySelector('[name="turns"]').value)
//   };
// }


// =======================
// Generate Puzzle Page – Unit Type dropdowns (uses -generate IDs)
// =======================
document.addEventListener("DOMContentLoaded", () => {
  // Only run on the generate page
  const generateForm = document.querySelector('form[action="/puzzles/generate"]');
  if (!generateForm) return;

  console.log("✅ Generate puzzle script active");

  const enemyContainerGen  = document.getElementById("enemy-units-generate");
  const playerContainerGen = document.getElementById("player-units-generate");

  const enemyCountInputGen = document.getElementById("enemy_count");
  const playerCountInputGen = document.getElementById("player_unit_count");

  // --- Enemy dropdowns ---
enemyCountInputGen?.addEventListener("input", e => {
  const count = parseInt(e.target.value) || 0;
  enemyContainerGen.innerHTML = "";
  if (count <= 0) return;

  for (let i = 0; i < count; i++) {
    enemyContainerGen.insertAdjacentHTML(
      "beforeend",
      `
      <div class="enemy-type-row">
        <label>Enemy ${i}:</label>

        <!-- Enemy Type -->
        <select name="enemy_type_${i}" required>
          <option value="">-- Select Type --</option>
          <option value="Grunt">Grunt</option>
<!--          <option value="Brute">Brute</option>-->
<!--          <option value="Archer">Archer</option>-->
        </select>

        <!-- Enemy Movement -->
        <select name="enemy_movement_${i}" required>
          <option value="Static" selected>Static</option>
          <option value="Move">Move</option>
<!--          <option value="Loop">Loop</option>-->
        </select>
      </div>
      `
    );
  }
});


  // --- Player dropdowns ---
  playerCountInputGen?.addEventListener("input", e => {
    const count = parseInt(e.target.value) || 0;
    playerContainerGen.innerHTML = "";
    if (count <= 0) return;

    for (let i = 0; i < count; i++) {
      playerContainerGen.insertAdjacentHTML(
        "beforeend",
        `
        <div class="player-type-row">
          <label>Player Unit ${i}:</label>
          <select name="player_type_${i}" required>
            <option value="">-- Select Type --</option>
            <option value="Swordman">Swordman</option>
            <option value="Nun">Nun</option>
            <option value="Archer">Archer</option>
            <option value="Peasant">Peasant</option>
          </select>
        </div>
        `
      );
    }
  });
});
