"""Export a slim vendor review dataset and HTML report for operators."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.extraction.vendor_intel import VendorIntelligence
from services.persistence import supabase_client

if TYPE_CHECKING:
    from supabase import Client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VENDOR_REVIEW_DATASET_PATH = PROJECT_ROOT / "outputs" / "vendor_review_dataset.json"
DEFAULT_VENDOR_REVIEW_HTML_PATH = PROJECT_ROOT / "outputs" / "vendor_review.html"


def export_vendor_review_artifacts(
    *,
    dataset_output_path: Path | None = None,
    html_output_path: Path | None = None,
    client: "Client | None" = None,
    fallback_profiles: list[VendorIntelligence] | None = None,
) -> list[dict[str, Any]]:
    """Write a slim JSON dataset plus a self-contained HTML review report."""
    dataset = build_vendor_review_dataset(client=client, fallback_profiles=fallback_profiles)
    dataset_output_path = dataset_output_path or DEFAULT_VENDOR_REVIEW_DATASET_PATH
    html_output_path = html_output_path or DEFAULT_VENDOR_REVIEW_HTML_PATH
    write_vendor_review_dataset(dataset, dataset_output_path)
    write_vendor_review_html(dataset, html_output_path)
    return dataset


def build_vendor_review_dataset(
    client: "Client | None" = None,
    *,
    fallback_profiles: list[VendorIntelligence] | None = None,
) -> list[dict[str, Any]]:
    """Return a review-friendly vendor subset from Supabase or current-run profiles."""
    rows: list[dict[str, Any]]
    if client is not None or supabase_client.is_configured():
        try:
            rows = supabase_client.list_vendor_profiles(limit=500, client=client)
        except Exception:
            rows = []
    else:
        rows = []

    if not rows and fallback_profiles:
        rows = [_profile_to_vendor_row(profile) for profile in fallback_profiles]

    dataset = [_normalize_vendor_row(row) for row in rows]
    return sorted(dataset, key=lambda item: item["vendor_name"].lower())


def write_vendor_review_dataset(dataset: list[dict[str, Any]], output_path: Path) -> None:
    """Write the JSON review dataset to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")


