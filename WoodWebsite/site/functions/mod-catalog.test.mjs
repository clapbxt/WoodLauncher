import assert from "node:assert/strict";
import test from "node:test";
import { createHandler } from "./mod-catalog.mjs";
import { MAX_CATALOG_PACKAGE_BYTES } from "./tungmod.mjs";

function testStore() {
  const values = new Map();
  return {
    async get(key, options) {
      const value = values.get(key);
      if (value === undefined) return null;
      return options.type === "json" ? JSON.parse(value) : value;
    },
    async set(key, value) {
      values.set(key, value);
    },
  };
}

const submission = {
  id: "hedge-helper",
  name: "Hedge Helper",
  author: "Wood",
  version: "1.0.0",
  summary: "A route helper for hedge practice.",
  description: "Adds useful hedge practice controls.",
  game_version: "Current Steam release",
  tags: ["Practice"],
  changelog: "Initial release.",
  code: "return { name = 'Hedge Helper' }\n",
};

function packageSubmission(icon = Buffer.alloc(0)) {
  const metadata = Buffer.from(`id=${submission.id}\nname=${submission.name}\nversion=${submission.version}\nauthor=${submission.author}\ndescription=${submission.description}\n`);
  const source = Buffer.from(submission.code);
  const bytes = Buffer.concat([
    Buffer.from(`TUNG-MOD/1\n${metadata.length}\n${source.length}\n${icon.length}\n`),
    metadata, source, icon,
  ]);
  const { code, ...details } = submission;
  return { ...details, package_base64: bytes.toString("base64") };
}

function event(httpMethod, values = {}, headers = {}) {
  return {
    httpMethod,
    headers,
    queryStringParameters: values.query ?? {},
    body: values.body === undefined ? "" : JSON.stringify(values.body),
  };
}

test("catalog is public, mod uploads need the curator token, and downloads return Lua", async () => {
  const store = testStore();
  const handler = createHandler({ openStore: () => store, getAdminToken: () => "secret" });
  const emptyCatalog = await handler(event("GET"));
  assert.equal(emptyCatalog.statusCode, 200);
  assert.deepEqual(JSON.parse(emptyCatalog.body), { mods: [] });
  assert.equal((await handler(event("POST", { body: submission }))).statusCode, 401);

  const uploaded = await handler(event("POST", { body: submission }, { authorization: "Bearer secret" }));
  assert.equal(uploaded.statusCode, 201);
  const list = JSON.parse((await handler(event("GET"))).body);
  assert.equal(list.mods[0].version, "1.0.0");

  const download = await handler(event("GET", { query: { id: "hedge-helper" } }));
  assert.equal(download.statusCode, 200);
  assert.equal(download.body, submission.code);
  assert.match(download.headers["Content-Disposition"], /hedge-helper-1\.0\.0\.lua/);
});

test("catalog rejects duplicate versions, invalid IDs, and oversized Lua", async () => {
  const store = testStore();
  const handler = createHandler({ openStore: () => store, getAdminToken: () => "secret" });
  const headers = { authorization: "Bearer secret" };
  assert.equal((await handler(event("POST", { body: { ...submission, id: "../escape" } }, headers))).statusCode, 400);
  assert.equal((await handler(event("POST", { body: { ...submission, code: "x".repeat(1024 * 1024 + 1) } }, headers))).statusCode, 400);
  assert.equal((await handler(event("POST", { body: submission }, headers))).statusCode, 201);
  assert.equal((await handler(event("POST", { body: submission }, headers))).statusCode, 409);
});

