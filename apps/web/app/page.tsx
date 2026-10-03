"use client";

import React, { useState, useEffect, useCallback } from "react";
import { NavTabId, SystemStatus, RecorderStatus, DataQuality, TradabilityMarket, StrategySummary, StrategyDetail, Str002Specialized, PortfolioState, PaperAccount, PropRuleProfileData } from "../types";
import { api } from "../lib/api";
import { TopStatusStrip } from "../components/layout/TopStatusStrip";
import { SidebarNavigation } from "../components/layout/SidebarNavigation";

// Views
import { CommandCenterView } from "../components/views/CommandCenterView";
import { RecorderView } from "../components/views/RecorderView";
import { DataQualityView } from "../components/views/DataQualityView";
import { TradabilityView } from "../components/views/TradabilityView";
import { StrategyRegistryView } from "../components/views/StrategyRegistryView";
import { StrategyDetailView } from "../components/views/StrategyDetailView";
import { Str002SpecializedView } from "../components/views/Str002SpecializedView";
import { ExperimentsView } from "../components/views/ExperimentsView";
import { BacktestsView } from "../components/views/BacktestsView";
import { HoldoutsView } from "../components/views/HoldoutsView";
import { SelectionGatesView } from "../components/views/SelectionGatesView";
import { PortfolioView } from "../components/views/PortfolioView";
import { PaperTradingView } from "../components/views/PaperTradingView";
import { ExecutionView } from "../components/views/ExecutionView";
import { RiskEngineView } from "../components/views/RiskEngineView";
import { EventClustersView } from "../components/views/EventClustersView";
import { CapitalPocketsView } from "../components/views/CapitalPocketsView";
import { PropFirmsView } from "../components/views/PropFirmsView";
import { PropSimulatorView } from "../components/views/PropSimulatorView";
import { MultiAccountView } from "../components/views/MultiAccountView";
import { AttributionView } from "../components/views/AttributionView";
import { AuditTrailView } from "../components/views/AuditTrailView";
import { TestsCiView } from "../components/views/TestsCiView";
import { BlueprintView } from "../components/views/BlueprintView";
import { RegimesView } from "../components/views/RegimesView";
import { ConfigurationView } from "../components/views/ConfigurationView";

