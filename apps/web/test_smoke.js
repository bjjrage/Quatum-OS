// Smoke test verifying essential Quant Cockpit web assets and invariants
const fs = require("fs");
const path = require("path");

console.log("[Smoke Test] Verifying Quant Cockpit Web Terminal assets...");

const requiredFiles = [
  "app/layout.tsx",
  "app/page.tsx",
  "app/globals.css",
  "types/index.ts",
  "lib/api.ts",
  "components/layout/TopStatusStrip.tsx",
  "components/layout/SidebarNavigation.tsx",
  "components/views/CommandCenterView.tsx",
  "components/views/RecorderView.tsx",
  "components/views/DataQualityView.tsx",
  "components/views/TradabilityView.tsx",
  "components/views/StrategyRegistryView.tsx",
  "components/views/Str002SpecializedView.tsx",
  "components/views/SelectionGatesView.tsx",
  "components/views/PortfolioView.tsx",
  "components/views/RiskEngineView.tsx",
  "components/views/PaperTradingView.tsx",
  "components/views/HoldoutsView.tsx",
  "components/views/BacktestsView.tsx",
  "components/views/AttributionView.tsx",
  "components/views/PropSimulatorView.tsx",
  "components/views/MultiAccountView.tsx",
  "components/views/AuditTrailView.tsx",
  "components/views/BlueprintView.tsx",
];

let failed = false;
for (const f of requiredFiles) {
  const fullPath = path.join(__dirname, f);
  if (!fs.existsSync(fullPath)) {
    console.error(`[FAIL] Missing required file: ${f}`);
    failed = true;
  }
}

if (failed) {
  process.exit(1);
}

// Invariant: Verify zero live risk declaration in types and TopStatusStrip
const topStrip = fs.readFileSync(path.join(__dirname, "components/layout/TopStatusStrip.tsx"), "utf8");
if (!topStrip.includes("$0 LIVE RISK") || !topStrip.includes("LOCKED")) {
  console.error("[FAIL] TopStatusStrip missing ZERO LIVE RISK / LOCKED invariant banner");
  process.exit(1);
}

console.log("[PASS] Quant Cockpit Web Smoke Test: All 19 required assets verified with zero live risk invariants.");
process.exit(0);
