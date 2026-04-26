// CI runs:
// - npm audit --audit-level=moderate (blocks merges on advisories)
// - syft generates SBOM, uploaded as build artifact
// - cosign verifies signed releases of native modules
// - WebView restricted to https://my.app, JS bridge audited per release
export {};