export default function QuantCockpitPage() {
  const [activeTab, setActiveTab] = useState<NavTabId>("command-center");
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);

  // Live state
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [recorderStatus, setRecorderStatus] = useState<RecorderStatus | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQuality | null>(null);
  const [tradabilityMarkets, setTradabilityMarkets] = useState<TradabilityMarket[]>([]);
  const [strategies, setStrategies] = useState<StrategySummary[]>([]);
  const [strategyDetail, setStrategyDetail] = useState<StrategyDetail | null>(null);
  const [str002Specialized, setStr002Specialized] = useState<Str002Specialized | null>(null);
  const [experimentsData, setExperimentsData] = useState<any>({ total: 0, experiments: [] });
  const [holdoutsData, setHoldoutsData] = useState<any>(null);
  const [gatesData, setGatesData] = useState<any>({ gates: [] });
  const [portfolioState, setPortfolioState] = useState<PortfolioState | null>(null);
  const [paperAccount, setPaperAccount] = useState<PaperAccount | null>(null);
  const [executionStatus, setExecutionStatus] = useState<any>(null);
  const [riskStatus, setRiskStatus] = useState<any>(null);
  const [pocketsData, setPocketsData] = useState<any>(null);
  const [propProfiles, setPropProfiles] = useState<PropRuleProfileData[]>([]);
  const [regimeData, setRegimeData] = useState<any>(null);

  // Initial & periodic fetch
  const refreshCore = useCallback(async () => {
    try {
      const [sys, rec, dq] = await Promise.all([
        api.getSystemStatus(),
        api.getRecorderStatus(),
        api.getDataQuality(),
      ]);
      if (sys) setSystemStatus(sys);
      if (rec) setRecorderStatus(rec);
      if (dq) setDataQuality(dq);
    } catch (e) {
      console.error("Error refreshing core telemetry:", e);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    refreshCore();
    try {
      const [
        trad,
        strats,
        str002,
        exps,
        holds,
        gts,
        port,
        paper,
        exec,
        risk,
        pockets,
        props,
        regime,
      ] = await Promise.all([
        api.getMarketsTradability(),
        api.getStrategies(),
        api.getStr002Specialized(),
        api.getExperiments(),
        api.getHoldouts(),
        api.getGates(),
        api.getPortfolio(),
        api.getPaperAccount(),
        api.getExecutionStatus(),
        api.getRiskStatus(),
        api.getCapitalPockets(),
        api.getPropProfiles(),
        api.getRegime(),
      ]);

      if (trad?.markets) setTradabilityMarkets(trad.markets);
      if (strats) setStrategies(strats);
      if (str002) setStr002Specialized(str002);
      if (exps) setExperimentsData(exps);
      if (holds) setHoldoutsData(holds);
      if (gts) setGatesData(gts);
      if (port) setPortfolioState(port);
      if (paper) setPaperAccount(paper);
      if (exec) setExecutionStatus(exec);
      if (risk) setRiskStatus(risk);
      if (pockets) setPocketsData(pockets);
      if (props) setPropProfiles(props);
      if (regime) setRegimeData(regime);
    } catch (err) {
      console.error("Error refreshing all data:", err);
    }
  }, [refreshCore]);

  // Initial load
  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshCore, 5000);
    return () => clearInterval(interval);
  }, [refreshAll, refreshCore]);

  // Handle strategy detail selection
  const handleSelectStrategy = async (strategyId: string) => {
    setSelectedStrategyId(strategyId);
    setActiveTab("strategy-detail");
    const detail = await api.getStrategyDetail(strategyId);
    if (detail) setStrategyDetail(detail);
  };

  const handleNavigate = (tab: NavTabId) => {
    setActiveTab(tab);
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-[#0a0b0d] text-[#f0f3f8]">
      {/* 1. TOP OPERATIONAL STATUS STRIP (PINNED) */}
      <TopStatusStrip status={systemStatus} recorder={recorderStatus} onRefresh={refreshAll} />

      {/* 2. BODY LAYOUT: SIDEBAR + MAIN VIEWPORT */}
      <div className="flex flex-1 overflow-hidden">
        {/* SIDEBAR NAVIGATION */}
        <SidebarNavigation
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          unvalidatedStrategiesCount={1}
          failedGatesCount={0}
        />

        {/* SCROLLABLE MAIN CONTENT AREA */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#0a0b0d]">
          <div className="max-w-[1600px] mx-auto pb-16">
            {activeTab === "command-center" && (
              <CommandCenterView
                status={systemStatus}
                recorder={recorderStatus}
                dataQuality={dataQuality}
                onNavigate={handleNavigate}
              />
            )}

            {activeTab === "recorder" && (
              <RecorderView
                recorder={recorderStatus}
                dataQuality={dataQuality}
                onRefresh={refreshCore}
              />
            )}

            {activeTab === "data-quality" && (
              <DataQualityView dataQuality={dataQuality} />
            )}

            {activeTab === "tradability" && (
              <TradabilityView
                markets={tradabilityMarkets}
                onRefresh={refreshAll}
              />
            )}

            {activeTab === "strategy-registry" && (
              <StrategyRegistryView
                strategies={strategies}
                onSelectStrategy={handleSelectStrategy}
                onNavigate={handleNavigate}
              />
            )}

            {activeTab === "strategy-detail" && (
              <StrategyDetailView
                strategy={strategyDetail}
                onBack={() => setActiveTab("strategy-registry")}
              />
            )}

            {activeTab === "str002-specialized" && (
              <Str002SpecializedView data={str002Specialized} />
            )}

            {activeTab === "experiments" && (
              <ExperimentsView
                experiments={experimentsData.experiments || []}
                strategyTrialCounts={experimentsData.strategy_trial_counts}
              />
            )}

            {activeTab === "backtests" && <BacktestsView />}

            {activeTab === "holdouts" && (
              <HoldoutsView holdoutsData={holdoutsData} />
            )}

            {activeTab === "selection-gates" && (
              <SelectionGatesView
                gates={gatesData.gates || []}
                provenanceInvariant={gatesData.provenance_invariant}
              />
            )}

            {activeTab === "portfolio" && (
              <PortfolioView portfolio={portfolioState} />
            )}

            {activeTab === "regimes" && (
              <RegimesView regimeData={regimeData} />
            )}

            {activeTab === "attribution" && <AttributionView />}

            {(activeTab === "paper-trading" ||
              activeTab === "orders-fills" ||
              activeTab === "positions") && (
              <PaperTradingView
                paperAccount={paperAccount}
                onRefresh={refreshAll}
              />
            )}

            {activeTab === "execution" && (
              <ExecutionView executionStatus={executionStatus} />
            )}

            {(activeTab === "risk-engine" || activeTab === "kill-switches") && (
              <RiskEngineView riskStatus={riskStatus} />
            )}

            {activeTab === "event-clusters" && <EventClustersView />}

            {activeTab === "capital-pockets" && (
              <CapitalPocketsView pocketsData={pocketsData} />
            )}

            {activeTab === "prop-firms" && (
              <PropFirmsView profiles={propProfiles} />
            )}

            {activeTab === "prop-simulator" && <PropSimulatorView />}

            {activeTab === "multi-account" && <MultiAccountView />}

            {activeTab === "audit-trail" && <AuditTrailView />}

            {activeTab === "tests-ci" && <TestsCiView />}

            {activeTab === "configuration" && <ConfigurationView />}

            {activeTab === "blueprint" && (
              <BlueprintView onNavigate={handleNavigate} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
