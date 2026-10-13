import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(new URL("./mods.js", import.meta.url), "utf8");

class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.className = "";
    this.classList = {
      add: (name) => this.classes.add(name),
      remove: (name) => this.classes.delete(name),
    };
    this.classes = new Set();
    this.textContent = "";
  }

  append(...children) {
    this.children.push(...children);
  }

  replaceChildren(...children) {
    this.children = children;
  }
}

async function renderCatalog(response) {
  const nodes = new Map([
    ["#mod-cards", new Element("div")],
    ["#catalog-status", new Element("p")],
  ]);
  const context = {
    document: {
      querySelector: (selector) => nodes.get(selector),
      createElement: (tagName) => new Element(tagName),
    },
    fetch: async () => response,
    encodeURIComponent,
  };
  vm.runInNewContext(source, context);

  for (let attempt = 0; attempt < 10 && nodes.get("#catalog-status").textContent === "Loading official mods..."; attempt++) {
    await new Promise((resolve) => setImmediate(resolve));
  }
  return nodes;
}

test("an empty online catalog renders only its empty state", async () => {
  const nodes = await renderCatalog({
    ok: true,
    json: async () => ({ mods: [] }),
  });
  const cards = nodes.get("#mod-cards").children;
  assert.equal(cards.length, 1);
  assert.equal(cards[0].className, "catalog-empty");
  assert.equal(cards[0].textContent, "No mods have been published yet.");
  assert.equal(cards[0].children.length, 0);
  assert.equal(nodes.get("#catalog-status").textContent, "No official mods published yet.");
});

test("an unavailable online catalog does not render fallback mod cards", async () => {
  const nodes = await renderCatalog({
    ok: false,
    status: 503,
  });
  const cards = nodes.get("#mod-cards").children;
  assert.equal(cards.length, 1);
  assert.equal(cards[0].className, "catalog-empty");
  assert.equal(cards[0].textContent, "The online catalog is currently unavailable.");
  assert.equal(nodes.get("#catalog-status").classes.has("catalog-error"), true);
});

test("download buttons use the published format, including older Lua releases", async () => {
  const nodes = await renderCatalog({ ok: true, json: async () => ({ mods: [
    { id: "new-mod", name: "New mod", version: "1.0.0", versions: [{ version: "1.0.0", format: "tungmod" }] },
    { id: "old-mod", name: "Old mod", version: "1.0.0", versions: [{ version: "1.0.0" }] },
  ] }) });
  const [packaged, legacy] = nodes.get("#mod-cards").children.map((card) => card.children.at(-1));
  assert.equal(packaged.textContent, "Download .tungmod");
  assert.equal(packaged.download, "new-mod-1.0.0.tungmod");
  assert.equal(legacy.download, "old-mod-1.0.0.lua");
});
