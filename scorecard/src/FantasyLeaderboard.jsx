import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AuthService from './services/AuthService'
import FantasyService from './services/FantasyService'
import PlayerAvatar from './PlayerAvatar'
import './FantasyLeaderboard.css'

/**
 * Reconstruct a per-line breakdown of how base_points were earned.
 * Mirrors fantasy_points.py calculate_player_points().
 * stats shape: { runs, balls, fours, sixes, wickets, catches, stumpings }
 * Additional bowling stats may come from the player-scores endpoint:
 *   { balls_bowled, runs_conceded, maidens }
 * Returns an array of { label, points } — only non-zero items — plus
 * a summary row for the multiplier if C or VC.
 */
function getPointBreakdown(stats, isCapt, isVc) {
  if (!stats) return []
  const lines = []

  // ── Batting ──────────────────────────────────────────
  const runs = stats.runs ?? stats.runs_scored ?? 0
  const balls = stats.balls ?? stats.balls_faced ?? 0
  const fours = stats.fours ?? 0
  const sixes = stats.sixes ?? 0

  if (runs > 0) lines.push({ label: `${runs} run${runs !== 1 ? 's' : ''}`, points: runs * 0.5 })
  if (fours > 0) lines.push({ label: `${fours} four${fours !== 1 ? 's' : ''} (bonus)`, points: fours * 1 })
  if (sixes > 0) lines.push({ label: `${sixes} six${sixes !== 1 ? 'es' : ''} (bonus)`, points: sixes * 2 })

  if (runs >= 100) lines.push({ label: '100+ runs milestone', points: 16 })
  else if (runs >= 50) lines.push({ label: '50+ runs milestone', points: 8 })
  else if (runs >= 30) lines.push({ label: '30+ runs milestone', points: 4 })

  // Duck penalty: we detect from stats — runs=0 and dismissed (stats.is_dismissed or stats.duck)
  if (runs === 0 && (stats.is_dismissed || stats.duck)) {
    lines.push({ label: 'Duck', points: -2 })
  }

  // Strike rate (min 10 balls)
  if (balls >= 10) {
    const sr = (runs / balls) * 100
    if (sr > 170) lines.push({ label: `SR ${sr.toFixed(1)} (>170)`, points: 6 })
    else if (sr >= 150) lines.push({ label: `SR ${sr.toFixed(1)} (150–170)`, points: 4 })
    else if (sr >= 130) lines.push({ label: `SR ${sr.toFixed(1)} (130–150)`, points: 2 })
    else if (sr < 50) lines.push({ label: `SR ${sr.toFixed(1)} (<50)`, points: -6 })
    else if (sr < 70) lines.push({ label: `SR ${sr.toFixed(1)} (50–70)`, points: -4 })
    else if (sr < 100) lines.push({ label: `SR ${sr.toFixed(1)} (70–100)`, points: -2 })
  }

  // ── Bowling ───────────────────────────────────────────
  const wickets = stats.wickets ?? 0
  const ballsBowled = stats.balls_bowled ?? 0
  const runsConceded = stats.runs_conceded ?? 0
  const maidens = stats.maidens ?? 0

  if (wickets > 0) lines.push({ label: `${wickets} wicket${wickets !== 1 ? 's' : ''}`, points: wickets * 25 })
  if (wickets >= 5) lines.push({ label: '5-wicket haul bonus', points: 16 })
  else if (wickets >= 4) lines.push({ label: '4-wicket haul bonus', points: 8 })
  else if (wickets >= 3) lines.push({ label: '3-wicket haul bonus', points: 4 })
  if (maidens > 0) lines.push({ label: `${maidens} maiden${maidens !== 1 ? 's' : ''}`, points: maidens * 12 })

  if (ballsBowled >= 12) {
    const overs = ballsBowled / 6
    const econ = runsConceded / overs
    if (econ <= 5) lines.push({ label: `Economy ${econ.toFixed(2)} (≤5)`, points: 6 })
    else if (econ <= 6) lines.push({ label: `Economy ${econ.toFixed(2)} (≤6)`, points: 4 })
    else if (econ <= 7) lines.push({ label: `Economy ${econ.toFixed(2)} (≤7)`, points: 2 })
    else if (econ >= 12) lines.push({ label: `Economy ${econ.toFixed(2)} (≥12)`, points: -6 })
    else if (econ >= 11) lines.push({ label: `Economy ${econ.toFixed(2)} (≥11)`, points: -4 })
    else if (econ >= 10) lines.push({ label: `Economy ${econ.toFixed(2)} (≥10)`, points: -2 })
  }

  // ── Fielding ──────────────────────────────────────────
  const catches = stats.catches ?? 0
  const stumpings = stats.stumpings ?? 0
  const runOutsDirect = stats.run_outs_direct ?? 0
  const runOutsIndirect = stats.run_outs_indirect ?? 0

  if (catches > 0) lines.push({ label: `${catches} catch${catches !== 1 ? 'es' : ''}`, points: catches * 8 })
  if (stumpings > 0) lines.push({ label: `${stumpings} stumping${stumpings !== 1 ? 's' : ''}`, points: stumpings * 12 })
  if (runOutsDirect > 0) lines.push({ label: `${runOutsDirect} direct run-out${runOutsDirect !== 1 ? 's' : ''}`, points: runOutsDirect * 12 })
  if (runOutsIndirect > 0) lines.push({ label: `${runOutsIndirect} indirect run-out${runOutsIndirect !== 1 ? 's' : ''}`, points: runOutsIndirect * 6 })

  return lines
}

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
  const [selectedPlayer, setSelectedPlayer] = useState(null) // player for breakdown modal
  const [playerScores, setPlayerScores] = useState([])       // match-level player scores
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
      const matchData = lbData.match || null
      setLeaderboard(lbData.leaderboard || [])
      setMatch(matchData)
      setMyBreakdown(pointsData.breakdown || [])

      // Load player scores for live/completed matches
      if (matchData?.status === 'live' || matchData?.status === 'completed') {
        try {
          const scoresData = await FantasyService.getMatchPlayerScores(matchId)
          setPlayerScores(scoresData.players || [])
        } catch (_) {
          // non-fatal
        }
      }
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
        {(match?.status === 'live' || match?.status === 'completed') && (
          <button
            className={`fl-tab ${activeTab === 'scores' ? 'active' : ''}`}
            onClick={() => setActiveTab('scores')}
          >
            🏏 Scores
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
                          <div className="name-cell-inner">
                            <div className="user-avatar-sm">
                              {entry.profile_picture
                                ? <img src={entry.profile_picture} alt={entry.display_name} className="user-avatar-sm-img" />
                                : <span className="user-avatar-sm-initials">{entry.display_name?.charAt(0).toUpperCase()}</span>
                              }
                            </div>
                            <span>
                              {entry.display_name}
                              {entry.is_current_user && <span className="you-badge"> (You)</span>}
                            </span>
                          </div>
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
                      <div
                        key={p.player_id}
                        className={`mp-card clickable-player ${p.is_captain ? 'mp-captain' : p.is_vice_captain ? 'mp-vc' : ''}`}
                        onClick={() => setSelectedPlayer(p)}
                      >
                        <div className="mp-left">
                          <PlayerAvatar
                            imageUrl={p.image_url}
                            name={p.name}
                            teamColor={p.team_color}
                            className="mp-avatar"
                          />
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

          {activeTab === 'scores' && (
            <div className="scores-list">
              {playerScores.length === 0 ? (
                <div className="fl-empty">
                  <div className="empty-icon">🏏</div>
                  <p>No player scores yet</p>
                </div>
              ) : (
                playerScores.map(p => (
                  <div
                    key={p.player_id}
                    className="scores-row clickable-player"
                    onClick={() => setSelectedPlayer({ ...p, multiplier: 1.0, total_points: p.base_points, is_captain: false, is_vice_captain: false })}
                  >
                    <PlayerAvatar
                      imageUrl={p.image_url}
                      name={p.name}
                      teamColor={p.team_color}
                      className="scores-avatar"
                    />
                    <div className="scores-info">
                      <div className="scores-name">{p.name}</div>
                      <div className="scores-meta">
                        {p.team_short} · <span className={`player-role-chip role-${p.role}`}>{p.role}</span>
                      </div>
                    </div>
                    <div className="scores-pts">{p.base_points.toFixed(1)}</div>
                  </div>
                ))
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
                    <div
                      key={p.player_id}
                      className={`mp-card clickable-player ${p.is_captain ? 'mp-captain' : p.is_vice_captain ? 'mp-vc' : ''}`}
                      onClick={() => setSelectedPlayer(p)}
                    >
                      <div className="mp-left">
                        <PlayerAvatar
                          imageUrl={p.image_url}
                          name={p.name}
                          teamColor={p.team_color}
                          className="mp-avatar"
                        />
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
      {/* Player Point Breakdown Modal */}
      {selectedPlayer && (() => {
        const lines = getPointBreakdown(
          selectedPlayer.stats,
          selectedPlayer.is_captain,
          selectedPlayer.is_vice_captain
        )
        const base = selectedPlayer.base_points ?? 0
        const multiplier = selectedPlayer.multiplier ?? (selectedPlayer.is_captain ? 2.0 : selectedPlayer.is_vice_captain ? 1.5 : 1.0)
        const total = selectedPlayer.total_points ?? base * multiplier
        const roleLabel = selectedPlayer.is_captain ? ' (C)' : selectedPlayer.is_vice_captain ? ' (VC)' : ''
        return (
          <div className="bd-overlay" onClick={() => setSelectedPlayer(null)}>
            <div className="bd-modal" onClick={(e) => e.stopPropagation()}>
              <div className="bd-header">
                <div>
                  <div className="bd-player-name">{selectedPlayer.name}{roleLabel}</div>
                  <div className="bd-player-meta">
                    {selectedPlayer.team_short} · <span className={`player-role-chip role-${selectedPlayer.role}`}>{selectedPlayer.role}</span>
                  </div>
                </div>
                <button className="bd-close-btn" onClick={() => setSelectedPlayer(null)}>✕</button>
              </div>
              <div className="bd-body">
                {lines.length === 0 ? (
                  <p className="bd-no-points">No points scored yet</p>
                ) : (
                  <table className="bd-table">
                    <tbody>
                      {lines.map((line, i) => (
                        <tr key={i}>
                          <td className="bd-label">{line.label}</td>
                          <td className={`bd-pts ${line.points >= 0 ? 'pts-pos' : 'pts-neg'}`}>
                            {line.points >= 0 ? '+' : ''}{line.points % 1 === 0 ? line.points : line.points.toFixed(1)}
                          </td>
                        </tr>
                      ))}
                      <tr className="bd-base-row">
                        <td>Base total</td>
                        <td className="bd-pts">{base.toFixed(1)}</td>
                      </tr>
                      {multiplier !== 1.0 && (
                        <tr className="bd-mult-row">
                          <td>{selectedPlayer.is_captain ? '👑 Captain 2×' : '🥈 Vice-Captain 1.5×'}</td>
                          <td className="bd-pts pts-pos">× {multiplier}</td>
                        </tr>
                      )}
                    </tbody>
                    <tfoot>
                      <tr className="bd-total-row">
                        <td>Total</td>
                        <td className="bd-total-pts">{total.toFixed(1)}</td>
                      </tr>
                    </tfoot>
                  </table>
                )}
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

export default FantasyLeaderboard
