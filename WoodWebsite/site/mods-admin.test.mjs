import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(new URL("./mods-admin.js", import.meta.url), "utf8");

async function publish(name, bytes) {
  let onSubmit, request;
  const form = { addEventListener: (_, callback) => { onSubmit = callback; }, reset() {} };
  const status = { classList: { add() {} } }, button = {};
  class File {
    constructor() { this.name = name; this.size = bytes.length; }
    async arrayBuffer() { return Uint8Array.from(bytes).buffer; }
  }
  const data = new Map([
    ["admin_token", "test-secret"], ["mod_file", new File()],
    ["id", "example"], ["tags", "Utilities"],
  ]);
  vm.runInNewContext(source, {
    document: { querySelector: (selector) => ({ "#publish-form": form, "#publish-status": status, "#publish-submit": button })[selector] },
    File, FormData: class { get(key) { return data.get(key); } },
    Uint8Array, btoa: (value) => Buffer.from(value, "binary").toString("base64"),
    fetch: async (_, options) => {
      request = options;
      return { ok: true, json: async () => ({ mod: { name: "Example", version: "1.0.0" } }) };
    },
  });
  await onSubmit({ preventDefault() {} });
  return { request, status, button };
}

test("curator form submits package bytes intact across encoding chunks", async () => {
  const bytes = Buffer.alloc(70000);
  for (let i = 0; i < bytes.length; i++) bytes[i] = i % 256;
  const { request, button } = await publish("example.tungmod", bytes);
  assert.deepEqual(Buffer.from(JSON.parse(request.body).package_base64, "base64"), bytes);
  assert.equal(JSON.parse(request.body).code, undefined);
  assert.equal(request.headers.Authorization, "Bearer test-secret");
  assert.equal(button.disabled, false);
});

test("curator form requires packages and rejects oversized uploads before sending", async () => {
  for (const [name, bytes] of [["example.lua", Buffer.from("return {}")], ["example.tungmod", Buffer.alloc(4 * 1024 * 1024 + 1)]]) {
    const { request, status } = await publish(name, bytes);
    assert.equal(request, undefined);
    assert.ok(status.textContent);
  }
});
