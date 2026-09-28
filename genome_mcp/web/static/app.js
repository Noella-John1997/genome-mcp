const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let sid = "demo";
const EXAMPLES = ["Am I a carrier for any disease?", "Do I carry anything in BRCA1?", "What is my APOE status?",
  "Is warfarin a concern for me?", "What is rs113993960?", "Give me an overview"];
$("#examples").innerHTML = EXAMPLES.map((q) => `<button class="btn sm" type="button">${esc(q)}</button>`).join("");
$("#examples").onclick = (e) => { if (e.target.tagName === "BUTTON") { $("#q").value = e.target.textContent; ask(); } };

const sigChip = (s) => `<span class="chip ${/pathogenic/i.test(s) && !/drug/i.test(s) ? "bad" : /risk/i.test(s) ? "warn" : "acc"}">${esc(s)}</span>`;
const zygChip = (z) => `<span class="chip">${esc(z)}</span>`;

// ---------- renderers (shared by the dashboard and the Ask answers)
function renderFindings(res) {
  if (!res.findings.length) return `<div class="empty">No pathogenic or risk variants found in the curated set.</div>`;
  return res.findings.map((f) => { const a = f.annotation; return `
    <div class="finding ${a.category === "risk" ? "risk" : ""}">
      <div class="row"><span class="g">${esc(a.gene)}</span>${sigChip(a.significance)}${zygChip(f.zygosity)}<span class="c">${esc(a.rsid)} · ${esc(a.change)}</span></div>
      <p><b>${esc(a.condition)}.</b> ${esc(f.interpretation || "")}</p></div>`; }).join("");
}
function renderApoe(a) {
  return `<div class="apoe">${esc(a.genotype)}</div><p style="margin:6px 0 0">${esc(a.meaning || "")}</p>
    ${(a.assumptions || []).length ? `<p class="muted" style="font-size:13px">${esc(a.assumptions.join("; "))}</p>` : ""}`;
}
function renderPgx(p) {
  return `<table><thead><tr><th>Gene</th><th>Variant</th><th>Copies</th><th>What it means</th></tr></thead><tbody>${
    p.results.map((r) => `<tr><td><b>${esc(r.gene)}</b></td><td class="mono">${esc(r.rsid)}</td>
      <td>${r.copies_of_variant ?? "—"}</td><td>${r.status ? `<span class="chip warn">${esc(r.status)}</span>` :
      (r.copies_of_variant ? esc(r.effect) : `<span class="muted">${esc(r.effect)}</span>`)}</td></tr>`).join("")}</tbody></table>
    <p class="muted" style="font-size:13px">${esc(p.note)}</p>`;
}
function renderVariants(vs) {
  if (!vs.length) return `<div class="empty">No variants carried in this region.</div>`;
  return `<div class="table-wrap"><table><thead><tr><th>Position</th><th>Change</th><th>Type</th><th>Genotype</th><th>Known as</th></tr></thead><tbody>${
    vs.map((v) => `<tr><td class="mono">chr${esc(v.chrom)}:${v.pos.toLocaleString()}</td><td class="mono">${esc(v.ref)} → ${esc(v.alt)}</td>
      <td>${esc(v.type)}</td><td>${zygChip(v.zygosity)}</td>
      <td>${v.annotation ? `${sigChip(v.annotation.significance)} <span class="muted">${esc(v.annotation.condition)}</span>` : `<span class="muted">${esc(v.id === "." ? "not in curated set" : v.id)}</span>`}</td></tr>`).join("")}</tbody></table></div>`;
}
function renderGene(g) {
  if (g.error) return `<div class="banner">${esc(g.error)}</div>`;
  return `<p style="margin:0 0 10px"><b>${esc(g.gene)}</b> <span class="muted">${esc(g.location)}</span><br>${esc(g.why_it_matters)}</p>${renderVariants(g.variants)}`;
}
function renderTiles(s) {
  const t = (k, n) => `<div class="tile"><div class="k">${k}</div><div class="n">${n ?? "—"}</div></div>`;
  return t("Variants", s.variants) + t("Passing filters", s.pass_filter) + t("SNVs", s.by_type.SNV || 0) +
    t("Indels", (s.by_type.insertion || 0) + (s.by_type.deletion || 0)) + t("Ts/Tv", s.ts_tv_ratio) + t("Het / Hom", s.het_hom_ratio);
}
function renderLookup(r) {
  const a = r.annotation;
  const inS = typeof r.in_sample === "string" ? `<span class="muted">${esc(r.in_sample)}</span>` : `${zygChip(r.in_sample.zygosity)} <span class="mono">${esc(r.in_sample.genotype)}</span>`;
  return `<dl class="kv" style="display:grid;grid-template-columns:auto 1fr;gap:6px 14px">
    <dt class="muted">Variant</dt><dd style="margin:0"><b>${esc(r.query)}</b></dd>
    ${a ? `<dt class="muted">Gene</dt><dd style="margin:0">${esc(a.gene)} · ${esc(a.change)}</dd><dt class="muted">Significance</dt><dd style="margin:0">${sigChip(a.significance)} ${esc(a.condition)}</dd>` : `<dt class="muted">Known</dt><dd style="margin:0">Not in the curated set</dd>`}
    <dt class="muted">In this sample</dt><dd style="margin:0">${inS}</dd></dl>`;
}
const RENDER = {
  clinically_relevant: (r) => renderFindings(r), apoe_genotype: renderApoe, pharmacogenomics: (r) => `<div class="table-wrap">${renderPgx(r)}</div>`,
  gene_variants: renderGene, query_region: (r) => renderVariants(r.variants), vcf_summary: (r) => `<div class="tiles">${renderTiles(r)}</div>`,
  lookup_variant: renderLookup, genome_report: (r) => `<pre class="md">${esc(r.markdown)}</pre>`,
};

