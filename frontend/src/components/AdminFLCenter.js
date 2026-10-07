import React, { useState, useEffect } from 'react';
import { FLConvergenceChart } from './Charts';
import AlertBanner from './AlertBanner';
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
  TbLayersLinked,
  TbInfoCircle,
  TbDatabase
} from 'react-icons/tb';

export default function AdminFLCenter() {
  const [rounds, setRounds] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [training, setTraining] = useState(false);
  const [alert, setAlert] = useState(null);
  const [selectedRound, setSelectedRound] = useState(null);
  const [roundDetails, setRoundDetails] = useState(null);
  const [activeTab, setActiveTab] = useState('pipeline'); // 'pipeline' | 'nodes' | 'rounds' | 'comparison'

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
      .catch((err) => {
        setAlert({
          type: 'error',
          message: err.response?.data?.error || 'Failed to load federated learning telemetry.',
        });
      });
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTriggerRound = async () => {
    setTraining(true);
    setAlert(null);
    try {
      const res = await skillService.triggerFLRound();
      setAlert({
        type: 'success',
        message: `Federated Round ${res.data.round_number} converged! Global Accuracy: ${Math.round(res.data.global_accuracy * 100)}% with Differential Privacy.`,
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
    try {
      const details = await skillService.getFLRoundDetails(roundNumber);
      setRoundDetails(details);
    } catch {
      setRoundDetails(null);
    }
  };

  const latestRound = rounds[rounds.length - 1];
  const currentAccuracy = latestRound ? Math.round(latestRound.global_accuracy * 100) : 78;
  const currentLoss = latestRound?.global_loss ?? 0.22;
  const currentEpsilon = latestRound?.privacy_epsilon ?? 0.85;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-3xl bg-slate-900/60 border border-slate-800">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
              Federated Learning Center
            </h1>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              Flower Engine · FedAvg
            </span>
          </div>
          <p className="text-cyan-400 font-medium text-xs mt-1">
            Privacy-Preserving Institutional Intelligence
          </p>
          <p className="text-slate-400 text-xs mt-0.5 max-w-2xl">
            Decentralized career readiness model synchronization across collegiate partitions. Raw student records never leave campus premises.
          </p>
        </div>

        <button
          onClick={handleTriggerRound}
          disabled={training}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs flex items-center justify-center space-x-2 shadow-lg shadow-cyan-950 disabled:opacity-40 transition-all"
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

      {/* Primary Telemetry Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-slate-400 text-xs font-mono">Total Rounds</span>
          <p className="font-heading text-3xl font-bold text-white mt-1">
            {rounds.length}
          </p>
          <p className="text-[11px] text-cyan-400 mt-1">Synchronized Cycles</p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-slate-400 text-xs font-mono">Global Accuracy</span>
          <p className="font-heading text-3xl font-bold text-cyan-300 mt-1">
            {currentAccuracy}%
          </p>
          <p className="text-[11px] text-slate-400 mt-1">FedAvg Unified Model</p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-slate-400 text-xs font-mono">Optimization Loss</span>
          <p className="font-heading text-3xl font-bold text-blue-300 mt-1">
            {currentLoss}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Validation Holdout Score</p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-slate-400 text-xs font-mono">Differential Privacy</span>
          <p className="font-heading text-3xl font-bold text-emerald-400 mt-1">
            ε = {currentEpsilon}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">δ = 1e-5 (Gaussian Noise)</p>
        </div>
      </div>

      {/* Internal Sub-View Switcher */}
      <div className="flex border-b border-slate-800 space-x-6 text-xs font-medium">
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`pb-3 transition-colors ${activeTab === 'pipeline' ? 'text-cyan-400 border-b-2 border-cyan-400 font-semibold' : 'text-slate-400 hover:text-white'}`}
        >
          Architecture & Privacy Pipeline
        </button>
        <button
          onClick={() => setActiveTab('nodes')}
          className={`pb-3 transition-colors ${activeTab === 'nodes' ? 'text-cyan-400 border-b-2 border-cyan-400 font-semibold' : 'text-slate-400 hover:text-white'}`}
        >
          Participating Institutional Nodes ({nodes.length})
        </button>
        <button
          onClick={() => setActiveTab('rounds')}
          className={`pb-3 transition-colors ${activeTab === 'rounds' ? 'text-cyan-400 border-b-2 border-cyan-400 font-semibold' : 'text-slate-400 hover:text-white'}`}
        >
          Round Telemetry & Convergence
        </button>
        <button
          onClick={() => setActiveTab('comparison')}
          className={`pb-3 transition-colors ${activeTab === 'comparison' ? 'text-cyan-400 border-b-2 border-cyan-400 font-semibold' : 'text-slate-400 hover:text-white'}`}
        >
          Centralized vs. Federated Analysis
        </button>
      </div>

      {/* TAB 1: ARCHITECTURE & PRIVACY PIPELINE */}
      {activeTab === 'pipeline' && (
        <div className="space-y-6 animate-slide-up">
          {/* FL Architecture Flowchart */}
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading text-base font-bold text-white flex items-center space-x-2">
                  <TbNetwork className="w-5 h-5 text-cyan-400" />
                  <span>Decentralized Architecture Flow</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  How student competency data flows securely from campus partitions to global intelligence
                </p>
              </div>
              <span className="text-[10px] font-mono px-3 py-1 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                Data Sovereignty: 100% On-Campus
              </span>
            </div>

            {/* Visual Node-to-Server Flow Diagram */}
            <div className="p-5 rounded-2xl bg-[#060a14] border border-slate-800/80">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
                {/* Stage 1: Institutions & Local Data */}
                <div className="p-4 rounded-xl bg-slate-900/90 border border-cyan-500/30 space-y-2">
                  <div className="flex items-center space-x-2 text-cyan-300">
                    <TbSchool className="w-4 h-4" />
                    <span className="font-semibold text-xs">Participating Nodes</span>
                  </div>
                  <div className="space-y-1 text-[11px] text-slate-400 font-mono">
                    <p>• Institution Alpha</p>
                    <p>• Institution Beta</p>
                    <p>• Institution Gamma</p>
                    <p>• Institution Delta</p>
                  </div>
                  <div className="p-2 rounded bg-emerald-950/40 border border-emerald-500/30 text-[10px] text-emerald-300 font-semibold text-center">
                    RAW STUDENT DATA STAYS LOCAL
                  </div>
                </div>

                {/* Stage 2: Local SGD Training */}
                <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-blue-300">
                    <TbCpu className="w-4 h-4" />
                    <span className="font-semibold text-xs">Local Training</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Colleges execute on-premise SGDClassifier fits over 10 competency dimensions (Python, SQL, ML, etc.).
                  </p>
                  <div className="text-[10px] text-slate-400 font-mono">
                    Output: Weight tensors (W, b)
                  </div>
                </div>

                {/* Stage 3: Privacy Layer & FedAvg */}
                <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-purple-300">
                    <TbLock className="w-4 h-4" />
                    <span className="font-semibold text-xs">Differential Privacy</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    L2 norm clipping bounds gradient sensitivity (C = 1.0). Gaussian perturbation noise added.
                  </p>
                  <div className="text-[10px] text-purple-300 font-mono">
                    Noise Mechanism: Gaussian
                  </div>
                </div>

                {/* Stage 4: Global Model Broadcast */}
                <div className="p-4 rounded-xl bg-slate-900/90 border border-emerald-500/30 space-y-2">
                  <div className="flex items-center space-x-2 text-emerald-300">
                    <TbGitMerge className="w-4 h-4" />
                    <span className="font-semibold text-xs">FedAvg Aggregator</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Server computes sample-weighted parameter fusion and broadcasts synchronized weights.
                  </p>
                  <div className="text-[10px] text-emerald-300 font-mono">
                    Sync: Global Career Model
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center space-x-2 text-emerald-400 font-mono text-[11px]">
                  <TbShieldCheck className="w-4 h-4" />
                  <span>Mathematical Guarantee: Resumes and raw scores are never uploaded to the central server.</span>
                </div>
                <span className="text-[11px] font-mono text-cyan-400">Flower NumPyClient Protocol</span>
              </div>
            </div>

            {/* Differential Privacy Mathematics */}
            <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-white">
                  <TbLock className="w-4 h-4 text-cyan-400" />
                  <h4 className="font-semibold text-xs">Configured Differential Privacy Bounds</h4>
                </div>
                <span className="text-[10px] font-mono text-cyan-400">ε = {currentEpsilon} | δ = 1e-5</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Federated Learning reduces the need to transfer raw training data. Differential Privacy provides an additional privacy protection layer by bounding the influence of any single student vector on the aggregated weights.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1">
                <div className="p-3 rounded-xl bg-[#070b14] border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono">Gradient Clipping (C)</span>
                  <p className="font-mono text-sm text-cyan-300 font-semibold mt-0.5">1.0 (L2 Norm)</p>
                  <p className="text-[10px] text-slate-400 mt-1">Bounds local client sensitivity</p>
                </div>
                <div className="p-3 rounded-xl bg-[#070b14] border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono">Noise Multiplier (σ)</span>
                  <p className="font-mono text-sm text-purple-300 font-semibold mt-0.5">0.05 Calibrated</p>
                  <p className="text-[10px] text-slate-400 mt-1">Gaussian perturbation scale</p>
                </div>
                <div className="p-3 rounded-xl bg-[#070b14] border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-mono">Target Delta (δ)</span>
                  <p className="font-mono text-sm text-emerald-300 font-semibold mt-0.5">1.0e-5</p>
                  <p className="text-[10px] text-slate-400 mt-1">Upper bound failure probability</p>
                </div>
              </div>
            </div>

            {/* SkillBridge Project Research Context */}
            <div className="p-5 rounded-2xl bg-cyan-950/20 border border-cyan-500/30 space-y-2">
              <h4 className="font-heading text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center space-x-1.5">
                <TbInfoCircle className="w-4 h-4" />
                <span>Research Contribution to SkillBridge</span>
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                Students generate skill profiles and complete verification quizzes at their universities. Rather than transmitting sensitive academic transcripts and resumes to a central authority, each university acts as an FL node. Model updates are synthesized using <strong className="text-white">PrivacyPreservingFedAvg</strong>, providing universally smarter career recommendations across institutions while preserving student privacy.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: PARTICIPATING INSTITUTIONAL NODES */}
      {activeTab === 'nodes' && (
        <div className="space-y-6 animate-slide-up">
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading text-base font-bold text-white flex items-center space-x-2">
                  <TbSchool className="w-5 h-5 text-cyan-400" />
                  <span>Institutional Node Cluster</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Actual participating university partitions and local compute telemetry
                </p>
              </div>
              <span className="text-xs font-mono text-emerald-400">4 / 4 Nodes Connected</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              {nodes.map((node, index) => (
                <div key={node.id} className="p-4 rounded-2xl bg-[#060a14] border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-500/30 flex items-center justify-center text-cyan-300 font-bold text-xs">
                        {String.fromCharCode(65 + index)}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">{node.name}</p>
                        <p className="text-[10px] text-slate-400 font-mono">{node.id}</p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono">
                      Synchronized
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/80">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Local Partition</span>
                      <span className="text-white font-mono font-medium">{node.samples} student records</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Training Status</span>
                      <span className="text-cyan-300 font-mono font-medium">Local SGD Ready</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Active Round</span>
                      <span className="text-white font-mono font-medium">Round #{rounds.length || 1}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Data Sovereignty</span>
                      <span className="text-emerald-400 font-mono font-medium">Local On-Prem</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ROUND TELEMETRY & CONVERGENCE */}
      {activeTab === 'rounds' && (
        <div className="space-y-6 animate-slide-up">
          {/* Convergence Chart */}
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="font-heading text-base font-bold text-white flex items-center space-x-2">
              <TbChartDots className="w-5 h-5 text-cyan-400" />
              <span>Multi-Round Convergence Trajectory</span>
            </h3>
            <p className="text-xs text-slate-400">
              Evolution of global model accuracy across decentralized aggregation rounds
            </p>
            <div className="pt-2">
              <FLConvergenceChart rounds={rounds} />
            </div>
          </div>

          {/* Historical Rounds Table */}
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-heading text-base font-bold text-white flex items-center space-x-2">
                <TbLayersLinked className="w-5 h-5 text-blue-400" />
                <span>Federated Round Logs (Real Database Telemetry)</span>
              </h3>
              <span className="text-xs text-slate-400 font-mono">{rounds.length} Total Rounds</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-[10px] font-mono uppercase text-slate-400">
                    <th className="py-2.5 px-3">Round</th>
                    <th className="py-2.5 px-3">Global Accuracy</th>
                    <th className="py-2.5 px-3">Loss</th>
                    <th className="py-2.5 px-3">Privacy Epsilon</th>
                    <th className="py-2.5 px-3">Aggregation Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {rounds.slice().reverse().map((r) => (
                    <tr
                      key={r.round_number}
                      className={`hover:bg-slate-800/40 transition-colors ${selectedRound === r.round_number ? 'bg-cyan-950/30' : ''}`}
                    >
                      <td className="py-2.5 px-3 font-bold text-white">
                        Round #{r.round_number}
                      </td>
                      <td className="py-2.5 px-3 text-cyan-300">
                        {Math.round(r.global_accuracy * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {r.global_loss}
                      </td>
                      <td className="py-2.5 px-3 text-emerald-400">
                        ε = {r.privacy_epsilon}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        Converged (FedAvg + DP)
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => handleSelectRound(r.round_number)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 text-[11px]"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Selected Round Granular Telemetry */}
            {roundDetails && (
              <div className="p-4 rounded-2xl bg-[#060a14] border border-cyan-500/30 space-y-3 pt-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-xs text-white">
                    Telemetry for Round #{roundDetails.round_number}
                  </h4>
                  <span className="text-[10px] font-mono text-cyan-400">
                    Strategy: {roundDetails.aggregation_strategy}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
                  {roundDetails.nodes?.map((node) => (
                    <div key={node.partition_id} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-white font-medium">{node.institution_name}</span>
                        <span className="text-cyan-300 font-mono">Acc: {Math.round(node.local_accuracy * 100)}%</span>
                      </div>
                      <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
                        <span>{node.local_samples} local vectors</span>
                        <span className="text-emerald-400">{node.raw_data_retention}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: CENTRALIZED VS FEDERATED COMPARISON */}
      {activeTab === 'comparison' && (
        <div className="space-y-6 animate-slide-up">
          <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-5">
            <div>
              <h3 className="font-heading text-base font-bold text-white flex items-center space-x-2">
                <TbGitMerge className="w-5 h-5 text-purple-400" />
                <span>Centralized vs. Federated Learning Comparison</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Technical rationale for why Federated Learning was chosen for the SkillBridge platform
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Centralized Model */}
              <div className="p-5 rounded-2xl bg-[#060a14] border border-rose-500/30 space-y-4">
                <div className="flex items-center space-x-2 text-rose-400">
                  <TbDatabase className="w-5 h-5" />
                  <h4 className="font-bold text-sm">Centralized Architecture (Legacy)</h4>
                </div>

                <div className="space-y-2 text-xs text-slate-400 leading-relaxed">
                  <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1">
                    <p>Colleges A, B, C, D</p>
                    <p className="text-rose-400">  ↓ Uploads Raw Resumes</p>
                    <p>Central Cloud Server</p>
                    <p className="text-slate-400">  ↓ Centralized Training</p>
                    <p>Monolithic Model</p>
                  </div>
                  <p className="text-rose-300 font-medium">Drawbacks:</p>
                  <p>• High privacy and data liability risks.</p>
                  <p>• Single point of regulatory failure under FERPA / GDPR.</p>
                  <p>• Institutions unwilling to pool raw proprietary student records.</p>
                </div>
              </div>

              {/* Federated Model */}
              <div className="p-5 rounded-2xl bg-[#060a14] border border-emerald-500/40 space-y-4">
                <div className="flex items-center space-x-2 text-emerald-400">
                  <TbNetwork className="w-5 h-5" />
                  <h4 className="font-bold text-sm">Federated Architecture (SkillBridge)</h4>
                </div>

                <div className="space-y-2 text-xs text-slate-400 leading-relaxed">
                  <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 font-mono text-[11px] text-emerald-300 space-y-1">
                    <p>Colleges A, B, C, D (Local Training)</p>
                    <p className="text-cyan-400">  ↓ Uploads Model Weights (W, b)</p>
                    <p>Flower FedAvg Aggregator (+ Differential Privacy)</p>
                    <p className="text-emerald-400">  ↓ Broadcasts Global Model</p>
                    <p>Collaborative Career Intelligence</p>
                  </div>
                  <p className="text-emerald-300 font-medium">Benefits:</p>
                  <p>• Raw student records remain 100% on-campus.</p>
                  <p>• Mathematical Differential Privacy bounds data leakage.</p>
                  <p>• Colleges collaboratively gain macro job-market intelligence.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
