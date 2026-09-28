import React, { useState } from 'react';

// -------------------------------------------------------------
// 1. Time Series Chart (SVG Area / Bar)
// -------------------------------------------------------------
export interface TimeSeriesPoint {
  timestamp: string;
  tx_count: number;
  volume: number;
}

interface TimeSeriesChartProps {
  data: TimeSeriesPoint[];
  height?: number;
  metric?: 'volume' | 'tx_count';
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  height = 200,
  metric = 'tx_count',
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.85rem' }}>
        No time series activity recorded
      </div>
    );
  }

  const padding = { top: 20, right: 20, bottom: 30, left: 45 };
  const width = 600; // viewBox width for SVG responsiveness
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const values = data.map((d) => (metric === 'volume' ? d.volume : d.tx_count));
  const maxValue = Math.max(...values, 1);

  // Generate SVG path for line / area
  const points = data.map((d, i) => {
    const x = padding.left + (i / Math.max(data.length - 1, 1)) * chartWidth;
    const val = metric === 'volume' ? d.volume : d.tx_count;
    const y = padding.top + chartHeight - (val / maxValue) * chartHeight;
    return { x, y, data: d };
  });

  const linePath = points.reduce((acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`, '');
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${padding.top + chartHeight} L ${points[0].x} ${padding.top + chartHeight} Z`;

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: 'auto', overflow: 'visible' }}
      >
        <defs>
          <linearGradient id="cyberAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Horizontal gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
          const y = padding.top + chartHeight * (1 - ratio);
          const labelVal = (maxValue * ratio).toFixed(metric === 'volume' ? 2 : 0);
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#1e293b"
                strokeDasharray="4 4"
              />
              <text
                x={padding.left - 8}
                y={y + 3}
                fill="#64748b"
                fontSize="10"
                textAnchor="end"
                fontFamily="ui-monospace, monospace"
              >
                {labelVal}
              </text>
            </g>
          );
        })}

        {/* Area fill */}
        <path d={areaPath} fill="url(#cyberAreaGrad)" />

        {/* Stroke line */}
        <path d={linePath} fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Interactive Data Dots */}
        {points.map((pt, i) => (
          <g key={i}>
            <circle
              cx={pt.x}
              cy={pt.y}
              r={hoveredIndex === i ? 6 : 3.5}
              fill={hoveredIndex === i ? '#38bdf8' : '#0f172a'}
              stroke="#38bdf8"
              strokeWidth="2"
              style={{ cursor: 'pointer', transition: 'r 0.15s' }}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          </g>
        ))}

        {/* X Axis Labels (First and Last) */}
        {points.length > 0 && (
          <>
            <text
              x={points[0].x}
              y={height - 8}
              fill="#64748b"
              fontSize="9"
              textAnchor="start"
              fontFamily="ui-monospace, monospace"
            >
              {points[0].data.timestamp ? points[0].data.timestamp.slice(0, 16) : 'T0'}
            </text>
            {points.length > 1 && (
              <text
                x={points[points.length - 1].x}
                y={height - 8}
                fill="#64748b"
                fontSize="9"
                textAnchor="end"
                fontFamily="ui-monospace, monospace"
              >
                {points[points.length - 1].data.timestamp
                  ? points[points.length - 1].data.timestamp.slice(0, 16)
                  : `T${points.length - 1}`}
              </text>
            )}
          </>
        )}
      </svg>

      {/* Floating Tooltip */}
      {hoveredIndex !== null && data[hoveredIndex] && (
        <div
          style={{
            position: 'absolute',
            top: '8px',
            right: '12px',
            background: '#0f172a',
            border: '1px solid #38bdf888',
            borderRadius: '6px',
            padding: '0.4rem 0.65rem',
            fontSize: '0.75rem',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            pointerEvents: 'none',
          }}
        >
          <div style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
            {data[hoveredIndex].timestamp || 'Timestamp bucket'}
          </div>
          <div style={{ color: '#f8fafc', fontWeight: 600, marginTop: '2px' }}>
            {metric === 'volume'
              ? `${data[hoveredIndex].volume.toFixed(4)} ₿ Volume`
              : `${data[hoveredIndex].tx_count} Transactions`}
          </div>
        </div>
      )}
    </div>
  );
};

// -------------------------------------------------------------
// 2. Priority Donut Chart (CRITICAL, HIGH, MODERATE, LOW)
// -------------------------------------------------------------
interface PriorityDonutProps {
  counts: {
    CRITICAL?: number;
    HIGH?: number;
    MODERATE?: number;
    LOW?: number;
  };
  size?: number;
}

export const PriorityDonutChart: React.FC<PriorityDonutProps> = ({ counts, size = 160 }) => {
  const critical = counts.CRITICAL || 0;
  const high = counts.HIGH || 0;
  const moderate = counts.MODERATE || 0;
  const low = counts.LOW || 0;
  const total = critical + high + moderate + low;

  if (total === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: size, color: '#64748b', fontSize: '0.85rem' }}>
        No entities scored
      </div>
    );
  }

  const radius = 60;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * radius;

  const slices = [
    { label: 'CRITICAL', count: critical, color: '#ef4444' },
    { label: 'HIGH', count: high, color: '#f87171' },
    { label: 'MODERATE', count: moderate, color: '#f59e0b' },
    { label: 'LOW', count: low, color: '#10b981' },
  ];

  let accumulatedPercent = 0;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
      <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
        <svg viewBox="0 0 160 160" width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          {/* Background circle */}
          <circle cx="80" cy="80" r={radius} fill="none" stroke="var(--border-subtle)" strokeWidth={strokeWidth} />
          {slices.map((slice) => {
            if (slice.count === 0) return null;
            const percent = slice.count / total;
            const strokeDasharray = `${circumference * percent} ${circumference * (1 - percent)}`;
            const strokeDashoffset = -circumference * accumulatedPercent;
            accumulatedPercent += percent;

            return (
              <circle
                key={slice.label}
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="butt"
              />
            );
          })}
        </svg>

        {/* Center Total Count */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <span style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'ui-monospace, monospace' }}>
            {total}
          </span>
          <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
            Scored
          </span>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', flex: 1, minWidth: '130px' }}>
        {slices.map((s) => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.78rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: s.color }} />
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{s.label}</span>
            </div>
            <span style={{ fontFamily: 'ui-monospace, monospace', color: s.count > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
              {s.count} ({((s.count / total) * 100).toFixed(0)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// 3. Category Horizontal Bar Chart (Behavioral, Ports, Script Types)
// -------------------------------------------------------------
interface CategoryBarProps {
  data: Record<string, number>;
  maxItems?: number;
  color?: string;
}

export const CategoryBarChart: React.FC<CategoryBarProps> = ({
  data,
  maxItems = 6,
  color = '#38bdf8',
}) => {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxItems);

  if (entries.length === 0) {
    return <div style={{ color: '#64748b', fontSize: '0.85rem', padding: '0.5rem 0' }}>No categories recorded</div>;
  }

  const maxValue = Math.max(...entries.map((e) => e[1]), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
      {entries.map(([label, count]) => {
        const pct = (count / maxValue) * 100;
        return (
          <div key={label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '3px' }}>
              <span style={{ color: '#cbd5e1', fontWeight: 500, fontFamily: 'ui-monospace, monospace' }}>
                {label.replace(/_/g, ' ')}
              </span>
              <span style={{ color: '#94a3b8', fontFamily: 'ui-monospace, monospace' }}>
                {count}
              </span>
            </div>
            <div style={{ height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: `linear-gradient(90deg, ${color}88, ${color})`,
                  borderRadius: '3px',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
