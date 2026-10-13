import { timingSafeEqual } from "node:crypto";
import { getStore } from "@netlify/blobs";
import { MAX_CATALOG_PACKAGE_BYTES, readPackage } from "./tungmod.mjs";

const STORE_NAME = "official-mod-catalog";
const CATALOG_KEY = "catalog.json";
const MAX_LUA_BYTES = 1024 * 1024;

function jsonResponse(statusCode, body, headers = {}) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      ...headers,
    },
    body: JSON.stringify(body),
  };
}

function safeEqual(left, right) {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

function validateSubmission(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { error: "Submit a JSON object." };
  }

  let packaged;
  if (value.package_base64 !== undefined) {
    try {
      packaged = readPackage(value.package_base64);
      for (const field of ["id", "name", "author", "version"]) {
        if (value[field] !== packaged.metadata[field]) {
          return { error: `The form ${field} must match the package metadata.` };
        }
      }
    } catch (error) {
      return { error: error.message };
    }
  }
  const fields = [
    ["id", 2, 40],
    ["name", 2, 80],
    ["author", 2, 60],
    ["summary", 10, 180],
    ["description", 10, 2000],
    ["game_version", 1, 80],
    ["changelog", 0, 1000],
  ];
  for (const [field, minimum, maximum] of fields) {
    if (typeof value[field] !== "string") return { error: `Missing ${field}.` };
    const text = value[field].trim();
    if (text.length < minimum || Buffer.byteLength(text, "utf8") > maximum) {
      return { error: `${field} must be ${minimum}-${maximum} characters.` };
    }
    value[field] = text;
  }
  if (!packaged && (typeof value.code !== "string" || !value.code.trim() ||
      Buffer.byteLength(value.code, "utf8") > MAX_LUA_BYTES)) {
    return { error: "Lua source must be non-empty and no larger than 1 MiB." };
  }

  if (!/^[a-z0-9][a-z0-9_-]*$/.test(value.id)) {
    return { error: "ID must start with a lowercase letter or digit and use letters, digits, underscores, or hyphens." };
  }
  if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(value.version)) {
    return { error: "Version must use MAJOR.MINOR.PATCH format." };
  }
  if (!packaged && value.code.includes("\0")) {
    return { error: "The Lua file contains a null byte." };
  }
  if (!Array.isArray(value.tags) || value.tags.length > 5 ||
      value.tags.some((tag) => typeof tag !== "string" || tag.trim().length > 24)) {
    return { error: "Add at most five tags, each 24 characters or shorter." };
  }

  return {
    submission: {
      id: value.id,
      name: value.name,
      author: value.author,
      version: value.version,
      summary: value.summary,
      description: value.description,
      game_version: value.game_version,
      tags: [...new Set(value.tags.map((tag) => tag.trim()).filter(Boolean))],
      changelog: value.changelog,
      code: value.code,
      package: packaged?.bytes,
    },
  };
}

function openCatalogStore(getStoreImpl, env) {
  const siteID = env.NETLIFY_SITE_ID || env.SITE_ID;
  const token = env.NETLIFY_AUTH_TOKEN;
  if (siteID || token) {
    if (!siteID || !token) {
      throw new Error("Set both NETLIFY_SITE_ID and NETLIFY_AUTH_TOKEN to configure Netlify Blobs.");
    }
    return getStoreImpl(STORE_NAME, { siteID, token });
  }
  return getStoreImpl(STORE_NAME);
}

