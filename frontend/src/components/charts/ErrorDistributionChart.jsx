/**
 * ErrorDistributionChart — Doughnut chart for incident categories
 * (Security, Performance, Availability, etc.) with center total and scrollable side legend.
 */

import { Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const CATEGORY_COLORS = [
  '#6366f1', // indigo
  '#f43f5e', // rose
  '#f59e0b', // amber
  '#10b981', // emerald
  '#06b6d4', // cyan
  '#8b5cf6', // violet
  '#3b82f6', // blue
  '#ec4899', // pink
  '#14b8a6', // teal
  '#a855f7', // purple
];

export default function ErrorDistributionChart({ distribution = [], total = 0 }) {
  const labels = distribution.map((d) => d.category);
  const values = distribution.map((d) => d.count);
  const colors = distribution.map((_, i) => CATEGORY_COLORS[i % CATEGORY_COLORS.length]);

  const chartData = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: colors.map((c) => c + '33'),
        borderColor: colors,
        borderWidth: 2,
        hoverBackgroundColor: colors.map((c) => c + '66'),
        hoverBorderWidth: 3,
        spacing: 2,
        borderRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '68%',
    plugins: {
      legend: { display: false },
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
        callbacks: {
          label: (ctx) => {
            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
            return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
          },
        },
      },
    },
  };

  // Center text plugin
  const centerTextPlugin = {
    id: 'centerText',
    beforeDraw(chart) {
      const { ctx, width, height } = chart;
      ctx.save();
      ctx.font = '800 28px Inter';
      ctx.fillStyle = '#f1f5f9';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(total.toLocaleString(), width / 2, height / 2 - 8);
      ctx.font = '500 11px Inter';
      ctx.fillStyle = '#64748b';
      ctx.fillText('TOTAL', width / 2, height / 2 + 14);
      ctx.restore();
    },
  };

  // Show top 8 in legend, rest grouped into "Others"
  const MAX_LEGEND = 8;
  const legendItems = distribution.length > MAX_LEGEND
    ? [
        ...distribution.slice(0, MAX_LEGEND),
        {
          category: `+${distribution.length - MAX_LEGEND} more`,
          count: distribution.slice(MAX_LEGEND).reduce((s, d) => s + d.count, 0),
          percentage: distribution.slice(MAX_LEGEND).reduce((s, d) => s + d.percentage, 0).toFixed(1),
          _isOther: true,
        },
      ]
    : distribution;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, height: 260 }}>
      <div style={{ flex: '0 0 190px', height: 190, position: 'relative' }}>
        <Doughnut data={chartData} options={options} plugins={[centerTextPlugin]} />
      </div>
      <div className="doughnut-legend" style={{ maxHeight: 250, overflowY: 'auto' }}>
        {legendItems.map((d, i) => (
          <div key={d.category} className="doughnut-legend-item" title={d.category}>
            <span
              className="doughnut-legend-dot"
              style={{
                background: d._isOther
                  ? 'var(--text-muted)'
                  : CATEGORY_COLORS[i % CATEGORY_COLORS.length],
              }}
            />
            <span className="doughnut-legend-label">{d.category || 'Unknown'}</span>
            <span className="doughnut-legend-value">{d.count}</span>
            <span className="doughnut-legend-pct">{d.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
