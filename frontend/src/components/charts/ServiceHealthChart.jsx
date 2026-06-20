/**
 * ServiceHealthChart — Horizontal stacked bar chart per Azure service.
 * Shows P1/P2/P3 breakdown with open/resolved counts.
 */

import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const SERVICE_DISPLAY = {
  'azure-front-door': 'Front Door',
  'azure-app-gateway': 'App Gateway',
  'azure-apim': 'API Management',
  'azure-vm': 'Virtual Machine',
};

export default function ServiceHealthChart({ services = [] }) {
  const labels = services.map(
    (s) => SERVICE_DISPLAY[s.service] || s.service || 'Unknown'
  );

  const chartData = {
    labels,
    datasets: [
      {
        label: 'P1 Critical',
        data: services.map((s) => s.P1 || 0),
        backgroundColor: 'rgba(239, 68, 68, 0.6)',
        borderColor: '#ef4444',
        borderWidth: 1,
        borderRadius: 3,
        borderSkipped: false,
      },
      {
        label: 'P2 Warning',
        data: services.map((s) => s.P2 || 0),
        backgroundColor: 'rgba(245, 158, 11, 0.6)',
        borderColor: '#f59e0b',
        borderWidth: 1,
        borderRadius: 3,
        borderSkipped: false,
      },
      {
        label: 'P3 Info',
        data: services.map((s) => s.P3 || 0),
        backgroundColor: 'rgba(16, 185, 129, 0.6)',
        borderColor: '#10b981',
        borderWidth: 1,
        borderRadius: 3,
        borderSkipped: false,
      },
    ],
  };

  const options = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
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
        callbacks: {
          afterBody: (items) => {
            const svcIdx = items[0]?.dataIndex;
            if (svcIdx !== undefined && services[svcIdx]) {
              const svc = services[svcIdx];
              return `\nOpen: ${svc.open || 0} · Resolved: ${svc.resolved || 0}`;
            }
          },
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        beginAtZero: true,
        grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
        ticks: {
          color: '#64748b',
          font: { size: 11, family: 'Inter' },
          stepSize: 1,
        },
        border: { display: false },
      },
      y: {
        stacked: true,
        grid: { display: false },
        ticks: {
          color: '#94a3b8',
          font: { size: 12, family: 'Inter', weight: '500' },
        },
        border: { display: false },
      },
    },
  };

  return (
    <div style={{ height: 280, position: 'relative' }}>
      <Bar data={chartData} options={options} />
    </div>
  );
}
