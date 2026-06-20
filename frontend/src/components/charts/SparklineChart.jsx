/**
 * SparklineChart — Tiny inline sparkline using canvas.
 * No axes, no labels. Just a gradient-filled area line.
 */

import { useRef, useEffect } from 'react';

export default function SparklineChart({
  data = [],
  width = 80,
  height = 28,
  color = '#6366f1',
  strokeWidth = 1.5,
  className = '',
  style = {},
}) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const max = Math.max(...data, 1);
    const min = Math.min(...data, 0);
    const range = max - min || 1;
    const padding = 2;
    const drawW = width - padding * 2;
    const drawH = height - padding * 2;

    const points = data.map((v, i) => ({
      x: padding + (i / (data.length - 1)) * drawW,
      y: padding + drawH - ((v - min) / range) * drawH,
    }));

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, color + '40');
    gradient.addColorStop(1, color + '05');

    // Area fill
    ctx.beginPath();
    ctx.moveTo(points[0].x, height);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line stroke
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const cp1x = (points[i - 1].x + points[i].x) / 2;
      const cp1y = points[i - 1].y;
      const cp2x = cp1x;
      const cp2y = points[i].y;
      ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, points[i].x, points[i].y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = strokeWidth;
    ctx.stroke();

    // End dot
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last.x, last.y, 2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }, [data, width, height, color, strokeWidth]);

  return (
    <canvas
      ref={canvasRef}
      className={`sparkline-canvas ${className}`}
      style={{ width, height, ...style }}
    />
  );
}
