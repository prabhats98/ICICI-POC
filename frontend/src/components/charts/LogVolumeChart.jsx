/**
 * LogVolumeChart — Multi-line chart for log levels (CRITICAL, ERROR, WARNING, INFO) over time.
 * Lines with gradient area fills beneath each.
 */

import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const LEVEL_CONFIG = {
  CRITICAL: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.10)' },
  ERROR: { color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.10)' },
  WARNING: { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.08)' },
  INFO: { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.08)' },
};

export default function LogVolumeChart({ data = [] }) {
  const labels = data.map((d) => {
    const date = new Date(d.date);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });

  const chartData = {
    labels,
    datasets: Object.entries(LEVEL_CONFIG).map(([level, cfg]) => ({
      label: level,
      data: data.map((d) => d[level] || 0),
      borderColor: cfg.color,
      backgroundColor: cfg.bg,
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointRadius: 2,
      pointBackgroundColor: cfg.color,
      pointBorderColor: 'transparent',
      pointHoverRadius: 5,
      pointHoverBackgroundColor: cfg.color,
      pointHoverBorderColor: cfg.bg,
      pointHoverBorderWidth: 4,
    })),
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        align: 'end',
        labels: {
          color: '#94a3b8',
          font: { size: 11, family: 'Inter' },
          usePointStyle: true,
          pointStyle: 'circle',
          boxWidth: 8,
          boxHeight: 8,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        padding: 12,
        cornerRadius: 8,
        titleFont: { size: 13, weight: '600', family: 'Inter' },
        bodyFont: { size: 12, family: 'Inter' },
        displayColors: true,
        boxPadding: 4,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
        ticks: { color: '#64748b', font: { size: 11, family: 'Inter' } },
        border: { display: false },
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
        ticks: { color: '#64748b', font: { size: 11, family: 'Inter' } },
        border: { display: false },
      },
    },
  };

  return (
    <div style={{ height: 280, position: 'relative' }}>
      <Line data={chartData} options={options} />
    </div>
  );
}
