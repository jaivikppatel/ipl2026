import { useState } from 'react'
import './PlayerAvatar.css'

// Known generic placeholder URLs from CricketData.org — treated as "no image"
const PLACEHOLDER_URLS = new Set([
  'https://h.cricapi.com/img/icon512.png',
  'https://cdorgapi.b-cdn.net/img/icon512.png',
])

function isRealImage(url) {
  return url && !PLACEHOLDER_URLS.has(url)
}

function HumanIcon() {
  return (
    <svg
      className="pa-human-icon"
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="paHeadGrad" cx="38%" cy="30%" r="65%">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0.6" />
        </radialGradient>
        <radialGradient id="paBodyGrad" cx="50%" cy="0%" r="80%">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0.5" />
        </radialGradient>
      </defs>
      {/* Head */}
      <circle cx="20" cy="14" r="7.5" fill="url(#paHeadGrad)" />
      {/* Highlight on head for 3D effect */}
      <circle cx="17.5" cy="11.5" r="2.5" fill="#fff" opacity="0.3" />
      {/* Body / shoulders */}
      <path
        d="M6 38c0-7.732 6.268-14 14-14s14 6.268 14 14"
        fill="url(#paBodyGrad)"
      />
    </svg>
  )
}

/**
 * PlayerAvatar — shows player photo when available, otherwise a human silhouette icon.
 *
 * Props:
 *   imageUrl   – URL from API (may be null or a placeholder)
 *   name       – Player name (used for alt text)
 *   teamColor  – Team primary color (used as background when no real image)
 *   className  – CSS class for the outer div (default: 'player-avatar')
 *   style      – Extra inline styles for the outer div
 */
export default function PlayerAvatar({ imageUrl, name, teamColor, className = 'player-avatar', style = {} }) {
  const [imgFailed, setImgFailed] = useState(false)
  const showImage = isRealImage(imageUrl) && !imgFailed

  return (
    <div
      className={`${className} pa-root`}
      style={showImage ? style : { ...style, background: teamColor || '#2a2a2a' }}
    >
      {showImage ? (
        <img
          src={imageUrl}
          alt={name || ''}
          className="pa-img"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <HumanIcon />
      )}
    </div>
  )
}