// ---------- data loading
async function api(path, opts) {
  const r = await fetch(`/api/${sid}${path}`, opts);
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || r.statusText);
  return d;
}
async function load() {
  const o = await api("/overview");
  $("#tiles").innerHTML = renderTiles(o.summary);
  $("#findings").innerHTML = renderFindings(o.findings);
  $("#fnote").textContent = o.findings.interpretation_note;
  $("#apoe").innerHTML = renderApoe(o.apoe);
  $("#pgx").innerHTML = renderPgx(o.pgx);
  $("#disclaimer").textContent = o.disclaimer;
  $("#genes").innerHTML = o.genes.map((g) => `<button class="btn sm" aria-pressed="false" title="${esc(g.note)}" data-g="${esc(g.name)}">${esc(g.name)}</button>`).join("");
  $("#dl").href = `/api/${sid}/report.md`;
  showGene("BRCA1");
}
async function showGene(name) {
  document.querySelectorAll("#genes .btn").forEach((b) => b.setAttribute("aria-pressed", b.dataset.g === name));
  $("#genebox").innerHTML = renderGene(await api(`/gene/${encodeURIComponent(name)}`));
}
$("#genes").onclick = (e) => { if (e.target.dataset.g) showGene(e.target.dataset.g); };

async function ask() {
  const question = $("#q").value.trim(); if (!question) return;
  $("#answer").innerHTML = '<span class="spinner"></span>';
  try {
    const d = await api("/ask", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question})});
    $("#answer").innerHTML = `<div class="trace">MCP tool call → <b>${esc(d.tool)}</b>(${esc(JSON.stringify(d.args))})</div>
      ${(RENDER[d.tool] || ((r) => ""))(d.result)}
      <details class="raw"><summary>Raw tool result (what the AI model receives)</summary><pre>${esc(JSON.stringify(d.result, null, 2))}</pre></details>`;
  } catch (e) { $("#answer").innerHTML = `<div class="banner">${esc(e.message)}</div>`; }
}
$("#askform").onsubmit = (e) => { e.preventDefault(); ask(); };

$("#file").onchange = async () => {
  const f = $("#file").files[0]; if (!f) return;
  $("#upmsg").innerHTML = '<span class="spinner"></span> Reading file…';
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/upload", {method: "POST", body: fd});
  const d = await r.json();
  if (!r.ok) { $("#upmsg").textContent = "Upload failed: " + d.detail; return; }
  sid = d.session_id; $("#who").textContent = `${d.sample} (${d.filename})`;
  $("#upmsg").textContent = "Loaded. Your file is kept for 30 minutes on this server, then deleted.";
  $("#answer").innerHTML = ""; load();
};
$("#demo").onclick = () => { sid = "demo"; $("#who").textContent = "DEMO_SAMPLE (synthetic)"; $("#upmsg").textContent = "Upload only synthetic or public data (e.g. 1000 Genomes). Files are deleted after 30 minutes."; $("#answer").innerHTML = ""; load(); };
load();
