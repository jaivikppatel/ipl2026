import { useState, useEffect } from 'react'
import FantasyService from './services/FantasyService'
import './FantasyOverallLeaderboard.css'

function FantasyOverallLeaderboard({ seriesId = null }) {
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedPlayer, setSelectedPlayer] = useState(null)

  useEffect(() => {
    loadLeaderboard()
  }, [seriesId])

  const loadLeaderboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await FantasyService.getFantasyOverallLeaderboard(seriesId)
      setLeaderboard(data.leaderboard || [])
    } catch (err) {
      setError(err.message || 'Failed to load leaderboard')
    } finally {
      setLoading(false)
    }
  }

  const openPlayer = (player) => setSelectedPlayer(player)
  const closePlayer = () => setSelectedPlayer(null)

  const getInitial = (name) => name?.charAt(0).toUpperCase() || '?'

  const getMedalEmoji = (rank) => {
    if (rank === 1) return '🏆'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return null
  }

  if (loading) {
    return (
      <div className="fol-loading">
        <div className="fol-spinner" />
        <p>Loading leaderboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fol-error">
        <div className="fol-error-icon">⚠️</div>
        <p>{error}</p>
        <button onClick={loadLeaderboard} className="fol-retry-btn">Try Again</button>
      </div>
    )
  }

  if (leaderboard.length === 0) {
    return (
      <div className="fol-empty">
        <div className="fol-empty-icon">🏏</div>
        <h3>No Rankings Yet</h3>
        <p>Leaderboard will appear once fantasy matches are completed.</p>
      </div>
    )
  }

  const top3 = leaderboard.slice(0, 3)
  const rest = leaderboard.slice(3)

  return (
    <>
    <div className="fol-container">
      <div className="fol-header">
        <h2 className="fol-title">
          <span>🏆</span> Fantasy Champions
        </h2>
      </div>

      {/* Podium */}
      {top3.length > 0 && (
        <div className="fol-podium-section">
          <div className="fol-podium-container">
            {/* 2nd */}
            {top3[1] && (
              <div className={`fol-podium-card fol-second${top3[1].is_current_user ? ' fol-me' : ''}`}
                onClick={() => openPlayer(top3[1])}
              >
                <div className="fol-rank-badge">2</div>
                <div className="fol-podium-avatar">
                  {top3[1].profilePicture ? (
                    <img src={top3[1].profilePicture} alt={top3[1].display_name} />
                  ) : (
                    <div className="fol-avatar-placeholder fol-silver">{getInitial(top3[1].display_name)}</div>
                  )}
                  <div className="fol-medal-overlay">🥈</div>
                </div>
                <h3 className="fol-podium-name">{top3[1].display_name}</h3>
                <div className="fol-podium-points">{top3[1].total_points}</div>
                <div className="fol-podium-label">pts</div>
                <div className="fol-podium-stats">
                  <span>{top3[1].matches_played}M</span>
                  <span className="fol-dot">·</span>
                  <span>{top3[1].average_points} avg</span>
                </div>
              </div>
            )}

            {/* 1st */}
            {top3[0] && (
              <div className={`fol-podium-card fol-first${top3[0].is_current_user ? ' fol-me' : ''}`}
                onClick={() => openPlayer(top3[0])}
              >
                <div className="fol-crown">👑</div>
                <div className="fol-rank-badge">1</div>
                <div className="fol-podium-avatar fol-champion-avatar">
                  {top3[0].profilePicture ? (
                    <img src={top3[0].profilePicture} alt={top3[0].display_name} />
                  ) : (
                    <div className="fol-avatar-placeholder fol-gold">{getInitial(top3[0].display_name)}</div>
                  )}
                  <div className="fol-medal-overlay">🏆</div>
                  <div className="fol-glow"></div>
                </div>
                <h3 className="fol-podium-name">{top3[0].display_name}</h3>
                <div className="fol-podium-points fol-champion-pts">{top3[0].total_points}</div>
                <div className="fol-podium-label">pts</div>
                <div className="fol-podium-stats">
                  <span>{top3[0].matches_played}M</span>
                  <span className="fol-dot">·</span>
                  <span>{top3[0].average_points} avg</span>
                </div>
              </div>
            )}

            {/* 3rd */}
            {top3[2] && (
              <div className={`fol-podium-card fol-third${top3[2].is_current_user ? ' fol-me' : ''}`}
                onClick={() => openPlayer(top3[2])}
              >
                <div className="fol-rank-badge">3</div>
                <div className="fol-podium-avatar">
                  {top3[2].profilePicture ? (
                    <img src={top3[2].profilePicture} alt={top3[2].display_name} />
                  ) : (
                    <div className="fol-avatar-placeholder fol-bronze">{getInitial(top3[2].display_name)}</div>
                  )}
                  <div className="fol-medal-overlay">🥉</div>
                </div>
                <h3 className="fol-podium-name">{top3[2].display_name}</h3>
                <div className="fol-podium-points">{top3[2].total_points}</div>
                <div className="fol-podium-label">pts</div>
                <div className="fol-podium-stats">
                  <span>{top3[2].matches_played}M</span>
                  <span className="fol-dot">·</span>
                  <span>{top3[2].average_points} avg</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Rest of rankings */}
      {rest.length > 0 && (
        <div className="fol-rankings-section">
          <div className="fol-rankings-header">
            <h3>All Rankings</h3>
            <span className="fol-count">{leaderboard.length} Players</span>
          </div>
          <div className="fol-rankings-list">
            {rest.map((player, index) => {
              const rank = index + 4
              return (
                <div
                  key={player.user_id}
                  className={`fol-ranking-row${player.is_current_user ? ' fol-me' : ''}`}
                  style={{ animationDelay: `${index * 0.04}s` }}
                  onClick={() => openPlayer(player)}
                >
                  <div className="fol-rank-num">{rank}</div>
                  <div className="fol-ranking-avatar">
                    {player.profilePicture ? (
                      <img src={player.profilePicture} alt={player.display_name} />
                    ) : (
                      <div className="fol-avatar-placeholder">{getInitial(player.display_name)}</div>
                    )}
                  </div>
                  <div className="fol-ranking-info">
                    <div className="fol-ranking-name">{player.display_name}</div>
                    <div className="fol-ranking-meta">
                      <span>🎮 {player.matches_played}</span>
                      <span>📊 {player.average_points} avg</span>
                      {player.best_rank && (
                        <span>{getMedalEmoji(player.best_rank) || '⭐'} Best: P{player.best_rank}</span>
                      )}
                    </div>
                  </div>
                  <div className="fol-ranking-score">
                    <div className="fol-score-val">{player.total_points}</div>
                    <div className="fol-score-lbl">pts</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>

    {selectedPlayer && (
      <FantasyPlayerModal player={selectedPlayer} onClose={closePlayer} seriesId={seriesId} />
    )}
    </>
  )
}


// ── Player Fantasy Matches Modal ─────────────────────────────
function FantasyPlayerModal({ player, onClose, seriesId = null }) {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    FantasyService.getFantasyPlayerMatches(player.user_id, seriesId)
      .then(data => setMatches(data.matches || []))
      .catch(err => setError(err.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [player.user_id, seriesId])

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr + 'T12:00:00').toLocaleDateString(undefined, {
      day: 'numeric', month: 'short', year: 'numeric'
    })
  }

  const rankLabel = (rank) => {
    const suffixes = ['st', 'nd', 'rd']
    const suffix = rank <= 3 ? suffixes[rank - 1] : 'th'
    return `P${rank}`
  }

  const medalFor = (rank) => {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return null
  }

  const getInitial = (name) => name?.charAt(0).toUpperCase() || '?'

  return (
    <div className="fol-modal-overlay" onClick={onClose}>
      <div className="fol-modal" onClick={(e) => e.stopPropagation()}>
        <div className="fol-modal-header">
          <div className="fol-modal-player">
            <div className="fol-modal-avatar">
              {player.profilePicture
                ? <img src={player.profilePicture} alt={player.display_name} />
                : <div className="fol-avatar-placeholder">{getInitial(player.display_name)}</div>
              }
            </div>
            <div>
              <div className="fol-modal-name">{player.display_name}</div>
              <div className="fol-modal-sub">Fantasy Match History</div>
            </div>
          </div>
          <button className="fol-modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="fol-modal-summary">
          <div className="fol-summary-item">
            <div className="fol-summary-val">{player.total_points}</div>
            <div className="fol-summary-lbl">Total Pts</div>
          </div>
          <div className="fol-summary-item">
            <div className="fol-summary-val">{player.matches_played}</div>
            <div className="fol-summary-lbl">Matches</div>
          </div>
          <div className="fol-summary-item">
            <div className="fol-summary-val">{player.average_points}</div>
            <div className="fol-summary-lbl">Avg Pts</div>
          </div>
          <div className="fol-summary-item">
            <div className="fol-summary-val">{player.best_rank ? `P${player.best_rank}` : '—'}</div>
            <div className="fol-summary-lbl">Best</div>
          </div>
        </div>

        <div className="fol-modal-body">
          {loading ? (
            <div className="fol-modal-loading"><div className="fol-spinner" /> Loading...</div>
          ) : error ? (
            <div className="fol-modal-error">⚠️ {error}</div>
          ) : matches.length === 0 ? (
            <div className="fol-modal-empty">No completed fantasy matches yet.</div>
          ) : (
            <div className="fol-match-list">
              {matches.map((m) => (
                <div key={m.match_id} className="fol-match-item">
                  <div className="fol-match-left">
                    <div className="fol-match-name">{m.short_name || m.match_name}</div>
                    <div className="fol-match-date">{formatDate(m.match_date)}</div>
                  </div>
                  <div className="fol-match-right">
                    <div className="fol-match-rank">
                      {medalFor(m.rank) && <span className="fol-match-medal">{medalFor(m.rank)}</span>}
                      <span className="fol-match-rank-label">{rankLabel(m.rank)}</span>
                    </div>
                    <div className="fol-match-pts">
                      <span className="fol-match-pts-earned">+{m.points_earned} pts</span>
                      <span className="fol-match-fantasy">{m.fantasy_points.toFixed(1)} fantasy</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FantasyOverallLeaderboard
