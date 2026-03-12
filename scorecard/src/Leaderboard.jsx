import { useState, useEffect } from 'react'
import AuthService from './services/AuthService'
import PlayerGames from './PlayerGames'
import './Leaderboard.css'

function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedPlayer, setSelectedPlayer] = useState(null)

  useEffect(() => {
    loadLeaderboard()
  }, [])

  const loadLeaderboard = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await AuthService.getLeaderboard()
      setLeaderboard(data.leaderboard || [])
    } catch (err) {
      setError(err.message || 'Failed to load leaderboard')
    } finally {
      setLoading(false)
    }
  }

  const handlePlayerClick = (player) => {
    setSelectedPlayer(player)
  }

  const handleClosePlayerGames = () => {
    setSelectedPlayer(null)
  }

  const getPlayerInitial = (name) => {
    return name?.charAt(0).toUpperCase() || '?'
  }

  const getMedalEmoji = (rank) => {
    if (rank === 1) return '🏆'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return null
  }

  if (loading) {
    return (
      <div className="leaderboard-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading leaderboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="leaderboard-container">
        <div className="error-state">
          <div className="error-icon">⚠️</div>
          <p>{error}</p>
          <button onClick={loadLeaderboard} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // Get top 3 for podium
  const top3 = leaderboard.slice(0, 3)
  const rest = leaderboard.slice(3)

  return (
    <div className="leaderboard-container">
      <div className="leaderboard-header">
        <h1 className="leaderboard-title">
          <span className="title-icon">🏆</span>
          Champions League
        </h1>
        <p className="leaderboard-subtitle">Top Fantasy Cricket Players</p>
      </div>

      {leaderboard.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🏏</div>
          <h3>No Rankings Yet</h3>
          <p>Be the first to play and climb the leaderboard!</p>
        </div>
      ) : (
        <>
          {/* Top 3 Podium */}
          {top3.length > 0 && (
            <div className="podium-section">
              <div className="podium-container">
                {/* 2nd Place */}
                {top3[1] && (
                  <div 
                    className="podium-card podium-second"
                    onClick={() => handlePlayerClick(top3[1])}
                  >
                    <div className="podium-rank-badge">2</div>
                    <div className="podium-avatar">
                      {top3[1].profilePicture ? (
                        <img src={top3[1].profilePicture} alt={top3[1].display_name} />
                      ) : (
                        <div className="avatar-placeholder silver">
                          {getPlayerInitial(top3[1].display_name)}
                        </div>
                      )}
                      <div className="medal-overlay">🥈</div>
                    </div>
                    <h3 className="podium-name">{top3[1].display_name}</h3>
                    <div className="podium-points">{top3[1].total_points.toLocaleString()}</div>
                    <div className="podium-label">Points</div>
                    <div className="podium-stats">
                      <span>{top3[1].matches_played} matches</span>
                      <span className="stat-divider">•</span>
                      <span>{top3[1].average_points} avg</span>
                    </div>
                  </div>
                )}

                {/* 1st Place */}
                {top3[0] && (
                  <div 
                    className="podium-card podium-first"
                    onClick={() => handlePlayerClick(top3[0])}
                  >
                    <div className="crown-icon">👑</div>
                    <div className="podium-rank-badge">1</div>
                    <div className="podium-avatar champion">
                      {top3[0].profilePicture ? (
                        <img src={top3[0].profilePicture} alt={top3[0].display_name} />
                      ) : (
                        <div className="avatar-placeholder gold">
                          {getPlayerInitial(top3[0].display_name)}
                        </div>
                      )}
                      <div className="medal-overlay">🏆</div>
                      <div className="glow-effect"></div>
                    </div>
                    <h3 className="podium-name">{top3[0].display_name}</h3>
                    <div className="podium-points champion-points">{top3[0].total_points.toLocaleString()}</div>
                    <div className="podium-label">Points</div>
                    <div className="podium-stats">
                      <span>{top3[0].matches_played} matches</span>
                      <span className="stat-divider">•</span>
                      <span>{top3[0].average_points} avg</span>
                    </div>
                  </div>
                )}

                {/* 3rd Place */}
                {top3[2] && (
                  <div 
                    className="podium-card podium-third"
                    onClick={() => handlePlayerClick(top3[2])}
                  >
                    <div className="podium-rank-badge">3</div>
                    <div className="podium-avatar">
                      {top3[2].profilePicture ? (
                        <img src={top3[2].profilePicture} alt={top3[2].display_name} />
                      ) : (
                        <div className="avatar-placeholder bronze">
                          {getPlayerInitial(top3[2].display_name)}
                        </div>
                      )}
                      <div className="medal-overlay">🥉</div>
                    </div>
                    <h3 className="podium-name">{top3[2].display_name}</h3>
                    <div className="podium-points">{top3[2].total_points.toLocaleString()}</div>
                    <div className="podium-label">Points</div>
                    <div className="podium-stats">
                      <span>{top3[2].matches_played} matches</span>
                      <span className="stat-divider">•</span>
                      <span>{top3[2].average_points} avg</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Rest of Rankings */}
          {rest.length > 0 && (
            <div className="rankings-section">
              <div className="section-header">
                <h2>All Rankings</h2>
                <div className="rankings-count">{leaderboard.length} Players</div>
              </div>
              
              <div className="rankings-grid">
                {rest.map((player, index) => {
                  const rank = index + 4
                  return (
                    <div 
                      key={player.user_id} 
                      className="ranking-card"
                      onClick={() => handlePlayerClick(player)}
                      style={{ animationDelay: `${index * 0.05}s` }}
                    >
                      <div className="ranking-position">
                        <div className="rank-number">{rank}</div>
                      </div>
                      
                      <div className="ranking-avatar">
                        {player.profilePicture ? (
                          <img src={player.profilePicture} alt={player.display_name} />
                        ) : (
                          <div className="avatar-placeholder">
                            {getPlayerInitial(player.display_name)}
                          </div>
                        )}
                      </div>

                      <div className="ranking-info">
                        <h4 className="ranking-name">{player.display_name}</h4>
                        <div className="ranking-meta">
                          <span className="meta-item">
                            <span className="meta-icon">🎮</span>
                            {player.matches_played}
                          </span>
                          <span className="meta-item">
                            <span className="meta-icon">📊</span>
                            {player.average_points} avg
                          </span>
                          {player.best_rank && (
                            <span className="meta-item">
                              <span className="meta-icon">{getMedalEmoji(player.best_rank) || '⭐'}</span>
                              Best: P{player.best_rank}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="ranking-score">
                        <div className="score-value">{player.total_points.toLocaleString()}</div>
                        <div className="score-label">pts</div>
                      </div>

                      <div className="ranking-arrow">→</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Player Games Modal */}
      {selectedPlayer && (
        <PlayerGames 
          player={selectedPlayer} 
          onClose={handleClosePlayerGames}
        />
      )}
    </div>
  )
}

export default Leaderboard
