/**
 * IncidentTrendChart — Bar chart showing incidents by priority over time.
 * Light theme with vibrant colors.
 */
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

export default function IncidentTrendChart({ data = [] }) {
  if (!data || data.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">📊</div>
        <div className="empty-state-title">No trend data</div>
        <div className="empty-state-text">Run the pipeline to generate incident trends</div>
      </div>
    );
  }

  const labels = data.map((d) => {
    const dt = new Date(d.date);
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });

  const chartData = {
    labels,
    datasets: [
      {
        label: 'P1 Critical',
        data: data.map((d) => d.P1 || 0),
        backgroundColor: 'rgba(239, 68, 68, 0.85)',
        borderColor: '#ef4444',
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.7,
      },
      {
        label: 'P2 High',
        data: data.map((d) => d.P2 || 0),
        backgroundColor: 'rgba(245, 158, 11, 0.85)',
        borderColor: '#f59e0b',
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.7,
      },
      {
        label: 'P3 Medium',
        data: data.map((d) => d.P3 || 0),
        backgroundColor: 'rgba(16, 185, 129, 0.85)',
        borderColor: '#10b981',
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.7,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#334155', font: { size: 12, weight: '600' }, padding: 16, usePointStyle: true, pointStyleWidth: 8 },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#fff',
        bodyColor: '#e2e8f0',
        padding: 12,
        cornerRadius: 8,
        titleFont: { size: 13, weight: '700' },
      },
    },
    scales: {
      x: {
        ticks: { color: '#64748b', font: { size: 11 } },
        grid: { color: 'rgba(0, 0, 0, 0.04)' },
        border: { color: '#e2e8f0' },
      },
      y: {
        ticks: { color: '#64748b', font: { size: 11 }, stepSize: 1 },
        grid: { color: 'rgba(0, 0, 0, 0.04)' },
        border: { color: '#e2e8f0' },
        beginAtZero: true,
      },
    },
  };

  return (
    <div style={{ height: 260 }}>
      <Bar data={chartData} options={options} />
    </div>
  );
}
