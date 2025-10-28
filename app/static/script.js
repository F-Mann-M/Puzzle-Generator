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
