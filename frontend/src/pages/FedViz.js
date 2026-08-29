import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import { FLConvergenceChart } from '../components/Charts';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbNetwork,
  TbCpu,
  TbRefresh,
  TbServer,
  TbSchool
} from 'react-icons/tb';

export default function FedViz() {
  const [rounds, setRounds] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [training, setTraining] = useState(false);
  const [alert, setAlert] = useState(null);

  const fetchData = () => {
    Promise.all([skillService.getFLRounds(), skillService.getFLNodes()])
      .then(([roundsRes, nodesRes]) => {
        setRounds(roundsRes.rounds || []);
        setNodes(nodesRes.institutions || []);
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
    } catch (err) {
      setAlert({
        type: 'error',
        message: err.response?.data?.error || 'Failed to simulate federated learning round.',
      });
    } finally {
      setTraining(false);
    }
  };

  const latestRound = rounds[rounds.length - 1];

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-heading text-2xl font-bold text-white">
                Federated Learning Visualizer
              </h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent-500/15 text-accent-300 border border-accent-400/30">
                Flower Engine
              </span>
            </div>
            <p className="text-white/50 text-sm mt-1">
              Decentralized skill gap models trained on institutional partitions without centralizing student resumes.
            </p>
          </div>

          <button
            onClick={handleTriggerRound}
            disabled={training}
            className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 max-w-xs shadow-glow disabled:opacity-40"
          >
            <TbRefresh className={`w-4 h-4 ${training ? 'animate-spin' : ''}`} />
            <span>{training ? 'Aggregating Nodes...' : 'Simulate FL Round'}</span>
          </button>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* Privacy Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Total Rounds Executed</span>
            <p className="font-heading text-2xl font-bold text-white mt-1">
              {rounds.length}
            </p>
          </div>

          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Global Model Accuracy</span>
            <p className="font-heading text-2xl font-bold text-accent-400 mt-1">
              {latestRound ? Math.round(latestRound.global_accuracy * 100) : 78}%
            </p>
          </div>

          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Differential Privacy</span>
            <p className="font-heading text-2xl font-bold text-emerald-400 mt-1">
              ε = 0.85
            </p>
            <p className="text-[10px] text-white/40">Gaussian noise added</p>
          </div>

          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Active Institutional Nodes</span>
            <p className="font-heading text-2xl font-bold text-teal-400 mt-1">
              {nodes.length || 4}
            </p>
          </div>
        </div>

        {/* Architecture Topology Visualizer */}
        <div className="glass p-6 rounded-3xl relative overflow-hidden space-y-6">
          <div className="flex items-center space-x-2">
            <TbNetwork className="w-5 h-5 text-accent-400" />
            <h3 className="font-heading font-semibold text-white text-base">
              Decentralized Topology & Local Nodes
            </h3>
          </div>

          {/* Central Coordinator */}
          <div className="max-w-md mx-auto surface p-4 rounded-2xl border-accent-400/40 text-center space-y-1 shadow-glow">
            <div className="w-10 h-10 mx-auto rounded-xl bg-accent-500/20 text-accent-300 flex items-center justify-center mb-1">
              <TbServer className="w-5 h-5" />
            </div>
            <h4 className="text-sm font-semibold text-white">Central Aggregation Coordinator</h4>
            <p className="text-[11px] text-white/50">
              Executes <span className="font-mono text-accent-300">PrivacyPreservingFedAvg</span> · Only weight tensors aggregated
            </p>
          </div>

          {/* Connected College Nodes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
            {nodes.map((node) => (
              <div key={node.id} className="surface p-4 rounded-xl border border-base-700 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-lg bg-base-700 text-white/80 flex items-center justify-center">
                    <TbSchool className="w-4 h-4" />
                  </div>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                </div>
                <div>
                  <h5 className="text-xs font-semibold text-white">{node.name}</h5>
                  <p className="text-[10px] text-white/40 font-mono mt-0.5">
                    Partition: {node.id}
                  </p>
                </div>
                <div className="pt-2 border-t border-base-800 flex justify-between text-[11px] text-white/50">
                  <span>Samples:</span>
                  <span className="font-mono text-accent-300">{node.samples}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Global Model Convergence Chart */}
        <div className="glass p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TbCpu className="w-5 h-5 text-accent-400" />
              <h3 className="font-heading font-semibold text-white text-base">
                Global Accuracy Convergence Curve
              </h3>
            </div>
            <span className="text-xs font-mono text-white/40">
              Across Federated Rounds
            </span>
          </div>

          <div className="pt-2">
            <FLConvergenceChart rounds={rounds} />
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
