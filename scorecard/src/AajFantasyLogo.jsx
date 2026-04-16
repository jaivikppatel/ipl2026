/**
 * AajFantasyLogo — inline SVG brand logo for "आज Fantasy"
 *
 * Props:
 *  size     'sm' | 'md' | 'lg'  (default 'md')
 *  light    boolean              if true, FANTASY text is white (for gradient backgrounds)
 *  className  string
 */
export default function AajFantasyLogo({ size = 'md', light = false, className = '' }) {
  const cfg = {
    sm: { w: 130, h: 52,  aajY: 28, aajFs: 29, lineY: 34, fantasyY: 49, fantasyFs: 17, ls: '1.5' },
    md: { w: 165, h: 66,  aajY: 35, aajFs: 37, lineY: 42, fantasyY: 62, fantasyFs: 22, ls: '2'   },
    lg: { w: 205, h: 82,  aajY: 44, aajFs: 46, lineY: 52, fantasyY: 76, fantasyFs: 27, ls: '2.5' },
  }[size]

  const gradId  = `afg-${size}`
  const lineId  = `afgl-${size}`
  const glowId  = `afgw-${size}`

  return (
    <svg
      width={cfg.w}
      height={cfg.h}
      viewBox={`0 0 ${cfg.w} ${cfg.h}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="आज Fantasy"
    >
      <defs>
        {/* Pink → orange gradient for "FANTASY" text */}
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#ec008c" />
          <stop offset="100%" stopColor="#ff6b00" />
        </linearGradient>

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

      {/* "FANTASY" — gradient or white (on gradient bg) */}
      <text
        x={cfg.w / 2}
        y={cfg.fantasyY}
        textAnchor="middle"
        fontFamily="'Rajdhani', sans-serif"
        fontWeight="700"
        fontSize={cfg.fantasyFs}
        fill={light ? 'white' : `url(#${gradId})`}
        letterSpacing={cfg.ls}
      >
        FANTASY
      </text>
    </svg>
  )
}
