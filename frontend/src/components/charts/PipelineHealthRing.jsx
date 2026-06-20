/**
 * PipelineHealthRing — Ring chart showing pipeline success/fail/running ratio.
 * Center: success rate %. Below: avg duration, last run time.
 */

import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip } from 'chart.js';

ChartJS.register(ArcElement, Tooltip);

export default function PipelineHealthRing({ runs = [] }) {
  const success = runs.filter((r) => r.status === 'SUCCESS').length;
  const failed = runs.filter((r) => r.status === 'FAILED').length;
  const running = runs.filter((r) => r.status === 'RUNNING').length;
  const other = runs.length - success - failed - running;
  const total = runs.length || 1;
  const successRate = Math.round((success / total) * 100);

  const avgDuration = runs
    .filter((r) => r.duration_seconds)
    .reduce((sum, r, _, arr) => sum + r.duration_seconds / arr.length, 0);

  const lastRun = runs[0];
  const lastRunTime = lastRun?.started_at
    ? new Date(lastRun.started_at).toLocaleString()
    : 'No runs';

  const chartData = {
    labels: ['Success', 'Failed', 'Running', 'Other'],
    datasets: [{
      data: [success, failed, running, other],
      backgroundColor: [
        'rgba(16,185,129,0.6)',
        'rgba(239,68,68,0.6)',
        'rgba(59,130,246,0.6)',
        'rgba(100,116,139,0.3)',
      ],
      borderColor: [
        '#10b981',
        '#ef4444',
        '#3b82f6',
        '#64748b',
      ],
      borderWidth: 2,
      spacing: 2,
      borderRadius: 4,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '72%',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        padding: 10,
        cornerRadius: 8,
        titleFont: { size: 12, weight: '600', family: 'Inter' },
        bodyFont: { size: 11, family: 'Inter' },
      },
    },
  };

  const centerTextPlugin = {
    id: 'pipelineCenterText',
    beforeDraw(chart) {
      const { ctx, width, height } = chart;
      ctx.save();
      ctx.font = '800 26px Inter';
      ctx.fillStyle = successRate >= 80 ? '#10b981' : successRate >= 50 ? '#f59e0b' : '#ef4444';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${successRate}%`, width / 2, height / 2 - 6);
      ctx.font = '500 9px Inter';
      ctx.fillStyle = '#64748b';
      ctx.fillText('SUCCESS', width / 2, height / 2 + 12);
      ctx.restore();
    },
  };

  return (
    <div className="pipeline-health-ring">
      <div style={{ width: 160, height: 160, margin: '0 auto' }}>
        <Doughnut data={chartData} options={options} plugins={[centerTextPlugin]} />
      </div>
      <div className="pipeline-ring-stats">
        <div className="pipeline-ring-stat">
          <span className="pipeline-ring-stat-value">{runs.length}</span>
          <span className="pipeline-ring-stat-label">Total Runs</span>
        </div>
        <div className="pipeline-ring-stat-divider" />
        <div className="pipeline-ring-stat">
          <span className="pipeline-ring-stat-value">{avgDuration ? avgDuration.toFixed(1) + 's' : '—'}</span>
          <span className="pipeline-ring-stat-label">Avg Duration</span>
        </div>
        <div className="pipeline-ring-stat-divider" />
        <div className="pipeline-ring-stat">
          <span className="pipeline-ring-stat-value" style={{ fontSize: 11 }}>{lastRunTime}</span>
          <span className="pipeline-ring-stat-label">Last Run</span>
        </div>
      </div>
    </div>
  );
}
