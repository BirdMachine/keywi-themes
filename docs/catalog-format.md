# Catalog format v1

`catalog.json` is UTF-8 JSON. It contains `catalogVersion` (1), a stable catalog `id`, `name`, `description`, `repository` URL and an `entries` array. An app should reject unsupported catalog versions gracefully and keep its last successfully validated catalog cache.

Each entry has:

| Field | Meaning |
| --- | --- |
| `id` | Stable catalog slug, independent of display name |
| `name`, `description`, `author`, `tags` | Display/search metadata |
| `license` | SPDX identifier or source-specific license URL when confirmed; null when unset |
| `version` | Human-readable package version |
| `revision` | Positive integer update counter, increasing within a stable ID |
| `themeDocumentId` | Expected `theme.json` ID; must match the downloaded package |
| `compatibility.themeSchemaVersion` | Theme-document schema required by the package |
| `compatibility.requiredFeatures` | Additional app capabilities; currently empty for defaults, and group styling capabilities for OilSlyck |
| `package.url` | Relative HTTPS-resolved URL of the versioned theme ZIP |
| `package.bytes`, `package.sha256` | Exact download size and SHA-256 integrity check |
| `preview.thumbnail` | Small PNG for the browsing grid |
| `preview.animation` | GIF for the detail page |
| `preview.type` | `rendered-demo`; does not claim a device recording |
| `preview.layout`, `preview.facet`, `preview.geometry` | Conditions used for illustration; not settings to auto-apply |
| `preview.durationMs`, `preview.animationBytes`, `preview.animationSha256` | GIF length, size and integrity check |
| `features` | Background-animation status and key-group/per-key override counts |
| `provenance` | Source type and reference app commit |

All file URLs in this repository are relative to `catalog.json`. A client fetches the index once, then thumbnails as needed; ZIPs are never fetched merely to obtain a preview. Package URLs are immutable per version. A listing can be updated by increasing `revision` and referencing a new versioned file.

SHA-256 verifies bytes against the catalog; it does not independently authenticate a catalog. The initial client should use the official HTTPS catalog URL. A future repository system can add catalog signatures and user-managed sources without changing theme ZIPs.

The importer accepts `theme.json` plus referenced assets under `assets/`. Keep catalog metadata and previews outside that ZIP. This is a content/catalog contract for the upcoming Explore client, not an API already implemented in Keywi.
