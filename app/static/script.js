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
        {length: currentNodeCount},
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
        {length: currentNodeCount},
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

    const response = await fetch(`/puzzles/${puzzleId}`, {method: "DELETE"});
    if (response.ok) {
        window.location.reload();
        alert("Puzzle deleted!");
    } else {
        alert("Error deleting puzzle");
    }
}

// =======================
// Submit Puzzle as JSON
// =======================
document.getElementById("puzzle-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();

    // ----- Nodes -----
    const nodes = [];
    document.querySelectorAll(".node-row").forEach((row, i) => {
        const x = parseFloat(row.querySelector(`[name="node_${i}_x"]`).value);
        const y = parseFloat(row.querySelector(`[name="node_${i}_y"]`).value);
        nodes.push({index: i, x: x, y: y});
    });

    // ----- Edges -----
    // use getEdgeList() and map to objects {start, end}
    const edges = getEdgeList().map(([start, end], i) => ({
        index: i,      // ✅ new index key
        start: start,  // optional rename for clarity
        end: end       // optional rename for clarity
    }));

    // ----- Units -----
    const units = [];
    // Enemies
    document.querySelectorAll("#enemy-units .unit-row").forEach((row, i) => {
        const type = row.querySelector("select").value;
        const faction = "enemy";
        const path = [];
        row.querySelectorAll("select[name^='unit_enemy_']").forEach(sel => {
            const val = parseInt(sel.value);
            if (!isNaN(val)) path.push(val);
        });
        units.push({faction, type, path});
    });
    // Players
    document.querySelectorAll("#player-units .unit-row").forEach((row, i) => {
        const type = row.querySelector("select").value;
        const faction = "player";
        const path = [];
        row.querySelectorAll("select[name^='unit_player_']").forEach(sel => {
            const val = parseInt(sel.value);
            if (!isNaN(val)) path.push(val);
        });
        units.push({faction, type, path});
    });

    // ----- Combine -----
    const data = {
        name: document.getElementById("name").value,
        model: "Created by user",
        game_mode: document.getElementById("game_mode").value,
        coins: parseInt(document.getElementById("coins").value) || 0,
        nodes,
        edges,
        units
    };

    // ----- Send -----
    const response = await fetch("/puzzles/", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    // ✅ Check if backend returned a redirect
if (response.redirected) {
  window.location.href = response.url;  // manually follow it
} else if (response.ok) {
  const json = await response.json().catch(() => null);
  if (json?.id) {
    // fallback if backend returns the new puzzle ID as JSON
    window.location.href = `/puzzles/${json.id}`;
  } else {
    alert("✅ Puzzle created!");
  }
} else {
  alert("❌ Error creating puzzle");
}
});


// =======================
// Generate Puzzle Page – Build structured JSON
// =======================
document.addEventListener("DOMContentLoaded", () => {
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
          <select name="enemy_type_${i}" required>
            <option value="">-- Select Type --</option>
            <option value="Grunt">Grunt</option>
          </select>
          <select name="enemy_movement_${i}" required>
            <option value="Static" selected>Static</option>
            <option value="Move">Move</option>
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
            <option value="Swordsman">Swordsman</option>
<!--            <option value="Nun">Nun</option>-->
<!--            <option value="Archer">Archer</option>-->
<!--            <option value="Peasant">Peasant</option>-->
          </select>
        </div>
        `
      );
    }
  });

  // --- Intercept form submission ---
  generateForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    // ----- Collect values -----
    const name = document.getElementById("name").value;
    const model = document.getElementById("model").value;
    const game_mode = document.getElementById("game_mode").value;
    const node_count = parseInt(document.getElementById("node_count").value) || 0;
    const edge_count = parseInt(document.getElementById("edge_count").value) || 0;
    const turns = parseInt(document.getElementById("turns").value) || 0;

    // ----- Build units -----
    const units = [];

    // Enemies
    enemyContainerGen.querySelectorAll(".enemy-type-row").forEach((row) => {
      const type = row.querySelector(`[name^="enemy_type_"]`).value;
      const movement = row.querySelector(`[name^="enemy_movement_"]`).value;
      if (type) units.push({ faction: "enemy", type, movement });
    });

    // Players
    playerContainerGen.querySelectorAll(".player-type-row").forEach((row) => {
      const type = row.querySelector(`[name^="player_type_"]`).value;
      if (type) units.push({ faction: "player", type });
    });

    // ----- Build final data object -----
    const data = {
      name,
      model,
      game_mode,
      node_count,
      edge_count,
      turns,
      units,
    };

    console.log("📤 Sending puzzle generation JSON:", data);

    // ----- Send to backend -----
    const response = await fetch("/puzzles/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (response.redirected) {
    window.location.href = response.url;  // manually follow it
    } else if (response.ok) {
      alert("✅ Puzzle generation request sent!");
    } else {
      const err = await response.text();
      alert("❌ Error generating puzzle: " + err);
      console.error("❌ Server response:", err);
    }
  });
});


// ========================
// Puzzle Preview
// ========================

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("puzzle-form");
  const plotDiv = document.getElementById("puzzle-plot");

  if (!form || !plotDiv) return;

  async function updatePreview() {
    const formData = new FormData(form);
    const config = Object.fromEntries(formData.entries());

    if (!config.node_count || !config.edge_count) return;

    try {
      const res = await fetch("/puzzles/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const fig = await res.json(); // ✅ already parsed
      Plotly.react("puzzle-plot", fig.data, fig.layout);
    } catch (err) {
      console.error("Preview update failed:", err);
    }
  }

  // Debounced listener
  let timer;
  form.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(updatePreview, 400);
  });
});