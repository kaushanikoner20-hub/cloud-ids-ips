// Phase 0 dashboard shell.
// No statistics/chart polling yet - that arrives with Phase 5
// (ARCHITECTURE.md Section 11). For now this just confirms the API is
// reachable so the shell isn't entirely inert.

async function checkHealth() {
  const badge = document.getElementById("health-badge");
  try {
    const res = await fetch("/api/v1/health");
    if (res.ok) {
      badge.textContent = "API healthy";
      badge.className = "badge badge-ok";
    } else {
      throw new Error(`status ${res.status}`);
    }
  } catch (err) {
    badge.textContent = "API unreachable";
    badge.className = "badge badge-error";
  }
}

checkHealth();