test("packages with icon bytes survive upload/download unchanged and retain their format", async () => {
  const store = testStore();
  const handler = createHandler({ openStore: () => store, getAdminToken: () => "secret" });
  // Minimal header accepted by the runtime's PNG dimension check, plus binary data.
  const icon = Buffer.alloc(28);
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(icon);
  icon.writeUInt32BE(13, 8); icon.write("IHDR", 12);
  icon.writeUInt32BE(32, 16); icon.writeUInt32BE(32, 20);
  icon[24] = 255;
  const packaged = packageSubmission(icon);
  const response = await handler(event("POST", { body: packaged }, { authorization: "Bearer secret" }));
  assert.equal(response.statusCode, 201, response.body);
  assert.equal(JSON.parse(response.body).mod.versions[0].format, "tungmod");
  const download = await handler(event("GET", { query: { id: submission.id } }));
  assert.equal(download.statusCode, 200);
  assert.equal(download.isBase64Encoded, true);
  assert.equal(download.headers["Content-Type"], "application/octet-stream");
  assert.match(download.headers["Content-Disposition"], /\.tungmod"$/);
  assert.equal(download.body, packaged.package_base64);
});

test("invalid packages, mismatched metadata and oversized packages are rejected", async () => {
  const handler = createHandler({ openStore: testStore, getAdminToken: () => "secret" });
  const headers = { authorization: "Bearer secret" };
  const packaged = packageSubmission();
  for (const input of [
    { ...packaged, package_base64: "not base64" },
    { ...packaged, package_base64: Buffer.from("not a package").toString("base64") },
    { ...packaged, id: "different-id" },
    { ...packaged, package_base64: Buffer.from(packaged.package_base64, "base64").subarray(0, -1).toString("base64") },
    { ...packaged, package_base64: Buffer.concat([Buffer.from(packaged.package_base64, "base64"), Buffer.from("extra")]).toString("base64") },
    { ...packaged, package_base64: Buffer.alloc(MAX_CATALOG_PACKAGE_BYTES + 1).toString("base64") },
  ]) {
    assert.equal((await handler(event("POST", { body: input }, headers))).statusCode, 400);
  }
});

test("unconfigured curator uploads fail explicitly", async () => {
  const handler = createHandler({ openStore: testStore, getAdminToken: () => "" });
  const response = await handler(event("POST", { body: submission }));
  assert.equal(response.statusCode, 503);
  assert.match(JSON.parse(response.body).error, /not configured/);
});

test("explicit Netlify Blobs credentials are passed to the store", async () => {
  let calledWith;
  const handler = createHandler({
    getStoreImpl: (...args) => {
      calledWith = args;
      return testStore();
    },
    getAdminToken: () => "secret",
    env: {
      NETLIFY_SITE_ID: "site-id",
      NETLIFY_AUTH_TOKEN: "netlify-token",
    },
  });

  const response = await handler(event("POST", { body: submission }, { authorization: "Bearer secret" }));
  assert.equal(response.statusCode, 201);
  assert.equal(calledWith[0], "official-mod-catalog");
  assert.deepEqual(calledWith[1], { siteID: "site-id", token: "netlify-token" });
});

test("partial Netlify Blobs credentials return an actionable configuration error", async () => {
  const handler = createHandler({
    getStoreImpl: testStore,
    getAdminToken: () => "secret",
    env: { NETLIFY_SITE_ID: "site-id" },
  });
  const originalError = console.error;
  console.error = () => {};
  try {
    const response = await handler(event("GET"));
    assert.equal(response.statusCode, 503);
    assert.match(JSON.parse(response.body).error, /NETLIFY_SITE_ID and NETLIFY_AUTH_TOKEN/);
  } finally {
    console.error = originalError;
  }
});

test("missing automatic Netlify Blobs credentials return setup guidance", async () => {
  const handler = createHandler({
    getStoreImpl: () => {
      throw Object.assign(new Error("Missing store credentials"), { name: "MissingBlobsEnvironmentError" });
    },
    env: {},
  });
  const originalError = console.error;
  console.error = () => {};
  try {
    const response = await handler(event("GET"));
    assert.equal(response.statusCode, 503);
    assert.match(JSON.parse(response.body).error, /configure.*NETLIFY_SITE_ID.*NETLIFY_AUTH_TOKEN/i);
  } finally {
    console.error = originalError;
  }
});
