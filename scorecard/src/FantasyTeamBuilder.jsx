import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AuthService from './services/AuthService'
import FantasyService from './services/FantasyService'
import './FantasyTeamBuilder.css'

const ROLES = ['WK', 'BAT', 'AR', 'BOWL']
const ROLE_LABELS = { WK: 'Wicket-Keepers', BAT: 'Batsmen', AR: 'All-Rounders', BOWL: 'Bowlers' }
const ROLE_ICONS = { WK: '🧤', BAT: '🏏', AR: '⚡', BOWL: '🎾' }
const TEAM_SIZE = 11
const MAX_CREDITS = 100.0
const MAX_FROM_ONE_TEAM = 7

const ROLE_MINS = { WK: 1, BAT: 3, AR: 1, BOWL: 3 }

function FantasyTeamBuilder() {
  const { matchId } = useParams()
  const navigate = useNavigate()

  const [step, setStep] = useState(1) // 1 = select players, 2 = pick C/VC
  const [players, setPlayers] = useState([])
  const [selected, setSelected] = useState(new Set()) // player IDs
  const [captain, setCaptain] = useState(null)
  const [viceCaptain, setViceCaptain] = useState(null)
  const [activeRole, setActiveRole] = useState('WK')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [squadAnnounced, setSquadAnnounced] = useState(false)
  const [playingXiAnnounced, setPlayingXiAnnounced] = useState(false)
  const [matchInfo, setMatchInfo] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!AuthService.isAuthenticated()) { navigate('/login'); return }
    loadData()
  }, [matchId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [playersData, matchesData, myTeamData] = await Promise.all([
        FantasyService.getMatchPlayers(matchId),
        FantasyService.getMatches(),
        FantasyService.getMyTeam(matchId),
      ])

      setPlayers(playersData.players || [])
      setSquadAnnounced(playersData.squad_announced || false)
      setPlayingXiAnnounced(playersData.playing_xi_announced || false)

      const match = (matchesData.matches || []).find(m => String(m.id) === String(matchId))
      setMatchInfo(match || null)

      // Pre-fill existing team
      if (myTeamData.team) {
        const existingPlayers = myTeamData.team.players || []
        setSelected(new Set(existingPlayers.map(p => p.player_id)))
        const cap = existingPlayers.find(p => p.is_captain)
        const vc = existingPlayers.find(p => p.is_vice_captain)
        if (cap) setCaptain(cap.player_id)
        if (vc) setViceCaptain(vc.player_id)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const playerById = (id) => players.find(p => p.id === id)

  const selectedPlayers = [...selected].map(id => playerById(id)).filter(Boolean)
  const totalCredits = selectedPlayers.reduce((s, p) => s + p.credits, 0)
  const remainingCredits = MAX_CREDITS - totalCredits

  const teamCounts = {}
  selectedPlayers.forEach(p => {
    teamCounts[p.team_short] = (teamCounts[p.team_short] || 0) + 1
  })

  // Role counts (WK counts as BAT too)
  const roleCounts = { WK: 0, BAT: 0, AR: 0, BOWL: 0 }
  selectedPlayers.forEach(p => {
    roleCounts[p.role] = (roleCounts[p.role] || 0) + 1
    if (p.role === 'WK') roleCounts['BAT'] = (roleCounts['BAT'] || 0) + 1
  })

  const validationErrors = () => {
    const errs = []
    if (selected.size !== TEAM_SIZE) errs.push(`Select exactly ${TEAM_SIZE} players (${selected.size} selected)`)
    if (totalCredits > MAX_CREDITS) errs.push(`Credits ${totalCredits.toFixed(1)} exceed ${MAX_CREDITS} limit`)
    for (const [team, cnt] of Object.entries(teamCounts)) {
      if (cnt > MAX_FROM_ONE_TEAM) errs.push(`Max ${MAX_FROM_ONE_TEAM} from one team (${team}: ${cnt})`)
    }
    for (const [role, min] of Object.entries(ROLE_MINS)) {
      if ((roleCounts[role] || 0) < min) {
        errs.push(`Need at least ${min} ${ROLE_LABELS[role]}`)
      }
    }
    return errs
  }

  const canProceed = validationErrors().length === 0 && selected.size === TEAM_SIZE
  const canSubmit = captain && viceCaptain && captain !== viceCaptain

  const togglePlayer = (player) => {
    if (selected.has(player.id)) {
      const next = new Set(selected)
      next.delete(player.id)
      setSelected(next)
      if (captain === player.id) setCaptain(null)
      if (viceCaptain === player.id) setViceCaptain(null)
      setError('')
      return
    }

    // Checks before adding
    if (selected.size >= TEAM_SIZE) {
      setError('Team is full (11 players)')
      return
    }
    const playerCredits = totalCredits + player.credits
    if (playerCredits > MAX_CREDITS) {
      setError(`Adding this player (${player.credits}cr) would exceed the ${MAX_CREDITS}cr limit`)
      return
    }
    const teamCount = teamCounts[player.team_short] || 0
    if (teamCount >= MAX_FROM_ONE_TEAM) {
      setError(`Max ${MAX_FROM_ONE_TEAM} players from ${player.team_short}`)
      return
    }
    setError('')
    setSelected(new Set([...selected, player.id]))
  }

  const setCaptainVC = (playerId) => {
    if (captain === playerId) {
      setCaptain(null)
    } else if (viceCaptain === playerId) {
      setViceCaptain(null)
    } else if (!captain) {
      setCaptain(playerId)
    } else if (!viceCaptain) {
      setViceCaptain(playerId)
    } else {
      // Replace captain
      setCaptain(playerId)
    }
  }

  const handleSubmit = async () => {
    if (!canSubmit) return
    setSaving(true)
    setError('')
    try {
      const teamPayload = selectedPlayers.map(p => ({
        player_id: p.id,
        is_captain: p.id === captain,
        is_vice_captain: p.id === viceCaptain,
      }))
      await FantasyService.submitTeam(matchId, teamPayload)
      navigate('/fantasy')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const filteredPlayers = players.filter(p => p.role === activeRole)

  if (loading) {
    return (
      <div className="ftb-container">
        <div className="ftb-loading">
          <div className="spinner" />
          <p>Loading players...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="ftb-container">
      {/* Header */}
      <div className="ftb-header">
        <button className="ftb-back-btn" onClick={() => navigate('/fantasy')}>←</button>
        <div className="ftb-header-info">
          <h1>{matchInfo?.short_name || matchInfo?.match_name || 'Create Team'}</h1>
          {matchInfo?.match_date && (
            <span className="ftb-header-date">
              {new Date(matchInfo.match_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
            </span>
          )}
        </div>
        {squadAnnounced && <span className="squad-badge-small">Squad Available</span>}
        {playingXiAnnounced && <span className="squad-badge-small xi-badge-small">XI Set</span>}
      </div>

      {/* Credit & player count bar */}
      <div className="ftb-credit-bar">
        <div className="credit-info">
          <span className={`credit-count ${remainingCredits < 5 ? 'low' : ''}`}>
            {remainingCredits.toFixed(1)} cr left
          </span>
          <span className="player-count">{selected.size}/{TEAM_SIZE} players</span>
        </div>
        <div className="credit-progress">
          <div
            className="credit-fill"
            style={{ width: `${Math.min(100, (totalCredits / MAX_CREDITS) * 100)}%` }}
          />
        </div>
        <div className="role-counts">
          {ROLES.map(r => (
            <span key={r} className={`rc-chip ${roleCounts[r] < ROLE_MINS[r] ? 'rc-warn' : 'rc-ok'}`}>
              {ROLE_ICONS[r]} {roleCounts[r]}
            </span>
          ))}
        </div>
      </div>

      {/* Step tabs */}
      <div className="ftb-steps">
        <button className={`step-btn ${step === 1 ? 'active' : ''}`} onClick={() => setStep(1)}>
          1. Select Players
        </button>
        <button
          className={`step-btn ${step === 2 ? 'active' : ''}`}
          onClick={() => canProceed && setStep(2)}
          disabled={!canProceed}
        >
          2. Captain &amp; VC
        </button>
      </div>

      {error && <div className="ftb-error">{error}</div>}

      {step === 1 && (
        <>
          {/* Role tab bar */}
          <div className="role-tabs">
            {ROLES.map(role => {
              const cnt = players.filter(p => p.role === role).length
              return (
                <button
                  key={role}
                  className={`role-tab ${activeRole === role ? 'active' : ''}`}
                  onClick={() => setActiveRole(role)}
                >
                  {ROLE_ICONS[role]} {role}
                  <span className="role-tab-count">{cnt}</span>
                </button>
              )
            })}
          </div>

          <div className="player-list">
            {filteredPlayers.length === 0 && (
              <div className="no-players">No {ROLE_LABELS[activeRole]} available</div>
            )}
            {filteredPlayers.map(player => {
              const isSelected = selected.has(player.id)
              const wouldExceedCredits = !isSelected && totalCredits + player.credits > MAX_CREDITS
              const teamFull = !isSelected && (teamCounts[player.team_short] || 0) >= MAX_FROM_ONE_TEAM
              const totalFull = !isSelected && selected.size >= TEAM_SIZE
              const disabled = wouldExceedCredits || teamFull || totalFull

              return (
                <div
                  key={player.id}
                  className={`player-card ${isSelected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
                  onClick={() => !disabled || isSelected ? togglePlayer(player) : setError(
                    totalFull ? 'Team is full' :
                    wouldExceedCredits ? `Not enough credits` :
                    `Max ${MAX_FROM_ONE_TEAM} from ${player.team_short}`
                  )}
                >
                  <div className="player-left">
                    <div className="player-avatar" style={{ background: player.team_color || '#333' }}>
                      {player.name.charAt(0)}
                    </div>
                    <div className="player-info">
                      <div className="player-name">
                        {player.name}
                        {player.is_playing_xi && <span className="xi-chip">XI</span>}
                      </div>
                      <div className="player-meta">
                        <span className="player-team">{player.team_short}</span>
                        <span className={`player-role-chip role-${player.role}`}>{player.role}</span>
                      </div>
                    </div>
                  </div>
                  <div className="player-right">
                    <div className="player-credits">{player.credits} cr</div>
                    {isSelected && <div className="selected-tick">✓</div>}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="ftb-footer">
            {validationErrors().length > 0 && (
              <div className="validation-hints">
                {validationErrors().map((e, i) => <div key={i} className="hint-item">{e}</div>)}
              </div>
            )}
            <button
              className="proceed-btn"
              disabled={!canProceed}
              onClick={() => setStep(2)}
            >
              Next: Pick Captain & VC →
            </button>
          </div>
        </>
      )}

      {step === 2 && (
        <>
          <div className="cvc-instructions">
            <p>Tap a player to set as <strong>C</strong> (2x pts) or <strong>VC</strong> (1.5x pts).</p>
          </div>
          <div className="cvc-list">
            {selectedPlayers.map(player => {
              const isCap = captain === player.id
              const isVC = viceCaptain === player.id
              return (
                <div
                  key={player.id}
                  className={`cvc-card ${isCap ? 'is-captain' : isVC ? 'is-vc' : ''}`}
                  onClick={() => setCaptainVC(player.id)}
                >
                  <div className="cvc-avatar" style={{ background: player.team_color || '#333' }}>
                    {player.name.charAt(0)}
                  </div>
                  <div className="cvc-info">
                    <div className="cvc-name">{player.name}</div>
                    <div className="cvc-meta">
                      <span>{player.team_short}</span>
                      <span className={`player-role-chip role-${player.role}`}>{player.role}</span>
                    </div>
                  </div>
                  <div className="cvc-badge-area">
                    {isCap && <span className="badge badge-captain">C</span>}
                    {isVC && <span className="badge badge-vc">VC</span>}
                    {!isCap && !isVC && <span className="badge badge-none">—</span>}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="ftb-footer">
            {!canSubmit && (
              <div className="validation-hints">
                {!captain && <div className="hint-item">Select a Captain (C)</div>}
                {!viceCaptain && <div className="hint-item">Select a Vice-Captain (VC)</div>}
              </div>
            )}
            <div className="submit-actions">
              <button className="back-step-btn" onClick={() => setStep(1)}>← Back</button>
              <button
                className="submit-btn"
                disabled={!canSubmit || saving}
                onClick={handleSubmit}
              >
                {saving ? 'Saving...' : '✓ Save Team'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default FantasyTeamBuilder
