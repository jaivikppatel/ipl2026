import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthService from './services/AuthService'
import FantasyService from './services/FantasyService'
import BottomNav from './BottomNav'
import './Fantasy.css'

function Fantasy() {
  const [matches, setMatches] = useState([])
  const [myTeams, setMyTeams] = useState({}) // matchId -> team or null
  const [loading, setLoading] = useState(true)
  const [showRules, setShowRules] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!AuthService.isAuthenticated()) {
      navigate('/login')
      return
    }
    loadMatches()
  }, [])

  const loadMatches = async () => {
    setLoading(true)
    try {
      const data = await FantasyService.getMatches()
      const matchList = data.matches || []
      setMatches(matchList)

      // Fetch "my team" status only for visible matches (live + next 5 upcoming + completed)
      const visibleIds = new Set([
        ...matchList.filter(m => m.status === 'live').map(m => m.id),
        ...matchList.filter(m => m.status === 'upcoming').slice(0, 5).map(m => m.id),
        ...matchList.filter(m => m.status === 'completed').map(m => m.id),
      ])
      const entries = await Promise.allSettled(
        matchList.filter(m => visibleIds.has(m.id)).map(m =>
          FantasyService.getMyTeam(m.id).then(res => [m.id, res.team])
        )
      )
      const teamsMap = {}
      entries.forEach(result => {
        if (result.status === 'fulfilled') {
          const [id, team] = result.value
          teamsMap[id] = team
        }
      })
      setMyTeams(teamsMap)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    // Append T12:00:00 so date-only strings aren't shifted to the previous day in
    // western timezones when JS parses them as UTC midnight.
    const d = new Date(dateStr.includes('T') ? dateStr + 'Z' : dateStr + 'T12:00:00')
    return d.toLocaleDateString(undefined, {
      weekday: 'short', day: 'numeric', month: 'short'
    })
  }

  const formatTime = (datetimeStr) => {
    if (!datetimeStr) return ''
    // datetimeStr is stored as naive UTC in the DB — append Z to mark it as UTC
    return new Date(datetimeStr + 'Z').toLocaleTimeString(undefined, {
      hour: '2-digit', minute: '2-digit', hour12: true, timeZoneName: 'short'
    })
  }

  const groupedMatches = {
    live: matches.filter(m => m.status === 'live'),
    upcoming: matches.filter(m => m.status === 'upcoming').slice(0, 5),
    completed: matches.filter(m => m.status === 'completed').reverse(),
  }

  const renderMatchCard = (match) => {
    const team = myTeams[match.id]
    const hasTeam = !!team
    const isLocked = team?.is_locked
    const deadlinePassed = match.match_datetime_gmt && new Date() >= new Date(match.match_datetime_gmt + 'Z')
    const canEdit = hasTeam && !isLocked && !deadlinePassed && match.status === 'upcoming'
    const canCreate = !hasTeam && !deadlinePassed && match.status === 'upcoming'
    const isLive = match.status === 'live'
    const isCompleted = match.status === 'completed'

    return (
      <div key={match.id} className="match-card">
        <div className="match-card-top">
          <span className={`status-pill ${match.status}`}>
            {match.status === 'live' ? '🔴 LIVE' : match.status === 'upcoming' ? 'Upcoming' : 'Completed'}
          </span>
          {match.squad_fetched && <span className="squad-badge">Squad Available</span>}
          {match.playing_xi_announced && <span className="squad-badge xi-badge">XI Announced</span>}
        </div>

        <div className="teams-row">
          <div className="team-col" style={{ '--team-color': match.team1?.color || '#333' }}>
            <div className="team-short">{match.team1?.short || '?'}</div>
            <div className="team-name">{match.team1?.name || 'TBD'}</div>
          </div>
          <div className="vs-divider">VS</div>
          <div className="team-col" style={{ '--team-color': match.team2?.color || '#333' }}>
            <div className="team-short">{match.team2?.short || '?'}</div>
            <div className="team-name">{match.team2?.name || 'TBD'}</div>
          </div>
        </div>

        <div className="match-meta">
          {match.match_date && <span>📅 {formatDate(match.match_date)}</span>}
          {match.match_datetime_gmt && <span>🕐 {formatTime(match.match_datetime_gmt)}</span>}
          {match.venue && <span className="venue-text">📍 {match.venue}</span>}
        </div>

        {isCompleted && match.status_note && (
          <div className="result-text">{match.status_note}</div>
        )}

        {(isLive || isCompleted) && match.live_score && match.live_score.length > 0 && (
          <div className="live-score-block">
            {match.live_score.map((inn, i) => {
              // Shorten inning label: "Mumbai Indians 1st Innings" → "MI 1st"
              const label = inn.inning || ''
              const short = label.replace(/\s+(innings|inning)$/i, '').replace(/\s+\d+(st|nd|rd|th)\s+/i, ' ')
              return (
                <div key={i} className="live-score-row">
                  <span className="live-score-label">{short}</span>
                  <span className="live-score-val">{inn.r}/{inn.w} ({inn.o} ov)</span>
                </div>
              )
            })}
          </div>
        )}

        {isLive && !match.status_note && (
          <div className="live-status-text">🔴 Match in progress</div>
        )}
        {isLive && match.status_note && (
          <div className="live-status-text">{match.status_note}</div>
        )}

        {hasTeam && (
          <div className="my-team-badge">
            ✓ Team Created
            {team.leaderboard && <span className="rank-chip">Rank #{team.leaderboard.rank || '—'} · {team.leaderboard.total_points?.toFixed(1) || 0} pts</span>}
          </div>
        )}

        <div className="match-actions">
          {canCreate && (
            <button
              className="action-btn create-btn"
              onClick={() => navigate(`/fantasy/match/${match.id}`)}
            >
              🏏 Create Team
            </button>
          )}
          {canEdit && (
            <button
              className="action-btn edit-btn"
              onClick={() => navigate(`/fantasy/match/${match.id}`)}
            >
              ✏️ Edit Team
            </button>
          )}
          {(isLive || isCompleted) && (
            <button
              className="action-btn leaderboard-btn"
              onClick={() => navigate(`/fantasy/match/${match.id}/leaderboard`)}
            >
              🏆 Leaderboard
            </button>
          )}
          {hasTeam && (isLive || isCompleted) && (
            <button
              className="action-btn view-btn"
              onClick={() => navigate(`/fantasy/match/${match.id}/leaderboard`)}
            >
              My Points
            </button>
          )}
          {isLive && !hasTeam && !deadlinePassed && (
            <button
              className="action-btn create-btn"
              onClick={() => navigate(`/fantasy/match/${match.id}`)}
            >
              🏏 Join Live
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="fantasy-container">
      <div className="fantasy-header">
        <div className="fantasy-header-top">
          <h1>🏏 Fantasy IPL 2026</h1>
          <button className="rules-btn" onClick={() => setShowRules(true)}>ℹ️ Rules</button>
        </div>
        <p className="fantasy-subtitle">Pick your dream team & beat your friends</p>
      </div>

      {loading ? (
        <div className="fantasy-loading">
          <div className="spinner" />
          <p>Loading matches...</p>
        </div>
      ) : matches.length === 0 ? (
        <div className="fantasy-empty">
          <div className="empty-icon">🏏</div>
          <h2>No Matches Yet</h2>
          <p>IPL 2026 schedule will appear here once loaded by the admin.</p>
        </div>
      ) : (
        <>
          {groupedMatches.live.length > 0 && (
            <section className="match-section">
              <h2 className="section-title live-title">🔴 Live Now</h2>
              <div className="matches-grid">
                {groupedMatches.live.map(renderMatchCard)}
              </div>
            </section>
          )}
          {groupedMatches.upcoming.length > 0 && (
            <section className="match-section">
              <h2 className="section-title">Upcoming Matches</h2>
              <div className="matches-grid">
                {groupedMatches.upcoming.map(renderMatchCard)}
              </div>
            </section>
          )}
          {groupedMatches.completed.length > 0 && (
            <section className="match-section">
              <h2 className="section-title">Completed</h2>
              <div className="matches-grid">
                {groupedMatches.completed.map(renderMatchCard)}
              </div>
            </section>
          )}
        </>
      )}

      <BottomNav />

      {showRules && (
        <div className="rules-overlay" onClick={() => setShowRules(false)}>
          <div className="rules-modal" onClick={(e) => e.stopPropagation()}>
            <div className="rules-modal-header">
              <h2>📋 Scoring Rules</h2>
              <button className="rules-close-btn" onClick={() => setShowRules(false)}>✕</button>
            </div>
            <div className="rules-modal-body">
              <p className="rules-multiplier-note">
                🌟 <strong>Captain</strong> earns <strong>2×</strong> points &nbsp;|&nbsp; 🥈 <strong>Vice-Captain</strong> earns <strong>1.5×</strong> points
              </p>

              <h3 className="rules-section-title">🏏 Batting</h3>
              <table className="rules-table">
                <tbody>
                  <tr><td>Run scored</td><td className="pts-pos">+1 / run</td></tr>
                  <tr><td>Four bonus</td><td className="pts-pos">+1 / four</td></tr>
                  <tr><td>Six bonus</td><td className="pts-pos">+3 / six</td></tr>
                  <tr><td>30+ runs milestone</td><td className="pts-pos">+4</td></tr>
                  <tr><td>50+ runs milestone</td><td className="pts-pos">+10</td></tr>
                  <tr><td>100+ runs milestone</td><td className="pts-pos">+20</td></tr>
                  <tr><td>Duck (dismissed for 0)</td><td className="pts-neg">−2</td></tr>
                  <tr><td colSpan={2} className="rules-subheading">Strike Rate (min 10 balls)</td></tr>
                  <tr><td>SR &gt; 170</td><td className="pts-pos">+6</td></tr>
                  <tr><td>SR 150–170</td><td className="pts-pos">+4</td></tr>
                  <tr><td>SR 130–150</td><td className="pts-pos">+2</td></tr>
                  <tr><td>SR &lt; 50</td><td className="pts-neg">−6</td></tr>
                  <tr><td>SR 50–70</td><td className="pts-neg">−4</td></tr>
                  <tr><td>SR 70–100</td><td className="pts-neg">−2</td></tr>
                </tbody>
              </table>

              <h3 className="rules-section-title">🎾 Bowling</h3>
              <table className="rules-table">
                <tbody>
                  <tr><td>Wicket</td><td className="pts-pos">+25 / wicket</td></tr>
                  <tr><td>3-wicket haul bonus</td><td className="pts-pos">+4</td></tr>
                  <tr><td>4-wicket haul bonus</td><td className="pts-pos">+8</td></tr>
                  <tr><td>5-wicket haul bonus</td><td className="pts-pos">+16</td></tr>
                  <tr><td>Maiden over</td><td className="pts-pos">+12 / maiden</td></tr>
                  <tr><td colSpan={2} className="rules-subheading">Economy Rate (min 2 overs)</td></tr>
                  <tr><td>Economy ≤ 5</td><td className="pts-pos">+6</td></tr>
                  <tr><td>Economy ≤ 6</td><td className="pts-pos">+4</td></tr>
                  <tr><td>Economy ≤ 7</td><td className="pts-pos">+2</td></tr>
                  <tr><td>Economy ≥ 10</td><td className="pts-neg">−2</td></tr>
                  <tr><td>Economy ≥ 11</td><td className="pts-neg">−4</td></tr>
                  <tr><td>Economy ≥ 12</td><td className="pts-neg">−6</td></tr>
                </tbody>
              </table>

              <h3 className="rules-section-title">🧤 Fielding</h3>
              <table className="rules-table">
                <tbody>
                  <tr><td>Catch</td><td className="pts-pos">+8 / catch</td></tr>
                  <tr><td>Stumping</td><td className="pts-pos">+12 / stumping</td></tr>
                  <tr><td>Direct run-out</td><td className="pts-pos">+12</td></tr>
                  <tr><td>Indirect run-out</td><td className="pts-pos">+6</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Fantasy
