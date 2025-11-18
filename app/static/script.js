// =======================
// Delete puzzle
// =======================
async function deletePuzzle(event, puzzleId) {
    event.preventDefault();
    if (!confirm("Are you sure you want to delete this puzzle?")) return;

    try {
        const response = await fetch(`/puzzles/${puzzleId}`, {method: "DELETE"});
        if (response.ok) {
            // Redirect to puzzles list after successful deletion
            window.location.href = "/puzzles";
        } else {
            const errorText = await response.text().catch(() => "Unknown error");
            alert(`Error deleting puzzle: ${errorText}`);
        }
    } catch (err) {
        console.error("Error deleting puzzle:", err);
        alert("Error deleting puzzle: " + err.message);
    }
}

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
            <option value="Nun">Nun</option>
            <option value="Archer">Archer</option>
            <option value="Peasant">Peasant</option>
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

