const API_FALLBACK_BASE = "http://127.0.0.1:8787";

const state = {
  apiBase: "",
  candidates: [],
  vendors: [],
  runs: [],
  errors: {
    candidates: "",
    vendors: "",
    runs: "",
  },
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("candidate-search")?.addEventListener("input", renderCandidates);
  document.getElementById("candidate-status-filter")?.addEventListener("change", renderCandidates);
  document.getElementById("vendor-search")?.addEventListener("input", renderVendors);
  document.getElementById("vendor-category-filter")?.addEventListener("change", renderVendors);
  loadDashboard();
});

async function loadDashboard() {
  try {
    state.apiBase = await detectApiBase();
    const [candidates, vendors, runs] = await Promise.all([
      fetchJson("/admin/candidates"),
      fetchJson("/admin/vendors"),
      fetchJson("/admin/runs"),
    ]);

    state.candidates = sortCandidates(candidates.items || []);
    state.vendors = vendors.items || [];
    state.runs = runs.items || [];
    state.errors.candidates = formatApiError(candidates);
    state.errors.vendors = formatApiError(vendors);
    state.errors.runs = formatApiError(runs);

    populateVendorCategoryFilter();
    renderCandidates();
    renderVendors();
    renderRuns();
  } catch (error) {
    renderFailureState(`Admin API unavailable: ${error.message}`);
  }
}