export function createHandler({
  openStore,
  getStoreImpl = getStore,
  getAdminToken = () => process.env.MOD_ADMIN_TOKEN,
  env = process.env,
} = {}) {
  const storeOpener = openStore ?? (() => openCatalogStore(getStoreImpl, env));
  return async function handler(event) {
    if (event.httpMethod === "OPTIONS") {
      return { statusCode: 204, headers: { Allow: "GET, POST, OPTIONS" }, body: "" };
    }
    if (event.httpMethod !== "GET" && event.httpMethod !== "POST") {
      return jsonResponse(405, { error: "Use GET to browse/download or POST to submit." }, { Allow: "GET, POST, OPTIONS" });
    }

    try {
      const store = storeOpener();
      if (event.httpMethod === "GET") {
        const catalog = (await store.get(CATALOG_KEY, { type: "json" })) ?? [];
        const id = event.queryStringParameters?.id;
        if (!id) return jsonResponse(200, { mods: catalog });
        const mod = catalog.find((item) => item.id === id);
        if (!mod) return jsonResponse(404, { error: "Mod not found." });

        const version = event.queryStringParameters?.version ?? mod.version;
        const release = mod.versions.find((item) => item.version === version);
        if (!release) return jsonResponse(404, { error: "Mod version not found." });
        const packaged = release.format === "tungmod";
        const code = await store.get(release.key, { type: packaged ? "arrayBuffer" : "text" });
        if (code == null || (!packaged && typeof code !== "string")) return jsonResponse(404, { error: "Mod file is unavailable." });
        return {
          statusCode: 200,
          headers: {
            "Content-Type": packaged ? "application/octet-stream" : "text/plain; charset=utf-8",
            "Content-Disposition": `attachment; filename="${mod.id}-${release.version}.${packaged ? "tungmod" : "lua"}"`,
            "Cache-Control": "public, max-age=300",
            "X-Content-Type-Options": "nosniff",
          },
          body: packaged ? Buffer.from(code).toString("base64") : code,
          ...(packaged ? { isBase64Encoded: true } : {}),
        };
      }

      const configuredToken = getAdminToken();
      if (!configuredToken) return jsonResponse(503, { error: "The curator upload service is not configured yet." });
      const authorization = event.headers?.authorization ?? event.headers?.Authorization ?? "";
      const providedToken = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
      if (!providedToken || !safeEqual(providedToken, configuredToken)) {
        return jsonResponse(401, { error: "Curator token is missing or invalid." });
      }
      if (Buffer.byteLength(event.body ?? "", "utf8") > Math.ceil(MAX_CATALOG_PACKAGE_BYTES / 3) * 4 + 64 * 1024) {
        return jsonResponse(413, { error: "Submission is too large; catalog packages must be no larger than 4 MiB." });
      }

      let input;
      try {
        input = JSON.parse(event.body ?? "");
      } catch {
        return jsonResponse(400, { error: "Submission must contain valid JSON." });
      }
      const checked = validateSubmission(input);
      if (checked.error) return jsonResponse(400, { error: checked.error });

      const catalog = (await store.get(CATALOG_KEY, { type: "json" })) ?? [];
      const submission = checked.submission;
      const existingIndex = catalog.findIndex((item) => item.id === submission.id);
      const existing = existingIndex < 0 ? null : catalog[existingIndex];
      if (existing?.versions.some((release) => release.version === submission.version)) {
        return jsonResponse(409, { error: "That mod version is already published. Use a new version number." });
      }

      const publishedAt = new Date().toISOString();
      const format = submission.package ? "tungmod" : "lua";
      const key = `mods/${submission.id}/${submission.version}.${format}`;
      await store.set(key, submission.package ?? submission.code);
      const release = { version: submission.version, published_at: publishedAt, changelog: submission.changelog, key, format };
      const mod = {
        id: submission.id,
        name: submission.name,
        author: submission.author,
        version: submission.version,
        summary: submission.summary,
        description: submission.description,
        game_version: submission.game_version,
        tags: submission.tags,
        published_at: publishedAt,
        versions: [...(existing?.versions ?? []), release],
      };
      if (existingIndex < 0) catalog.push(mod);
      else catalog[existingIndex] = mod;
      catalog.sort((a, b) => a.name.localeCompare(b.name));
      await store.set(CATALOG_KEY, JSON.stringify(catalog));
      return jsonResponse(201, { mod });
    } catch (error) {
      console.error("Official mod catalog request failed:", error);
      const message = error instanceof Error ? error.message : String(error);
      if ((error && typeof error === "object" && error.name === "MissingBlobsEnvironmentError") ||
          message.includes("NETLIFY_SITE_ID and NETLIFY_AUTH_TOKEN")) {
        return jsonResponse(503, {
          error: "Netlify Blobs is not configured. Set NETLIFY_SITE_ID and NETLIFY_AUTH_TOKEN in Netlify environment variables, then redeploy.",
        });
      }
      return jsonResponse(500, { error: "The catalog request failed. Check the Netlify function logs and try again." });
    }
  };
}

export const handler = createHandler();
export default { handler };
