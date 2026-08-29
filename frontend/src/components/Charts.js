import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Radar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
);

export function ReadinessRadar({ labels = [], userScores = [], targetScores = [] }) {
  const data = {
    labels: labels.length > 0 ? labels : ['Python', 'SQL', 'ML', 'Web', 'Algorithms', 'Data Eng'],
    datasets: [
      {
        label: 'Your Competency',
        data: userScores.length > 0 ? userScores : [85, 70, 60, 45, 75, 50],
        backgroundColor: 'rgba(45, 212, 191, 0.25)',
        borderColor: '#2dd4bf',
        borderWidth: 2,
        pointBackgroundColor: '#2dd4bf',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#2dd4bf',
      },
      {
        label: 'Industry Benchmark',
        data: targetScores.length > 0 ? targetScores : [80, 80, 80, 80, 80, 80],
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        borderColor: 'rgba(255, 255, 255, 0.25)',
        borderWidth: 1,
        borderDash: [4, 4],
        pointRadius: 0,
      }
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: 'rgba(255, 255, 255, 0.08)' },
        grid: { color: 'rgba(255, 255, 255, 0.08)' },
        pointLabels: { color: 'rgba(255, 255, 255, 0.7)', font: { size: 11, family: 'Inter' } },
        ticks: { display: false, min: 0, max: 100 },
      },
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: 'rgba(255, 255, 255, 0.6)', font: { size: 12, family: 'Inter' }, padding: 15 },
      },
      tooltip: {
        backgroundColor: '#0d1420',
        titleColor: '#fff',
        bodyColor: '#2dd4bf',
        borderColor: '#1b2333',
        borderWidth: 1,
      }
    },
  };

  return (
    <div className="w-full h-64 md:h-72">
      <Radar data={data} options={options} />
    </div>
  );
}

export function ProgressTrendLine({ snapshots = [] }) {
  const labels = snapshots.map((s, idx) => `Check-in ${idx + 1}`);
  const scores = snapshots.map((s) => s.readiness_score || 0);

  const data = {
    labels: labels.length > 0 ? labels : ['Day 1', 'Day 3', 'Day 7', 'Day 12', 'Day 18'],
    datasets: [
      {
        label: 'Readiness Score (%)',
        data: scores.length > 0 ? scores : [25, 38, 52, 68, 78],
        fill: true,
        backgroundColor: 'rgba(45, 212, 191, 0.12)',
        borderColor: '#2dd4bf',
        borderWidth: 2.5,
        tension: 0.35,
        pointBackgroundColor: '#2dd4bf',
        pointBorderColor: '#060a12',
        pointBorderWidth: 2,
        pointRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: 'rgba(255, 255, 255, 0.4)', font: { size: 11 } },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: 'rgba(255, 255, 255, 0.4)', font: { size: 11 } },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0d1420',
        titleColor: '#fff',
        bodyColor: '#2dd4bf',
        borderColor: '#1b2333',
        borderWidth: 1,
      }
    },
  };

  return (
    <div className="w-full h-64">
      <Line data={data} options={options} />
    </div>
  );
}

export function SalaryProjectionBar({ currentSalary = 6.5, projectedSalary = 10.2 }) {
  const data = {
    labels: ['Current Skills', 'With Missing Skills'],
    datasets: [
      {
        label: 'Projected Package (LPA ₹)',
        data: [currentSalary, projectedSalary],
        backgroundColor: ['rgba(255, 255, 255, 0.15)', 'rgba(45, 212, 191, 0.85)'],
        borderColor: ['rgba(255, 255, 255, 0.3)', '#2dd4bf'],
        borderWidth: 1,
        borderRadius: 8,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: 'rgba(255, 255, 255, 0.7)', font: { size: 12 } },
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.06)' },
        ticks: {
          color: 'rgba(255, 255, 255, 0.4)',
          callback: (value) => `₹${value} L`,
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0d1420',
        titleColor: '#fff',
        bodyColor: '#2dd4bf',
        callbacks: {
          label: (item) => `Est: ₹${item.raw} LPA`,
        },
      },
    },
  };

  return (
    <div className="w-full h-60">
      <Bar data={data} options={options} />
    </div>
  );
}

export function FLConvergenceChart({ rounds = [] }) {
  const labels = rounds.map((r) => `Round ${r.round_number}`);
  const accuracies = rounds.map((r) => Math.round(r.global_accuracy * 100));

  const data = {
    labels: labels.length > 0 ? labels : ['Round 1', 'Round 2', 'Round 3', 'Round 4', 'Round 5'],
    datasets: [
      {
        label: 'Global Model Accuracy (%)',
        data: accuracies.length > 0 ? accuracies : [72, 79, 84, 88, 91],
        borderColor: '#5eead4',
        backgroundColor: 'rgba(94, 234, 212, 0.15)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#5eead4',
        pointRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: 'rgba(255, 255, 255, 0.4)' },
      },
      y: {
        min: 50,
        max: 100,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: 'rgba(255, 255, 255, 0.4)',
          callback: (v) => `${v}%`,
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0d1420',
        borderColor: '#1b2333',
        borderWidth: 1,
      },
    },
  };

  return (
    <div className="w-full h-64">
      <Line data={data} options={options} />
    </div>
  );
}
