// Validate Wood's TUNG-MOD/1 container without executing its Lua.
export const MAX_CATALOG_PACKAGE_BYTES = 4 * 1024 * 1024;

export function readPackage(base64) {
  if (typeof base64 !== "string" || !base64 ||
      base64.length > Math.ceil(MAX_CATALOG_PACKAGE_BYTES / 3) * 4 ||
      !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(base64)) {
    throw new Error("Choose a valid .tungmod package, no larger than 4 MiB for catalog uploads.");
  }
  const bytes = Buffer.from(base64, "base64");
  if (bytes.length > MAX_CATALOG_PACKAGE_BYTES) throw new Error("Catalog packages must be at most 4 MiB.");
  const magic = Buffer.from("TUNG-MOD/1\n");
  if (!bytes.subarray(0, magic.length).equals(magic)) throw new Error("Unsupported .tungmod format. Build it with Wood Mod Packager.");
  let offset = magic.length;
  function length(label, max) {
    const end = bytes.indexOf(10, offset);
    if (end < 0 || end - offset > 10) throw new Error(`Invalid ${label} length.`);
    const text = bytes.subarray(offset, end).toString("latin1");
    if (!/^\d+$/.test(text)) throw new Error(`Invalid ${label} length.`);
    offset = end + 1;
    const value = Number(text);
    if (value > max) throw new Error(`Package ${label} is too large.`);
    return value;
  }
  const metadataLength = length("metadata", 8192);
  const sourceLength = length("source", 1024 * 1024);
  const iconLength = length("icon", 4 * 1024 * 1024);
  if (!sourceLength || offset + metadataLength + sourceLength + iconLength !== bytes.length) {
    throw new Error("The package is empty, truncated, or has trailing data.");
  }
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const metadataText = decoder.decode(bytes.subarray(offset, offset + metadataLength));
  offset += metadataLength;
  decoder.decode(bytes.subarray(offset, offset + sourceLength));
  offset += sourceLength;
  const limits = { id: 40, name: 80, version: 40, author: 60, description: 500 };
  const metadata = Object.create(null);
  for (const line of metadataText.split("\n").filter(Boolean)) {
    const match = /^([A-Za-z0-9_]+)=(.*)$/.exec(line);
    if (!match || !Object.hasOwn(limits, match[1]) || Object.hasOwn(metadata, match[1]) ||
        !match[2] || Buffer.byteLength(match[2], "utf8") > limits[match[1]] || match[2].includes("\r")) {
      throw new Error("Invalid .tungmod metadata.");
    }
    metadata[match[1]] = match[2];
  }
  if (Object.keys(metadata).length !== 5 || !/^[a-z0-9][a-z0-9_-]*$/.test(metadata.id)) {
    throw new Error("The package must contain all five metadata fields and a safe ID.");
  }
  if (iconLength) {
    const icon = bytes.subarray(offset);
    if (icon.length < 24 || !icon.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) ||
        icon.readUInt32BE(8) !== 13 || icon.subarray(12, 16).toString("ascii") !== "IHDR") {
      throw new Error("Invalid package PNG icon.");
    }
    const width = icon.readUInt32BE(16), height = icon.readUInt32BE(20);
    if (!width || !height || width > 2048 || height > 2048 || width * height > 4 * 1024 * 1024) {
      throw new Error("Package PNG icon dimensions exceed Wood's limits.");
    }
  }
  return { bytes, metadata };
}