async function detectApiBase() {
  try {
    const response = await fetch("/admin/candidates");
    if (response.ok) {
      return "";
    }
  } catch (error) {
    // fall through to local API fallback
  }
  return API_FALLBACK_BASE;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${state.apiBase}${path}`, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function sortCandidates(candidates) {
  return [...candidates].sort((left, right) => String(right.discovered_at || "").localeCompare(String(left.discovered_at || "")));
}

function populateVendorCategoryFilter() {
  const filter = document.getElementById("vendor-category-filter");
  if (!filter) {
    return;
  }
  const categories = Array.from(new Set(state.vendors.map((vendor) => vendor.directory_category).filter(Boolean))).sort();
  categories.forEach((category) => filter.appendChild(new Option(category, category)));
}

function renderCandidates() {
  const body = document.getElementById("candidates-body");
  if (!body) {
    return;
  }
  if (state.errors.candidates) {
    body.innerHTML = `<tr><td colspan="5" class="message">${escapeHtml(state.errors.candidates)}</td></tr>`;
    return;
  }
  const searchValue = document.getElementById("candidate-search")?.value.trim().toLowerCase() || "";
  const statusValue = document.getElementById("candidate-status-filter")?.value || "";

  const rows = state.candidates.filter((candidate) => {
    const matchesSearch = !searchValue || String(candidate.candidate_domain || "").toLowerCase().includes(searchValue);
    const matchesStatus = !statusValue || candidate.candidate_status === statusValue;
    return matchesSearch && matchesStatus;
  });

  body.innerHTML = rows.map((candidate) => {
    const statusClass = candidate.candidate_status === "filtered_out" ? "is-danger" : candidate.candidate_status === "failed" ? "is-warning" : "";
    const rowClass = candidate.candidate_status === "filtered_out" ? "is-filtered-out" : "";
    return `
      <tr class="${rowClass}">
        <td>${escapeHtml(candidate.candidate_domain || "")}</td>
        <td>${escapeHtml(candidate.source_query || "")}</td>
        <td><span class="status-pill ${statusClass}">${escapeHtml(candidate.candidate_status || "")}</span></td>
        <td>${escapeHtml(candidate.discovered_at || "")}</td>
        <td>${escapeHtml(candidate.drop_reason || "")}</td>
      </tr>
    `;
  }).join("") || '<tr><td colspan="5" class="message">No discovery candidates found.</td></tr>';
}

function renderVendors() {
  const body = document.getElementById("vendors-body");
  if (!body) {
    return;
  }
  if (state.errors.vendors) {
    body.innerHTML = `<tr><td colspan="6" class="message">${escapeHtml(state.errors.vendors)}</td></tr>`;
    return;
  }
  const searchValue = document.getElementById("vendor-search")?.value.trim().toLowerCase() || "";
  const categoryValue = document.getElementById("vendor-category-filter")?.value || "";

  const rows = state.vendors.filter((vendor) => {
    const matchesSearch = !searchValue || String(vendor.name || vendor.vendor_name || "").toLowerCase().includes(searchValue);
    const matchesCategory = !categoryValue || vendor.directory_category === categoryValue;
    return matchesSearch && matchesCategory;
  });

  body.innerHTML = rows.map((vendor) => {
    const includeValue = vendor.include_in_directory === true;
    const rowClass = includeValue ? "" : "is-excluded";
    const vendorName = vendor.name || vendor.vendor_name || "";
    return `
      <tr class="${rowClass}">
        <td><a href="${escapeAttribute(vendor.website || "#")}" target="_blank" rel="noreferrer">${escapeHtml(vendorName)}</a></td>
        <td>${escapeHtml(formatList(vendor.lifecycle_stages))}</td>
        <td>${escapeHtml(vendor.directory_category || "")}</td>
        <td>${escapeHtml(vendor.directory_fit || "")}</td>
        <td>${escapeHtml(includeValue ? "true" : "false")}</td>
        <td>
          <div class="actions">
            <button class="action-button action-primary" data-action="include" data-vendor="${escapeAttribute(vendor.website || vendorName)}">Include</button>
            <button class="action-button action-danger" data-action="exclude" data-vendor="${escapeAttribute(vendor.website || vendorName)}">Exclude</button>
            <button class="action-button action-secondary" data-action="rerun-enrichment" data-vendor="${escapeAttribute(vendor.website || vendorName)}">Rerun Enrichment</button>
          </div>
        </td>
      </tr>
    `;
  }).join("") || '<tr><td colspan="6" class="message">No enriched vendors found.</td></tr>';

  body.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", handleVendorAction);
  });
}

function renderRuns() {
  const body = document.getElementById("runs-body");
  if (!body) {
    return;
  }
  if (state.errors.runs) {
    body.innerHTML = `<tr><td colspan="6" class="message">${escapeHtml(state.errors.runs)}</td></tr>`;
    return;
  }
  body.innerHTML = state.runs.map((run) => `
    <tr>
      <td>${escapeHtml(run.run_id || "")}</td>
      <td>${escapeHtml(run.started_at || run.start_time || "")}</td>
      <td>${escapeHtml(run.query || run.queries_executed || "")}</td>
      <td>${escapeHtml(String(run.candidate_count ?? run.candidates_found ?? ""))}</td>
      <td>${escapeHtml(String(run.enriched_count ?? run.vendors_enriched ?? ""))}</td>
      <td>${escapeHtml(String(run.dropped_count ?? run.vendors_dropped ?? ""))}</td>
    </tr>
  `).join("") || '<tr><td colspan="6" class="message">No pipeline run snapshots found.</td></tr>';
}

function renderFailureState(message) {
  const failureMarkup = `<tr><td colspan="6" class="message">${escapeHtml(message)}</td></tr>`;
  const candidatesBody = document.getElementById("candidates-body");
  const vendorsBody = document.getElementById("vendors-body");
  const runsBody = document.getElementById("runs-body");
  if (candidatesBody) {
    candidatesBody.innerHTML = failureMarkup;
  }
  if (vendorsBody) {
    vendorsBody.innerHTML = failureMarkup;
  }
  if (runsBody) {
    runsBody.innerHTML = failureMarkup;
  }
}

function formatApiError(payload) {
  if (!payload || !payload.error) {
    return "";
  }
  const detail = payload.detail ? ` ${payload.detail}` : "";
  return `Data unavailable: ${payload.error}.${detail}`.trim();
}

async function handleVendorAction(event) {
  const button = event.currentTarget;
  const action = button.dataset.action;
  const vendor = button.dataset.vendor;
  if (!action || !vendor) {
    return;
  }

  button.disabled = true;
  try {
    await fetchJson(`/admin/vendor/${action}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({vendor}),
    });
    const vendors = await fetchJson("/admin/vendors");
    state.vendors = vendors.items || [];
    renderVendors();
  } catch (error) {
    window.alert(`Admin action failed: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function formatList(values) {
  return Array.isArray(values) ? values.join(", ") : String(values || "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
