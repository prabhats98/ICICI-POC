/**
 * ErrorDistributionChart — Doughnut chart showing error categories.
 * Light theme with vibrant colors.
 */
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const COLORS = [
  '#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6',
  '#06b6d4', '#f97316', '#ec4899', '#14b8a6', '#6366f1',
];

export default function ErrorDistributionChart({ distribution = [], total = 0 }) {
  if (!distribution || distribution.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-title">No error data</div>
        <div className="empty-state-text">Errors will appear after pipeline runs</div>
      </div>
    );
  }

  const chartData = {
    labels: distribution.map((d) => d.category || 'Unknown'),
    datasets: [{
      data: distribution.map((d) => d.count),
      backgroundColor: COLORS.slice(0, distribution.length),
      borderColor: '#ffffff',
      borderWidth: 3,
      hoverOffset: 8,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '60%',
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#334155',
          font: { size: 12, weight: '500' },
          padding: 14,
          usePointStyle: true,
          pointStyleWidth: 8,
          generateLabels: (chart) => {
            const data = chart.data;
            return data.labels.map((label, i) => ({
              text: `${label} (${data.datasets[0].data[i]})`,
              fillStyle: data.datasets[0].backgroundColor[i],
              strokeStyle: '#fff',
              lineWidth: 0,
              pointStyle: 'circle',
              index: i,
            }));
          },
        },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#fff',
        bodyColor: '#e2e8f0',
        padding: 12,
        cornerRadius: 8,
        callbacks: {
          label: (ctx) => {
            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
            return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`;
          },
        },
      },
    },
  };

  return (
    <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Doughnut data={chartData} options={options} />
    </div>
  );
}
