import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import { FLConvergenceChart } from '../components/Charts';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbNetwork,
  TbCpu,
  TbRefresh,
  TbSchool,
  TbShieldCheck,
  TbLock,
  TbGitMerge,
  TbChartDots,
  TbLayersLinked
} from 'react-icons/tb';

export default function FedViz() {
  const [rounds, setRounds] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [training, setTraining] = useState(false);
  const [alert, setAlert] = useState(null);
  const [selectedRound, setSelectedRound] = useState(null);
  const [roundDetails, setRoundDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [showPrivacyArchitecture, setShowPrivacyArchitecture] = useState(false);
  const [showComparison, setShowComparison] = useState(false);

  const fetchData = () => {
    Promise.all([skillService.getFLRounds(), skillService.getFLNodes()])
      .then(([roundsRes, nodesRes]) => {
        const roundList = roundsRes.rounds || [];
        setRounds(roundList);
        setNodes(nodesRes.institutions || []);
        if (roundList.length > 0 && !selectedRound) {
          handleSelectRound(roundList[roundList.length - 1].round_number);
        }
      })
      .catch(() => {
        setAlert({ type: 'error', message: 'Failed to load federated learning telemetry.' });
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTriggerRound = async () => {
    setTraining(true);
    setAlert(null);
    try {
      const res = await skillService.triggerFLRound();
      setAlert({
        type: 'success',
        message: `Round ${res.data.round_number} converged! Global Accuracy: ${Math.round(res.data.global_accuracy * 100)}% with Differential Privacy.`,
      });
      fetchData();
      handleSelectRound(res.data.round_number);
    } catch (err) {
      setAlert({
        type: 'error',
        message: err.response?.data?.error || 'Failed to simulate federated learning round.',
      });
    } finally {
      setTraining(false);
    }
  };

  const handleSelectRound = async (roundNumber) => {
    setSelectedRound(roundNumber);
    setLoadingDetails(true);
    try {
      const details = await skillService.getFLRoundDetails(roundNumber);
      setRoundDetails(details);
    } catch {
      setRoundDetails(null);
    } finally {
      setLoadingDetails(false);
    }
  };

  const latestRound = rounds[rounds.length - 1];
  const currentAccuracy = latestRound ? Math.round(latestRound.global_accuracy * 100) : 78;
  const currentLoss = latestRound?.global_loss ?? 0.22;
  const currentEpsilon = latestRound?.privacy_epsilon ?? 0.85;

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-heading text-2xl font-bold text-white">
                Federated Learning Center
              </h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent-500/15 text-accent-300 border border-accent-400/30">
                Flower Engine · FedAvg
              </span>
            </div>
            <p className="text-white/50 text-sm mt-1">
              Collaborative multi-institutional career intelligence with mathematical Differential Privacy guarantees.
            </p>
          </div>

          <button
            onClick={handleTriggerRound}
            disabled={training}
            className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 shadow-glow disabled:opacity-40"
          >
            <TbRefresh className={`w-4 h-4 ${training ? 'animate-spin' : ''}`} />
            <span>{training ? 'Aggregating Nodes...' : 'Simulate Collaborative Round'}</span>
          </button>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* Top Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="glass p-4 rounded-2xl">
            <span className="text-white/40 text-xs font-mono">Total Rounds</span>
            <p className="font-heading text-3xl font-bold text-white mt-1">
              {rounds.length}
            </p>
            <p className="text-[11px] text-accent-300 mt-1">Completed Cycles</p>
          </div>

          <div className="glass p-4 rounded-2xl">
            <span className="text-white/40 text-xs font-mono">Global Accuracy</span>
            <p className="font-heading text-3xl font-bold text-accent-400 mt-1">
              {currentAccuracy}%
            </p>
            <p className="text-[11px] text-white/40 mt-1">FedAvg Unified Model</p>
          </div>

          <div className="glass p-4 rounded-2xl">
            <span className="text-white/40 text-xs font-mono">Optimization Loss</span>
            <p className="font-heading text-3xl font-bold text-teal-300 mt-1">
              {currentLoss}
            </p>
            <p className="text-[11px] text-white/40 mt-1">Validation Loss Score</p>
          </div>

          <div className="glass p-4 rounded-2xl">
            <span className="text-white/40 text-xs font-mono">Differential Privacy</span>
            <p className="font-heading text-3xl font-bold text-emerald-400 mt-1">
              ε = {currentEpsilon}
            </p>
            <p className="text-[11px] text-white/40 mt-1">δ = 1e-5 (Gaussian Noise)</p>
          </div>
        </div>

        {/* Privacy Architecture Pipeline: Progressive Disclosure */}
        <div className="glass p-5 rounded-2xl border border-accent-400/30 space-y-3 transition-all duration-300">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-xl bg-accent-500/15 text-accent-300 flex items-center justify-center border border-accent-400/20">
                <TbLock className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-heading text-sm font-bold text-white">
                  Privacy-by-Design Architecture Layer
                </h3>
                <p className="text-[11px] text-white/40">
                  Mathematical Differential Privacy & on-premise compute guarantees
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowPrivacyArchitecture(!showPrivacyArchitecture)}
              className="text-xs px-3 py-1.5 rounded-xl surface border border-base-700 text-accent-300 hover:text-white transition-all"
            >
              {showPrivacyArchitecture ? 'Hide Layer Details ▲' : 'View Layer Details ▼'}
            </button>
          </div>

          {showPrivacyArchitecture && (
            <div className="space-y-3 animate-slide-up pt-3 border-t border-base-800">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                <div className="surface p-3.5 rounded-xl border border-base-700/80 space-y-1">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">01. Local Data</span>
                  <p className="font-semibold text-white">Raw Resumes Stay On-Campus</p>
                  <p className="text-white/50 text-[11px] leading-relaxed">
                    Student academic and skill records never leave the participating college server.
                  </p>
                </div>

                <div className="surface p-3.5 rounded-xl border border-base-700/80 space-y-1">
                  <span className="text-[10px] font-mono text-accent-400 uppercase tracking-wider">02. Gradient Weights</span>
                  <p className="font-semibold text-white">Model Updates Only</p>
                  <p className="text-white/50 text-[11px] leading-relaxed">
                    Only numerical weight tensors and biases are shared with the Flower aggregator.
                  </p>
                </div>

                <div className="surface p-3.5 rounded-xl border border-base-700/80 space-y-1">
                  <span className="text-[10px] font-mono text-teal-400 uppercase tracking-wider">03. FedAvg Coordinator</span>
                  <p className="font-semibold text-white">Sample-Weighted Fusion</p>
                  <p className="text-white/50 text-[11px] leading-relaxed">
                    Weights from all campus nodes are combined using sample-weighted Federated Averaging.
                  </p>
                </div>

                <div className="surface p-3.5 rounded-xl border border-base-700/80 space-y-1">
                  <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider">04. Differential Privacy</span>
                  <p className="font-semibold text-white">Noise Perturbation</p>
                  <p className="text-white/50 text-[11px] leading-relaxed">
                    Calibrated noise prevents membership inference or individual skill reconstruction.
                  </p>
                </div>
              </div>

              <div className="p-3 bg-base-950/80 rounded-xl border border-base-800 text-[11px] text-white/60 flex items-start space-x-2">
                <TbShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <p>
                  <span className="text-white font-medium">Research Privacy Guarantee:</span>{' '}
                  Federated Learning reduces the need to transfer raw training data; additional privacy mechanisms such as Differential Privacy provide stronger mathematical protection.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Network Overview: Participating Institutional Nodes */}
        <div className="glass p-6 rounded-3xl space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TbNetwork className="w-5 h-5 text-accent-400" />
              <h3 className="font-heading font-semibold text-white text-base">
                Participating Institutional Nodes ({nodes.length || 4})
              </h3>
            </div>
            <span className="text-xs font-mono text-emerald-400 flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>4 Nodes Synchronized</span>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {nodes.map((node) => (
              <div key={node.id} className="surface p-4 rounded-2xl border border-base-700/80 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xl bg-accent-500/10 text-accent-300 flex items-center justify-center border border-accent-400/20">
                    <TbSchool className="w-5 h-5" />
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                    Active
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-bold text-white">{node.name}</h4>
                  <p className="text-[11px] text-white/40 font-mono mt-0.5">ID: {node.id}</p>
                </div>

                <div className="space-y-1.5 pt-2 border-t border-base-800 text-xs">
                  <div className="flex justify-between text-white/60">
                    <span>Local Student Samples:</span>
                    <span className="font-mono text-white font-semibold">{node.samples}</span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Training Status:</span>
                    <span className="text-emerald-400">SGD Local</span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Data Privacy:</span>
                    <span className="text-accent-300 font-mono text-[11px]">On-Premise</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Global Convergence Curve & Round History Tracker */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Convergence Chart */}
          <div className="glass p-6 rounded-2xl space-y-4 lg:col-span-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <TbCpu className="w-5 h-5 text-accent-400" />
                <h3 className="font-heading font-semibold text-white text-base">
                  Model Convergence Curve (FedAvg)
                </h3>
              </div>
              <span className="text-xs font-mono text-white/40">Across Federated Rounds</span>
            </div>

            <div className="pt-2">
              <FLConvergenceChart rounds={rounds} />
            </div>
          </div>

          {/* Interactive Round Tracker Selector */}
          <div className="glass p-6 rounded-2xl space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <TbChartDots className="w-5 h-5 text-teal-400" />
                <h3 className="font-heading font-semibold text-white text-base">
                  Federated Round History
                </h3>
              </div>
              <p className="text-xs text-white/50 mb-3">
                Select any round to inspect its parameter aggregation:
              </p>

              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {rounds.map((r) => {
                  const isSelected = selectedRound === r.round_number;
                  return (
                    <button
                      key={r.round_number}
                      onClick={() => handleSelectRound(r.round_number)}
                      className={`w-full p-3 rounded-xl border text-left text-xs transition-all flex items-center justify-between ${
                        isSelected
                          ? 'bg-accent-500/20 border-accent-400 text-white shadow-glow'
                          : 'surface border-base-700 text-white/70 hover:text-white hover:border-base-600'
                      }`}
                    >
                      <div>
                        <span className="font-bold text-sm">Round #{r.round_number}</span>
                        <p className="text-[10px] text-white/40 font-mono mt-0.5">
                          {r.aggregation_status || 'Converged (FedAvg + DP)'}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-accent-300">
                          {Math.round(r.global_accuracy * 100)}%
                        </span>
                        <p className="text-[10px] text-white/40">Accuracy</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="text-[11px] text-white/40 border-t border-base-800 pt-3">
              Total {rounds.length} rounds logged across 4 campus partitions.
            </div>
          </div>
        </div>

        {/* Selected Round Detail Inspector Modal / Drawer */}
        {loadingDetails ? (
          <div className="glass p-8 rounded-3xl text-center text-white/50 text-xs flex items-center justify-center space-x-2">
            <div className="w-4 h-4 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
            <span>Fetching telemetry for Round #{selectedRound}...</span>
          </div>
        ) : roundDetails && (
          <div className="glass p-6 rounded-3xl border border-accent-400/40 space-y-5 animate-fade-in">
            <div className="flex items-center justify-between border-b border-base-800 pb-3">
              <div className="flex items-center space-x-2">
                <TbGitMerge className="w-5 h-5 text-accent-400" />
                <h3 className="font-heading text-lg font-bold text-white">
                  Telemetry Details: Round #{roundDetails.round_number}
                </h3>
              </div>
              <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {roundDetails.aggregation_status}
              </span>
            </div>

            {/* Aggregated Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="surface p-3 rounded-xl">
                <span className="text-white/40 font-mono">Global Accuracy</span>
                <p className="font-heading text-xl font-bold text-accent-300 mt-0.5">
                  {Math.round(roundDetails.global_accuracy * 100)}%
                </p>
              </div>
              <div className="surface p-3 rounded-xl">
                <span className="text-white/40 font-mono">Global Loss</span>
                <p className="font-heading text-xl font-bold text-teal-300 mt-0.5">
                  {roundDetails.global_loss}
                </p>
              </div>
              <div className="surface p-3 rounded-xl">
                <span className="text-white/40 font-mono">Clients Aggregated</span>
                <p className="font-heading text-xl font-bold text-white mt-0.5">
                  {roundDetails.participating_clients_count} Nodes
                </p>
              </div>
              <div className="surface p-3 rounded-xl">
                <span className="text-white/40 font-mono">Privacy Budget</span>
                <p className="font-heading text-xl font-bold text-emerald-400 mt-0.5">
                  ε = {roundDetails.privacy_guarantee?.epsilon}
                </p>
              </div>
            </div>

            {/* Participating Nodes Table */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-white/70">
                Participating Institutional Clients in this Round:
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-base-800 text-white/40 font-mono">
                      <th className="py-2 px-2">Institution Node</th>
                      <th className="py-2 px-2">Partition ID</th>
                      <th className="py-2 px-2">Local Samples</th>
                      <th className="py-2 px-2">Local Accuracy</th>
                      <th className="py-2 px-2">Transmission</th>
                      <th className="py-2 px-2">Raw Data Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-base-800/60 text-white/80">
                    {roundDetails.nodes?.map((n) => (
                      <tr key={n.partition_id}>
                        <td className="py-2.5 px-2 font-medium text-white">{n.institution_name}</td>
                        <td className="py-2.5 px-2 font-mono text-white/50">{n.partition_id}</td>
                        <td className="py-2.5 px-2 font-mono">{n.local_samples}</td>
                        <td className="py-2.5 px-2 font-mono text-accent-300">
                          {Math.round(n.local_accuracy * 100)}%
                        </td>
                        <td className="py-2.5 px-2 text-emerald-400/80">{n.transmission}</td>
                        <td className="py-2.5 px-2 font-mono text-teal-300">{n.raw_data_retention}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 5-Step Pipeline Flow */}
            <div className="space-y-2 pt-2 border-t border-base-800">
              <h4 className="text-xs font-semibold text-white/70">
                End-to-End Aggregation Workflow:
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-[11px]">
                {roundDetails.pipeline_steps?.map((step) => (
                  <div key={step.step} className="surface p-2.5 rounded-xl border border-base-700/60 space-y-1">
                    <span className="font-mono text-accent-400 font-bold">Step {step.step}</span>
                    <p className="font-semibold text-white">{step.name}</p>
                    <p className="text-white/40 leading-snug">{step.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Centralized vs Federated Learning Educational Comparison: Progressive Disclosure */}
        <div className="glass p-5 rounded-2xl border border-base-700/80 space-y-3 transition-all duration-300">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-xl bg-teal-500/15 text-teal-300 flex items-center justify-center border border-teal-500/20">
                <TbLayersLinked className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-heading text-sm font-bold text-white">
                  Centralized Learning vs. Federated Learning
                </h3>
                <p className="text-[11px] text-white/40">
                  Data exposure risk vs. institutional privacy preservation comparison
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowComparison(!showComparison)}
              className="text-xs px-3 py-1.5 rounded-xl surface border border-base-700 text-teal-300 hover:text-white transition-all"
            >
              {showComparison ? 'Hide Comparison ▲' : 'View Comparison ▼'}
            </button>
          </div>

          {showComparison && (
            <div className="animate-slide-up pt-3 border-t border-base-800">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Centralized Card */}
                <div className="surface p-4 rounded-xl border border-rose-500/30 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono uppercase text-rose-400 font-bold">Traditional Approach</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 text-rose-300 border border-rose-500/20">
                      Centralized Training
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white">Central Data Aggregation</h4>
                  <p className="text-xs text-white/60 leading-relaxed">
                    Raw student resumes, academic grades, and personal identifiers from all universities are transmitted over the Internet and deposited into a single cloud database.
                  </p>
                  <div className="bg-base-950/80 p-2.5 rounded-lg border border-base-800 text-[11px] text-rose-300/80 space-y-1">
                    <p>⚠ Vulnerable to central database leaks and privacy breaches.</p>
                    <p>⚠ Conflicts with FERPA, GDPR, and institutional data sovereignty.</p>
                    <p>⚠ Universities are often legally forbidden from pooling student transcripts.</p>
                  </div>
                </div>

                {/* Federated Card */}
                <div className="surface p-4 rounded-xl border border-emerald-500/40 space-y-2.5 shadow-glow">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono uppercase text-emerald-400 font-bold">SkillBridge Architecture</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                      Federated Learning
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white">Decentralized Collaborative Intelligence</h4>
                  <p className="text-xs text-white/60 leading-relaxed">
                    Each institution trains models on its own local compute. Only mathematical model weight vectors are exchanged with the Flower server using FedAvg and Differential Privacy.
                  </p>
                  <div className="bg-base-950/80 p-2.5 rounded-lg border border-base-800 text-[11px] text-emerald-300/90 space-y-1">
                    <p>✓ Raw student resumes never leave campus servers.</p>
                    <p>✓ Mathematical Differential Privacy (ε = {currentEpsilon}) prevents reconstruction.</p>
                    <p>✓ All campuses collaboratively gain a smarter career recommendation model.</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
