const cards = document.querySelector("#mod-cards");
const statusLine = document.querySelector("#catalog-status");

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function renderMod(mod) {
  const card = element("article", undefined, "mod-card");
  const title = element("h2", mod.name);
  const summary = element("p", mod.summary);
  const description = element("p", mod.description);
  const metadata = element("div", undefined, "mod-meta");
  metadata.append(element("span", `Version ${mod.version}`, "mod-tag"));
  metadata.append(element("span", `By ${mod.author}`, "mod-tag"));
  if (mod.game_version) metadata.append(element("span", `TUNG ${mod.game_version}`, "mod-tag"));
  for (const tag of Array.isArray(mod.tags) ? mod.tags : []) {
    metadata.append(element("span", tag, "mod-tag"));
  }

  const latest = Array.isArray(mod.versions)
    ? mod.versions.find((item) => item.version === mod.version)
    : null;
  let download;
  if (latest) {
    download = element("a", "Download Lua mod", "btn");
    download.href = `/api/mods?id=${encodeURIComponent(mod.id)}&version=${encodeURIComponent(latest.version)}`;
    download.download = `${mod.id}-${latest.version}.lua`;
  }

  card.append(title, summary, description, metadata);
  if (latest?.changelog) card.append(element("p", `Latest changes: ${latest.changelog}`));
  if (download) card.append(download);
  return card;
}

async function loadCatalog() {
  statusLine.classList.remove("catalog-error");
  statusLine.textContent = "Loading official mods...";
  cards.replaceChildren();

  try {
    const response = await fetch("/api/mods", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Online catalog returned HTTP ${response.status}.`);
    const result = await response.json();
    if (!result || !Array.isArray(result.mods)) {
      throw new Error("The online catalog returned an invalid response.");
    }

    if (result.mods.length === 0) {
      cards.append(element("p", "No mods have been published yet.", "catalog-empty"));
      statusLine.textContent = "No official mods published yet.";
      return;
    }

    cards.replaceChildren(...result.mods.map(renderMod));
    statusLine.textContent = `${result.mods.length} official mod${result.mods.length === 1 ? "" : "s"} available`;
  } catch (error) {
    cards.append(element("p", "The online catalog is currently unavailable.", "catalog-empty"));
    statusLine.textContent = `Could not load the online catalog: ${error.message}`;
    statusLine.classList.add("catalog-error");
  }
}

loadCatalog();
