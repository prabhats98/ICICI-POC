/**
 * IncidentTrendChart — Stacked area chart for P1/P2/P3 incidents over time.
 * Uses react-chartjs-2 with gradient fills and custom tooltip.
 */

import { useRef, useEffect } from 'react';
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

export default function IncidentTrendChart({ data = [] }) {
  const chartRef = useRef(null);

  const labels = data.map((d) => {
    const date = new Date(d.date);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });

  const createGradient = (ctx, color) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, color.replace('1)', '0.35)'));
    gradient.addColorStop(1, color.replace('1)', '0.02)'));
    return gradient;
  };

  const chartData = {
    labels,
    datasets: [
      {
        label: 'P1 Critical',
        data: data.map((d) => d.P1 || 0),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.15)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#ef4444',
        pointBorderColor: 'transparent',
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#ef4444',
        pointHoverBorderColor: 'rgba(239, 68, 68, 0.3)',
        pointHoverBorderWidth: 4,
      },
      {
        label: 'P2 Warning',
        data: data.map((d) => d.P2 || 0),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.12)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#f59e0b',
        pointBorderColor: 'transparent',
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#f59e0b',
        pointHoverBorderColor: 'rgba(245, 158, 11, 0.3)',
        pointHoverBorderWidth: 4,
      },
      {
        label: 'P3 Info',
        data: data.map((d) => d.P3 || 0),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.10)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#10b981',
        pointBorderColor: 'transparent',
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#10b981',
        pointHoverBorderColor: 'rgba(16, 185, 129, 0.3)',
        pointHoverBorderWidth: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
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
    },
  };

  return (
    <div style={{ height: 280, position: 'relative' }}>
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  );
}
