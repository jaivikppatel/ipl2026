import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AuthService from './services/AuthService'
import FantasyService from './services/FantasyService'
import './FantasyLeaderboard.css'

function FantasyLeaderboard() {
  const { matchId } = useParams()
  const navigate = useNavigate()
  const [leaderboard, setLeaderboard] = useState([])
  const [match, setMatch] = useState(null)
  const [myBreakdown, setMyBreakdown] = useState([])
  const [activeTab, setActiveTab] = useState('leaderboard')
  const [loading, setLoading] = useState(true)
  const [viewingTeam, setViewingTeam] = useState(null)   // { display_name, players }
  const [teamModalLoading, setTeamModalLoading] = useState(false)
  const currentUserId = AuthService.getUser()?.id

  useEffect(() => {
    if (!AuthService.isAuthenticated()) { navigate('/login'); return }
    loadData()
  }, [matchId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [lbData, pointsData] = await Promise.all([
        FantasyService.getMatchLeaderboard(matchId),
        FantasyService.getPointsBreakdown(matchId),
      ])
      setLeaderboard(lbData.leaderboard || [])
      setMatch(lbData.match || null)
      setMyBreakdown(pointsData.breakdown || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  }

  const myEntry = leaderboard.find(e => e.is_current_user)
  const totalParticipants = leaderboard.length
  const canViewTeams = match?.status === 'live' || match?.status === 'completed'

  const handleRowClick = async (entry) => {
    if (!canViewTeams) return
    if (entry.is_current_user) {
      setActiveTab('my-points')
      return
    }
    setTeamModalLoading(true)
    setViewingTeam({ display_name: entry.display_name, players: null })
    try {
      const data = await FantasyService.getUserTeam(matchId, entry.user_id)
      setViewingTeam({ display_name: data.display_name, players: data.players })
    } catch (err) {
      setViewingTeam(null)
      alert(err.message)
    } finally {
      setTeamModalLoading(false)
    }
  }

  return (
    <div className="fl-container">
      {/* Header */}
      <div className="fl-header">
        <button className="fl-back-btn" onClick={() => navigate('/fantasy')}>←</button>
        <div className="fl-header-info">
          <h1>{match?.name || 'Leaderboard'}</h1>
          {match?.date && <span className="fl-date">{formatDate(match.date)}</span>}
        </div>
        {match?.status && (
          <span className={`fl-status-pill ${match.status}`}>
            {match.status === 'live' ? '🔴 LIVE' : match.status === 'completed' ? 'Final' : 'Upcoming'}
          </span>
        )}
      </div>

      {/* My rank banner */}
      {myEntry && (
        <div className="my-rank-banner">
          <div className="rank-banner-left">
            <div className="rank-label">Your Rank</div>
            <div className="rank-number">#{myEntry.rank || '—'}</div>
          </div>
          <div className="rank-banner-divider" />
          <div className="rank-banner-center">
            <div className="rank-label">Points</div>
            <div className="rank-points">{myEntry.total_points?.toFixed(1)}</div>
          </div>
          <div className="rank-banner-divider" />
          <div className="rank-banner-right">
            <div className="rank-label">C / VC</div>
            <div className="rank-cvc">
              {myEntry.captain_name?.split(' ')[0] || '—'} / {myEntry.vc_name?.split(' ')[0] || '—'}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="fl-tabs">
        <button
          className={`fl-tab ${activeTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('leaderboard')}
        >
          🏆 Leaderboard ({totalParticipants})
        </button>
        {myBreakdown.length > 0 && (
          <button
            className={`fl-tab ${activeTab === 'my-points' ? 'active' : ''}`}
            onClick={() => setActiveTab('my-points')}
          >
            📊 My Points
          </button>
        )}
      </div>

      {loading ? (
        <div className="fl-loading">
          <div className="spinner" />
          <p>Loading...</p>
        </div>
      ) : (
        <>
          {activeTab === 'leaderboard' && (
            <div className="fl-table-wrap">
              {leaderboard.length === 0 ? (
                <div className="fl-empty">
                  <div className="empty-icon">🏆</div>
                  <p>No teams submitted yet</p>
                </div>
              ) : (
                <table className="fl-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Player</th>
                      <th>C / VC</th>
                      <th>Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((entry, idx) => (
                      <tr
                        key={entry.user_id}
                        className={`${entry.is_current_user ? 'my-row' : ''} ${canViewTeams ? 'clickable-row' : ''}`}
                        onClick={() => handleRowClick(entry)}
                      >
                        <td className="rank-cell">
                          {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : entry.rank || idx + 1}
                        </td>
                        <td className="name-cell">
                          {entry.display_name}
                          {entry.is_current_user && <span className="you-badge"> (You)</span>}
                        </td>
                        <td className="cvc-cell">
                          <span className="c-name">{entry.captain_name?.split(' ').pop() || '—'}</span>
                          <span className="cvc-sep">/</span>
                          <span className="vc-name">{entry.vc_name?.split(' ').pop() || '—'}</span>
                        </td>
                        <td className="pts-cell">{entry.total_points?.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {activeTab === 'my-points' && (
            <div className="my-points-list">
              {myBreakdown.length === 0 ? (
                <div className="fl-empty">
                  <p>Points not yet available</p>
                </div>
              ) : (
                <>
                  <div className="total-points-header">
                    Total: {myBreakdown.reduce((s, p) => s + p.total_points, 0).toFixed(1)} pts
                  </div>
                  {[...myBreakdown]
                    .sort((a, b) => b.total_points - a.total_points)
                    .map(p => (
                      <div key={p.player_id} className={`mp-card ${p.is_captain ? 'mp-captain' : p.is_vice_captain ? 'mp-vc' : ''}`}>
                        <div className="mp-left">
                          {p.is_captain && <span className="mp-badge mp-badge-c">C</span>}
                          {p.is_vice_captain && <span className="mp-badge mp-badge-vc">VC</span>}
                          <div className="mp-info">
                            <div className="mp-name">{p.name}</div>
                            <div className="mp-meta">
                              {p.team_short} · <span className={`player-role-chip role-${p.role}`}>{p.role}</span>
                            </div>
                          </div>
                        </div>
                        <div className="mp-right">
                          <div className="mp-total-pts">{p.total_points.toFixed(1)}</div>
                          <div className="mp-base-pts">
                            {p.base_points.toFixed(1)} × {p.multiplier}
                          </div>
                          <div className="mp-stats">
                            {p.stats.runs > 0 && <span>{p.stats.runs}R</span>}
                            {p.stats.wickets > 0 && <span>{p.stats.wickets}W</span>}
                            {p.stats.catches > 0 && <span>{p.stats.catches}C</span>}
                            {p.stats.stumpings > 0 && <span>{p.stats.stumpings}St</span>}
                          </div>
                        </div>
                      </div>
                    ))
                  }
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Team View Modal */}
      {viewingTeam && (
        <div className="team-modal-overlay" onClick={() => setViewingTeam(null)}>
          <div className="team-modal" onClick={(e) => e.stopPropagation()}>
            <div className="team-modal-header">
              <h2>{viewingTeam.display_name}&apos;s Team</h2>
              <button className="team-modal-close" onClick={() => setViewingTeam(null)}>✕</button>
            </div>
            {teamModalLoading || !viewingTeam.players ? (
              <div className="fl-loading">
                <div className="spinner" />
                <p>Loading team...</p>
              </div>
            ) : (
              <div className="team-modal-body">
                {[...viewingTeam.players]
                  .sort((a, b) => b.total_points - a.total_points)
                  .map(p => (
                    <div key={p.player_id} className={`mp-card ${p.is_captain ? 'mp-captain' : p.is_vice_captain ? 'mp-vc' : ''}`}>
                      <div className="mp-left">
                        {p.is_captain && <span className="mp-badge mp-badge-c">C</span>}
                        {p.is_vice_captain && <span className="mp-badge mp-badge-vc">VC</span>}
                        <div className="mp-info">
                          <div className="mp-name">{p.name}</div>
                          <div className="mp-meta">
                            {p.team_short} · <span className={`player-role-chip role-${p.role}`}>{p.role}</span>
                          </div>
                        </div>
                      </div>
                      <div className="mp-right">
                        <div className="mp-total-pts">{p.total_points.toFixed(1)}</div>
                        {p.base_points > 0 && (
                          <div className="mp-base-pts">
                            {p.base_points.toFixed(1)} × {p.is_captain ? '2' : p.is_vice_captain ? '1.5' : '1'}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                }
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default FantasyLeaderboard