def write_vendor_review_html(dataset: list[dict[str, Any]], output_path: Path) -> None:
    """Write a self-contained HTML report for quick visual review."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_vendor_review_html(dataset), encoding="utf-8")


def _normalize_vendor_row(row: dict[str, Any]) -> dict[str, Any]:
    mission = _string_value(row.get("mission"))
    usp = _string_value(row.get("usp"))
    use_cases = _list_value(row.get("use_cases"))
    pricing = _list_value(row.get("pricing"))
    evidence_urls = _list_value(row.get("evidence_urls"))
    lifecycle_stages = _list_value(row.get("lifecycle_stages"))

    return {
        "vendor_name": _string_value(row.get("name") or row.get("vendor_name")),
        "website": _string_value(row.get("website")),
        "source": _string_value(row.get("source")),
        "mission_summary": _summary_text(mission or usp),
        "use_case_summary": ", ".join(use_cases[:3]),
        "pricing_summary": ", ".join(pricing[:3]),
        "lifecycle_stages": lifecycle_stages,
        "directory_category": _string_value(row.get("directory_category")),
        "directory_fit": _string_value(row.get("directory_fit")),
        "include_in_directory": _bool_value(row.get("include_in_directory")),
        "confidence": _string_value(row.get("confidence")),
        "free_trial": _bool_value(row.get("free_trial")),
        "soc2": _bool_value(row.get("soc2")),
        "founded": _string_value(row.get("founded")),
        "evidence_url_count": len(evidence_urls),
        "last_updated": _string_value(row.get("last_updated")),
    }


def _profile_to_vendor_row(profile: VendorIntelligence) -> dict[str, Any]:
    return {
        "name": profile.vendor_name,
        "website": profile.website,
        "source": profile.source,
        "mission": profile.mission,
        "usp": profile.usp,
        "use_cases": profile.use_cases,
        "pricing": profile.pricing,
        "lifecycle_stages": profile.lifecycle_stages,
        "directory_category": profile.directory_category,
        "directory_fit": profile.directory_fit,
        "include_in_directory": profile.include_in_directory,
        "confidence": profile.confidence,
        "free_trial": profile.free_trial,
        "soc2": profile.soc2,
        "founded": profile.founded,
        "evidence_urls": profile.evidence_urls,
        "last_updated": "",
    }


def _render_vendor_review_html(dataset: list[dict[str, Any]]) -> str:
    payload = json.dumps(dataset)
    total_vendors = len(dataset)
    included_count = sum(1 for vendor in dataset if vendor.get("include_in_directory") is True)
    high_fit_count = sum(1 for vendor in dataset if vendor.get("directory_fit") == "high")

    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vendor Review Report | SuccessByCS</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3efe6;
      --panel: #fffaf1;
      --ink: #1f1b16;
      --muted: #6d655b;
      --line: #d7cdbf;
      --accent: #145a4a;
      --accent-soft: #d9efe8;
      --warn: #8b5e1a;
      --warn-soft: #f8ead1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Manrope", Arial, sans-serif;
      background: linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    .hero {{
      display: grid;
      gap: 16px;
      grid-template-columns: 2fr 1fr;
      align-items: start;
      margin-bottom: 28px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 18px 40px rgba(31, 27, 22, 0.06);
    }}
    h1, h2 {{ margin: 0 0 8px; }}
    p {{ margin: 0; line-height: 1.55; }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .metric-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .metric strong {{ display: block; font-size: 28px; margin-bottom: 4px; }}
    .toolbar {{
      display: grid;
      gap: 12px;
      grid-template-columns: 2fr 1fr 1fr;
      margin-bottom: 16px;
    }}
    input, select {{
      width: 100%;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fff;
      font: inherit;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border-radius: 16px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      background: #fbf7f0;
    }}
    tr:last-child td {{ border-bottom: none; }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .pill-warn {{
      background: var(--warn-soft);
      color: var(--warn);
    }}
    .muted {{ color: var(--muted); }}
    .empty {{
      padding: 28px;
      text-align: center;
      color: var(--muted);
      background: #fff;
      border: 1px dashed var(--line);
      border-radius: 16px;
    }}
    a {{ color: var(--accent); }}
    @media (max-width: 900px) {{
      .hero, .metric-grid, .toolbar {{ grid-template-columns: 1fr; }}
      table, thead, tbody, tr, th, td {{ display: block; }}
      thead {{ display: none; }}
      tr {{
        border-bottom: 1px solid var(--line);
        padding: 10px 0;
      }}
      td {{
        border-bottom: none;
        padding: 6px 0;
      }}
      td::before {{
        content: attr(data-label);
        display: block;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 2px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <article class="panel">
        <p class="eyebrow">Visual review output</p>
        <h1>Vendor review report</h1>
        <p>This report is generated by the pipeline run so operators can quickly inspect the vendor subset synced from Supabase or the current run fallback without opening a raw Google Sheet dump.</p>
      </article>
      <aside class="panel metric-grid">
        <div class="metric">
          <span class="eyebrow">Vendors</span>
          <strong>__TOTAL_VENDORS__</strong>
          <p class="muted">Rows available for review.</p>
        </div>
        <div class="metric">
          <span class="eyebrow">Included</span>
          <strong>__INCLUDED_COUNT__</strong>
          <p class="muted">Marked for directory inclusion.</p>
        </div>
        <div class="metric">
          <span class="eyebrow">High fit</span>
          <strong>__HIGH_FIT_COUNT__</strong>
          <p class="muted">High-fit vendors in the current review set.</p>
        </div>
      </aside>
    </section>

    <section class="panel">
      <div class="toolbar">
        <input id="search" type="search" placeholder="Search vendor name or website">
        <select id="include-filter">
          <option value="">All inclusion states</option>
          <option value="true">Included</option>
          <option value="false">Excluded</option>
        </select>
        <select id="category-filter">
          <option value="">All categories</option>
        </select>
      </div>
      <div id="table-container"></div>
    </section>
  </main>

  <script id="vendor-review-data" type="application/json">__PAYLOAD__</script>
  <script>
    const dataset = JSON.parse(document.getElementById("vendor-review-data").textContent);
    const tableContainer = document.getElementById("table-container");
    const searchInput = document.getElementById("search");
    const includeFilter = document.getElementById("include-filter");
    const categoryFilter = document.getElementById("category-filter");

    function populateCategoryFilter() {{
      const categories = Array.from(new Set(dataset.map((vendor) => vendor.directory_category).filter(Boolean))).sort();
      categories.forEach((category) => categoryFilter.appendChild(new Option(category, category)));
    }}

    function render() {{
      const searchValue = searchInput.value.trim().toLowerCase();
      const includeValue = includeFilter.value;
      const categoryValue = categoryFilter.value;

      const rows = dataset.filter((vendor) => {{
        const matchesSearch = !searchValue
          || String(vendor.vendor_name || "").toLowerCase().includes(searchValue)
          || String(vendor.website || "").toLowerCase().includes(searchValue);
        const matchesInclude = !includeValue || String(vendor.include_in_directory) === includeValue;
        const matchesCategory = !categoryValue || vendor.directory_category === categoryValue;
        return matchesSearch && matchesInclude && matchesCategory;
      }});

      if (!rows.length) {{
        tableContainer.innerHTML = '<div class="empty">No vendors match the current filters.</div>';
        return;
      }}

      tableContainer.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Lifecycle</th>
              <th>Category</th>
              <th>Fit</th>
              <th>Include</th>
              <th>Summary</th>
              <th>Pricing</th>
              <th>Signals</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((vendor) => `
              <tr>
                <td data-label="Vendor">
                  <strong>${escapeHtml(vendor.vendor_name || "")}</strong><br>
                  <a href="${escapeAttribute(vendor.website || "#")}" target="_blank" rel="noreferrer">${escapeHtml(vendor.website || "")}</a>
                </td>
                <td data-label="Lifecycle">${escapeHtml((vendor.lifecycle_stages || []).join(", ") || "Not mapped")}</td>
                <td data-label="Category">${escapeHtml(vendor.directory_category || "uncategorized")}</td>
                <td data-label="Fit"><span class="pill ${vendor.directory_fit === "low" ? "pill-warn" : ""}">${escapeHtml(vendor.directory_fit || "unscored")}</span></td>
                <td data-label="Include">${escapeHtml(vendor.include_in_directory === true ? "true" : vendor.include_in_directory === false ? "false" : "")}</td>
                <td data-label="Summary">${escapeHtml(vendor.mission_summary || "No summary captured.")}</td>
                <td data-label="Pricing">${escapeHtml(vendor.pricing_summary || "No pricing captured.")}</td>
                <td data-label="Signals">
                  Confidence: ${escapeHtml(vendor.confidence || "n/a")}<br>
                  Free trial: ${escapeHtml(formatBoolean(vendor.free_trial))}<br>
                  SOC2: ${escapeHtml(formatBoolean(vendor.soc2))}<br>
                  Evidence URLs: ${escapeHtml(String(vendor.evidence_url_count || 0))}
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }}

    function formatBoolean(value) {{
      if (value === true) return "Yes";
      if (value === false) return "No";
      return "Unknown";
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }}

    function escapeAttribute(value) {{
      return escapeHtml(value);
    }}

    populateCategoryFilter();
    render();
    searchInput.addEventListener("input", render);
    includeFilter.addEventListener("change", render);
    categoryFilter.addEventListener("change", render);
  </script>
</body>
</html>
"""
    return (
        template
        .replace("__TOTAL_VENDORS__", str(total_vendors))
        .replace("__INCLUDED_COUNT__", str(included_count))
        .replace("__HIGH_FIT_COUNT__", str(high_fit_count))
        .replace("__PAYLOAD__", escape(payload))
        .replace("{{", "{")
        .replace("}}", "}")
    )


def _string_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        separators_normalized = value.replace("\n", "|").replace(",", "|")
        return [segment.strip() for segment in separators_normalized.split("|") if segment.strip()]
    return []


def _bool_value(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


def _summary_text(text: str, *, max_chars: int = 140) -> str:
    cleaned = " ".join(text.split()).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."
