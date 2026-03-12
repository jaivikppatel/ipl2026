import { useState, useEffect } from 'react'
import AuthService from './services/AuthService'
import './PlayerGames.css'

function PlayerGames({ player, onClose }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadPlayerGames()
  }, [player])

  const loadPlayerGames = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await AuthService.getPlayerGames(player.user_id)
      setGames(data.matches || [])
    } catch (err) {
      setError(err.message || 'Failed to load matches')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{player.display_name}'s IPL Matches</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="player-summary">
          <div className="summary-item">
            <div className="summary-label">Total Points</div>
            <div className="summary-value">{player.total_points}</div>
          </div>
          <div className="summary-item">
            <div className="summary-label">Matches</div>
            <div className="summary-value">{player.matches_played}</div>
          </div>
          <div className="summary-item">
            <div className="summary-label">Average</div>
            <div className="summary-value">{player.average_points} pts</div>
          </div>
          <div className="summary-item">
            <div className="summary-label">Best Rank</div>
            <div className="summary-value">{player.best_rank ? `P${player.best_rank}` : 'N/A'}</div>
          </div>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="loading">Loading games...</div>
          ) : error ? (
            <div className="error">{error}</div>
          ) : games.length === 0 ? (
            <div className="no-games">
              <p>No IPL matches found for this player.</p>
            </div>
          ) : (
            <div className="games-list">
              {games.map((game, index) => (
                <div key={game.id} className="game-card" style={{ animationDelay: `${index * 0.1}s` }}>
                  <div className="game-header">
                    <div className="game-date">{formatDate(game.match_date)}</div>
                    <div className="game-type">IPL Match</div>
                  </div>
                  
                  <div className="match-title">{game.match_name}</div>
                  
                  <div className="game-score">
                    <div className="score-label">Rank: P{game.user_rank}</div>
                    <div className="score-value">{game.points} pts</div>
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

export default PlayerGames
