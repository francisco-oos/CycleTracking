"use strict";
// MVP: el token sólo se mantiene en memoria. No se guarda en localStorage.
const $ = (id) => document.getElementById(id);
let token = null;
let selected = null;
let me = null;
let words = {};

const dictionary = (key) => words[key] || key;
function showStatus(message) { $("status").textContent = message; }
function setText(id, value) { $(id).textContent = value; }
function clear(id) { $(id).replaceChildren(); }
function addText(parent, tag, value, className) {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  parent.appendChild(element);
  return element;
}
async function request(path, options = {}) {
  const headers = {"Content-Type": "application/json", ...(options.headers || {})};
  if (token) headers.Authorization = "Bearer " + token;
  const response = await fetch(path, {...options, headers});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) { token = null; me = null; $("login-panel").hidden = false; $("work-panel").hidden = true; }
    throw Error((data.detail && data.detail.code) || "HTTP_" + response.status);
  }
  return data;
}
async function switchLanguage() {
  try {
    const lang = $("language").value;
    words = await request("/api/v1/i18n/" + encodeURIComponent(lang));
    document.documentElement.lang = lang;
    setText("title", dictionary("app.title"));
    setText("alpha", dictionary("notice.alpha"));
    setText("label-user", dictionary("auth.username"));
    setText("label-password", dictionary("auth.password"));
    setText("login-btn", dictionary("auth.login"));
    setText("logout-btn", dictionary("auth.logout"));
    setText("asset-title", dictionary("asset.title"));
    $("search").placeholder = dictionary("asset.search");
    $("search").setAttribute("aria-label", dictionary("asset.search"));
    setText("search-btn", dictionary("asset.search"));
    setText("create-title", dictionary("action.register"));
    setText("create-btn", dictionary("action.register"));
    setText("detail-title", dictionary("asset.dossier"));
    setText("observe-title", dictionary("action.observe"));
    setText("observe-btn", dictionary("action.observe"));
    setText("decision-title", dictionary("action.confirm"));
    setText("decision-btn", dictionary("action.confirm"));
    $("equipment-type").placeholder = dictionary("asset.type");
    $("identifier").placeholder = dictionary("asset.serial");
    $("observation-note").placeholder = dictionary("action.reason");
    $("decision-note").placeholder = dictionary("action.reason");
    for (const option of $("observation-kind").options) option.textContent = dictionary("event." + option.value);
    for (const option of $("decision-status").options) option.textContent = dictionary("status." + option.value);
    if (me) setText("identity", me.username + " · " + dictionary("role." + me.role));
    if (selected) await loadDetails(selected.id);
  } catch (e) { showStatus(e.message); }
}
function showAccount() {
  $("login-panel").hidden = true;
  $("work-panel").hidden = false;
  $("create-panel").hidden = me.role !== "INVENTARIOS";
  setText("identity", me.username + " · " + dictionary("role." + me.role));
}
async function loadAssets() {
  const assets = await request("/api/v1/assets?q=" + encodeURIComponent($("search").value));
  clear("assets");
  if (!assets.length) addText($("assets"), "li", dictionary("asset.empty"), "muted");
  for (const asset of assets) {
    const li = document.createElement("li");
    const id = asset.identifiers.map((x) => x.kind + ": " + x.value).join(", ");
    const button = addText(li, "button", id + " · " + asset.equipment_type + " · " + dictionary("status." + asset.status));
    button.type = "button";
    button.addEventListener("click", () => loadDetails(asset.id).catch((e) => showStatus(e.message)));
    $("assets").appendChild(li);
  }
}
async function loadDetails(id) {
  const data = await request("/api/v1/assets/" + encodeURIComponent(id));
  selected = data.asset;
  const idText = selected.identifiers.map((x) => x.kind + ": " + x.value).join(", ");
  setText("details", idText + " · " + selected.equipment_type + " · " + dictionary("status." + selected.status) + " · v" + selected.version);
  clear("events");
  for (const ev of data.events) {
    const li = document.createElement("li");
    addText(li, "strong", dictionary("event." + ev.type));
    addText(li, "small", new Date(ev.occurred_at).toLocaleString($("language").value) + " · " + ev.actor_id);
    addText(li, "div", ev.note);
    if (ev.evidence_ref) addText(li, "small", dictionary("asset.evidence") + ": " + ev.evidence_ref);
    $("events").appendChild(li);
  }
  $("observe-form").hidden = !["OPERATIVO", "INVENTARIOS"].includes(me.role);
  $("decision-form").hidden = me.role !== "INVENTARIOS";
}
async function act(event, fn) {
  event.preventDefault();
  const button = event.submitter;
  if (button) button.disabled = true;
  try { await fn(); showStatus(dictionary("action.saved")); }
  catch (e) { showStatus(dictionary("error.generic") + " (" + e.message + ")"); }
  finally { if (button) button.disabled = false; }
}
$("language").addEventListener("change", switchLanguage);
$("login-form").addEventListener("submit", (event) => act(event, async () => {
  const result = await request("/api/v1/auth/login", {method:"POST", body:JSON.stringify({
    username:$("username").value, password:$("password").value
  })});
  $("password").value = "";
  token = result.access_token;
  me = await request("/api/v1/me");
  showAccount();
  await loadAssets();
}));
$("logout-btn").addEventListener("click", async () => {
  try { await request("/api/v1/auth/logout", {method:"POST"}); } catch (_) {}
  token = null; me = null; selected = null;
  $("login-panel").hidden = false; $("work-panel").hidden = true;
});
$("search-form").addEventListener("submit", (event) => act(event, loadAssets));
$("create-form").addEventListener("submit", (event) => act(event, async () => {
  const asset = await request("/api/v1/assets", {method:"POST", body:JSON.stringify({
    equipment_type:$("equipment-type").value, technology:$("technology").value || null,
    identifier_kind:$("identifier-kind").value, identifier:$("identifier").value,
  })});
  $("create-form").reset();
  await loadAssets(); await loadDetails(asset.id);
}));
$("observe-form").addEventListener("submit", (event) => act(event, async () => {
  if (!selected) return;
  await request("/api/v1/assets/" + encodeURIComponent(selected.id) + "/observations", {
    method:"POST", body:JSON.stringify({
      event_id:crypto.randomUUID(), occurred_at:new Date().toISOString(),
      event_type:$("observation-kind").value, note:$("observation-note").value
    })
  });
  $("observation-note").value = "";
  await loadDetails(selected.id); await loadAssets();
}));
$("decision-form").addEventListener("submit", (event) => act(event, async () => {
  if (!selected) return;
  await request("/api/v1/assets/" + encodeURIComponent(selected.id) + "/decisions", {
    method:"POST", body:JSON.stringify({
      event_id:crypto.randomUUID(), occurred_at:new Date().toISOString(),
      new_status:$("decision-status").value, expected_version:selected.version,
      note:$("decision-note").value
    })
  });
  $("decision-note").value = "";
  await loadDetails(selected.id); await loadAssets();
}));
switchLanguage();
