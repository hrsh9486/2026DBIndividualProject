import type { Catalogue, StaticDataAsset, StaticPayload } from "./types";
import { assertPayload } from "./runtimeGuards";

async function loadJson(path: string, version?: string): Promise<unknown> {
  const url = version ? `${path}?v=${encodeURIComponent(version)}` : path;
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  return response.json();
}

export async function loadCatalogue(): Promise<Catalogue> {
  const value = await loadJson("/data/catalogue.json");
  if (!value || typeof value !== "object" || !("assets" in value) || !("sections" in value)) {
    throw new Error("The static data catalogue is malformed");
  }
  return value as Catalogue;
}

export async function loadStaticAsset(asset: StaticDataAsset): Promise<StaticPayload> {
  const payload = await loadJson(asset.data_path, asset.version);
  assertPayload(payload, asset.schema);
  return payload;
}
