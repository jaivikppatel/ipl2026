/**
 * AajFantasyLogo — brand logo for "आज Fantasy"
 *
 * Props:
 *  size     'sm' | 'md' | 'lg'  (default 'md')
 *  light    boolean              if true, FANTASY text is white (for gradient backgrounds)
 *  className  string
 */
import { useId } from 'react'

export default function AajFantasyLogo({ size = 'md', light = false, className = '' }) {
  const cfg = {
    sm: { w: 130, svgH: 38, aajY: 28, aajFs: 29, lineY: 34, fantasyFs: 17, ls: '0.15em', gap: 4 },
    md: { w: 165, svgH: 48, aajY: 35, aajFs: 37, lineY: 42, fantasyFs: 22, ls: '0.18em', gap: 5 },
    lg: { w: 205, svgH: 58, aajY: 44, aajFs: 46, lineY: 52, fantasyFs: 27, ls: '0.22em', gap: 6 },
  }[size]

  const uid    = useId().replace(/:/g, 'x')
  const lineId = `afgl-${uid}`
  const glowId = `afgw-${uid}`

  const fantasyStyle = light
    ? { color: 'white' }
    : {
        background: 'linear-gradient(90deg, #ec008c 0%, #ff6b00 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }

  return (
    <div
      className={className}
      style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: cfg.gap }}
      aria-label="आज Fantasy"
    >
      {/* SVG: "आज" + separator line only */}
      <svg
        width={cfg.w}
        height={cfg.svgH}
        viewBox={`0 0 ${cfg.w} ${cfg.svgH}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Faded gradient for the separator line */}
          <linearGradient id={lineId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#ec008c" stopOpacity="0" />
            <stop offset="30%"  stopColor="#ec008c" stopOpacity="0.9" />
            <stop offset="70%"  stopColor="#ff6b00" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#ff6b00" stopOpacity="0" />
          </linearGradient>

          {/* Pink glow behind "आज" */}
          <filter id={glowId} x="-20%" y="-25%" width="140%" height="150%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
            <feFlood floodColor="#ec008c" floodOpacity="0.55" result="color" />
            <feComposite in="color" in2="blur" operator="in" result="glow" />
            <feMerge>
              <feMergeNode in="glow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* "आज" — Devanagari, white with pink glow */}
        <text
          x={cfg.w / 2}
          y={cfg.aajY}
          textAnchor="middle"
          fontFamily="'Rajdhani', sans-serif"
          fontWeight="700"
          fontSize={cfg.aajFs}
          fill="white"
          filter={`url(#${glowId})`}
        >
          आज
        </text>

        {/* Separator line */}
        <line
          x1={cfg.w * 0.08}
          y1={cfg.lineY}
          x2={cfg.w * 0.92}
          y2={cfg.lineY}
          stroke={light ? 'rgba(255,255,255,0.5)' : `url(#${lineId})`}
          strokeWidth="1.5"
        />
      </svg>

      {/* "FANTASY" — plain HTML text with CSS gradient, never breaks */}
      <span
        style={{
          fontFamily: "'Rajdhani', sans-serif",
          fontWeight: 700,
          fontSize: cfg.fantasyFs,
          letterSpacing: cfg.ls,
          lineHeight: 1,
          display: 'block',
          ...fantasyStyle,
        }}
      >
        FANTASY
      </span>
    </div>
  )
}
