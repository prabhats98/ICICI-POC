/**
 * AnimatedCounter — Smooth count-up animation for KPI values.
 * Uses requestAnimationFrame with easeOutExpo easing.
 */

import { useState, useEffect, useRef } from 'react';

function easeOutExpo(t) {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

export default function AnimatedCounter({
  value = 0,
  duration = 1200,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
  style = {},
}) {
  const [displayValue, setDisplayValue] = useState(0);
  const prevValue = useRef(0);
  const rafId = useRef(null);

  useEffect(() => {
    const startValue = prevValue.current;
    const endValue = typeof value === 'number' ? value : parseFloat(value) || 0;
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutExpo(progress);
      const current = startValue + (endValue - startValue) * eased;
      setDisplayValue(current);

      if (progress < 1) {
        rafId.current = requestAnimationFrame(animate);
      } else {
        prevValue.current = endValue;
      }
    };

    rafId.current = requestAnimationFrame(animate);
    return () => {
      if (rafId.current) cancelAnimationFrame(rafId.current);
    };
  }, [value, duration]);

  const formatted = typeof value === 'number'
    ? displayValue.toFixed(decimals)
    : value;

  return (
    <span className={`animated-counter ${className}`} style={style}>
      {prefix}{typeof value === 'number' ? Number(formatted).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : formatted}{suffix}
    </span>
  );
}
