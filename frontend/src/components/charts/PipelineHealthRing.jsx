/**
 * PipelineHealthRing — Shows pipeline run success/failure ratio.
 */
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip } from 'chart.js';

ChartJS.register(ArcElement, Tooltip);

export default function PipelineHealthRing({ runs = [] }) {
  if (!runs || runs.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">🔄</div>
        <div className="empty-state-title">No pipeline runs</div>
        <div className="empty-state-text">Run the pipeline to see health data</div>
      </div>
    );
  }

  const success = runs.filter((r) => r.status === 'SUCCESS').length;
  const failed = runs.filter((r) => r.status === 'FAILED').length;
  const running = runs.filter((r) => r.status === 'RUNNING').length;

  const data = {
    labels: ['Success', 'Failed', 'Running'],
    datasets: [{
      data: [success, failed, running],
      backgroundColor: ['#10b981', '#ef4444', '#3b82f6'],
      borderColor: '#ffffff',
      borderWidth: 3,
      hoverOffset: 6,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#334155', font: { size: 12, weight: '600' }, padding: 16, usePointStyle: true },
      },
      tooltip: { backgroundColor: '#0f172a', titleColor: '#fff', bodyColor: '#e2e8f0', padding: 10, cornerRadius: 8 },
    },
  };

  return (
    <div style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Doughnut data={data} options={options} />
    </div>
  );
}
