import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthService from './services/AuthService'
import AdminService from './services/AdminService'
import FantasyService from './services/FantasyService'
import BottomNav from './BottomNav'
import './Admin.css'

function Admin() {
  const [activeTab, setActiveTab] = useState('fantasy')
  const [games, setGames] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [modalType, setModalType] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [formData, setFormData] = useState({})
  const [fantasyPoints, setFantasyPoints] = useState({})
  const [users, setUsers] = useState([])
  const [fantasyPlayers, setFantasyPlayers] = useState([])
  const [fantasyApiUsage, setFantasyApiUsage] = useState({})
  const [fantasyMatches, setFantasyMatches] = useState([])
  const [fantasySeries, setFantasySeries] = useState([])
  const [newSeriesName, setNewSeriesName] = useState('')
  const [newSeriesTournamentId, setNewSeriesTournamentId] = useState('')
  const [newSeriesTournamentType, setNewSeriesTournamentType] = useState('intl')
  const [editingPlayer, setEditingPlayer] = useState({})
  // Series pricing & access management
  const [seriesEditModal, setSeriesEditModal] = useState(null) // null or series object
  const [seriesEditPrice, setSeriesEditPrice] = useState('')
  const [seriesEditMessage, setSeriesEditMessage] = useState('')
  const [seriesAccessPanel, setSeriesAccessPanel] = useState(null) // open series_id
  const [seriesAccessUsers, setSeriesAccessUsers] = useState([])
  const [seriesAccessLoading, setSeriesAccessLoading] = useState(false)
  const [whitelistInput, setWhitelistInput] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const user = AuthService.getUser()
    if (!user?.isAdmin) {
      navigate('/dashboard')
      return
    }
    loadData()
  }, [activeTab, navigate])

  const loadData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'schedule' || activeTab === 'rankings') {
        const data = await AdminService.getGames()
        setGames(data.games || [])
      }
      if (activeTab === 'profiles' || activeTab === 'schedule') {
        const data = await AdminService.getScoringProfiles()
        setProfiles(data.profiles || [])
      }
      if (activeTab === 'fantasy') {
        const [usageData, matchesData, playersData, seriesData] = await Promise.all([
          FantasyService.adminGetApiUsage(),
          FantasyService.adminGetMatches(),
          FantasyService.adminGetPlayers(),
          FantasyService.adminGetSeries(),
        ])
        setFantasyApiUsage(usageData || {})
        setFantasyMatches(matchesData.matches || [])
        setFantasyPlayers(playersData.players || [])
        setFantasySeries(seriesData.series || [])
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const openModal = (type, item = null) => {
    setModalType(type)
    setSelectedItem(item)
    setShowModal(true)
    
    if (type === 'addGame') {
      setFormData({
        match_name: '',
        match_date: new Date().toISOString().split('T')[0],
        match_time: '19:30',
        venue: '',
        scoring_profile_id: profiles.find(p => p.is_default)?.id || null
      })
    } else if (type === 'editProfile' && item) {
      setFormData({...item})
    } else if (type === 'addProfile') {
      setFormData({
        name: '',
        description: '',
        point_distribution: {"1": 25, "2": 18, "3": 15, "4": 12, "5": 10, "6": 8, "7": 6, "8": 4, "9": 2, "10": 1},
        is_multiplier: false,
        multiplier: 1.0,
        max_ranks: 10
      })
    }
  }

  const handleGameSubmit = async (e) => {
    e.preventDefault()
    try {
      await AdminService.createGame(formData)
      setShowModal(false)
      loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleProfileSubmit = async (e) => {
    e.preventDefault()
    try {
      if (selectedItem) {
        await AdminService.updateScoringProfile(selectedItem.id, formData)
      } else {
        await AdminService.createScoringProfile(formData)
      }
      setShowModal(false)
      loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleDeleteGame = async (gameId, event) => {
    if (event) event.stopPropagation()
    if (!window.confirm('Delete this game?')) return
    try {
      await AdminService.deleteGame(gameId)
      loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleDeleteProfile = async (profileId, event) => {
    if (event) event.stopPropagation()
    if (!window.confirm('Delete this profile?')) return
    try {
      await AdminService.deleteScoringProfile(profileId)
      loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  const loadPointsEntry = async (game) => {
    try {
      const data = await AdminService.getGameRankings(game.id)
      setSelectedItem(game)
      setUsers(data.users || [])
      
      const pointsMap = {}
      if (data.rankings && Array.isArray(data.rankings)) {
        data.rankings.forEach(r => {
          pointsMap[r.user_id] = r.fantasy_points || 0
        })
      }
      setFantasyPoints(pointsMap)
      setModalType('enterPoints')
      setShowModal(true)
    } catch (err) {
      console.error('Error loading points entry:', err)
      alert('Error: ' + (err.message || 'Failed to load game rankings'))
    }
  }

  const handlePointsSubmit = async () => {
    const entries = Object.entries(fantasyPoints)
      .filter(([_, points]) => points > 0)
      .map(([userId, points]) => ({
        user_id: parseInt(userId),
        fantasy_points: parseInt(points)
      }))

    if (entries.length === 0) {
      alert('Please enter fantasy points for at least one player')
      return
    }

    try {
      await AdminService.submitRankings({
        game_id: selectedItem.id,
        points: entries
      })
      setShowModal(false)
      setFantasyPoints({})
      loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  const applyProfileTemplate = (template) => {
    let dist = {}
    if (template === 'double') {
      dist = {"1": 50, "2": 36, "3": 30, "4": 24, "5": 20, "6": 16, "7": 12, "8": 8, "9": 4, "10": 2}
      setFormData({...formData, name: 'Double Points', description: '2x standard points', point_distribution: dist, is_multiplier: true, multiplier: 2.0, max_ranks: 10})
    } else if (template === 'top15') {
      dist = {"1": 25, "2": 18, "3": 15, "4": 12, "5": 10, "6": 8, "7": 6, "8": 4, "9": 2, "10": 1, "11": 1, "12": 1, "13": 1, "14": 1, "15": 1}
      setFormData({...formData, name: 'Top 15', description: 'Top 15 players get points', point_distribution: dist, max_ranks: 15})
    } else if (template === 'winner') {
      dist = {"1": 100}
      setFormData({...formData, name: 'Winner Takes All', description: 'Only 1st place gets points', point_distribution: dist, max_ranks: 1})
    }
  }

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>⚙️ Admin Panel</h1>
        <button onClick={() => navigate('/dashboard')} className="back-btn">← Back</button>
      </div>

      <div className="admin-tabs">
        {/* schedule, rankings, profiles tabs hidden - kept for future use */}
        {['fantasy'].map(tab => (
          <button 
            key={tab}
            className={activeTab === tab ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'fantasy' && '🏏 Fantasy'}
          </button>
        ))}
      </div>

      <div className="admin-content">
        {loading && <div className="loading-spinner">Loading...</div>}

        {/* SCHEDULE TAB */}
        {activeTab === 'schedule' && !loading && (
          <div className="section">
            <div className="section-header">
              <h2>IPL Match Schedule</h2>
              <button onClick={() => openModal('addGame')} className="primary-btn">+ Add Game</button>
            </div>
            <div className="games-grid">
              {games.map(game => (
                <div key={game.id} className="modern-card">
                  <div className="card-header">
                    <h3>{game.match_name}</h3>
                    <span className={`status-badge ${game.is_completed ? 'completed' : 'pending'}`}>
                      {game.is_completed ? '✓ Complete' : 'Pending'}
                    </span>
                  </div>
                  <div className="card-body">
                    <p>📅 {new Date(game.match_date).toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: 'numeric'})}</p>
                    {game.match_time && <p>🕐 {game.match_time}</p>}
                    {game.venue && <p>📍 {game.venue}</p>}
                    <p>🏆 {game.scoring_profile_name || 'Default'}</p>
                  </div>
                  <div className="card-actions">
                    <button onClick={(e) => handleDeleteGame(game.id, e)} className="delete-btn-small">Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RANKINGS TAB */}
        {activeTab === 'rankings' && !loading && (
          <div className="section">
            <div className="section-header">
              <h2>Enter Fantasy Points</h2>
            </div>
            <div className="games-grid">
              {games.map(game => (
                <div key={game.id} className="modern-card clickable" onClick={() => loadPointsEntry(game)}>
                  <div className="card-header">
                    <h3>{game.match_name}</h3>
                    <span className={`status-badge ${game.is_completed ? 'completed' : 'pending'}`}>
                      {game.is_completed ? 'Edit' : 'Enter'}
                    </span>
                  </div>
                  <div className="card-body">
                    <p>📅 {new Date(game.match_date).toLocaleDateString('en-IN')}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* FANTASY TAB */}
        {activeTab === 'fantasy' && !loading && (
          <div className="section">

            {/* Series Management */}
            <div className="section-header">
              <h2>Series Management</h2>
            </div>
            <div className="series-mgmt-list">
              {fantasySeries.length === 0 ? (
                <p style={{color:'#555', padding:'12px 0'}}>No series found.</p>
              ) : fantasySeries.map(s => (
                <div key={s.id}>
                  <div className="series-mgmt-row">
                    <div className="series-mgmt-info">
                      <span className="series-mgmt-name">{s.name}</span>
                      <span className="series-mgmt-id" title={String(s.statpal_tournament_id)}>
                        #{s.statpal_tournament_id} ({s.tournament_type})
                      </span>
                      <span className={`series-active-badge ${s.is_active ? 'active' : 'inactive'}`}>
                        {s.is_active ? 'Active' : 'Inactive'}
                      </span>
                      <span className="series-mgmt-count">{s.match_count} matches</span>
                      {s.price_cents > 0
                        ? <span className="series-price-badge">${(s.price_cents / 100).toFixed(2)}</span>
                        : <span className="series-price-badge free">Admin-grant</span>
                      }
                    </div>
                    <div style={{display:'flex', gap:6, flexShrink:0}}>
                      <button
                        className="edit-btn-small"
                        onClick={() => {
                          setSeriesEditModal(s)
                          setSeriesEditPrice(s.price_cents ? (s.price_cents / 100).toFixed(2) : '')
                          setSeriesEditMessage(s.payment_message || '')
                        }}
                      >Edit</button>
                      <button
                        className="edit-btn-small"
                        onClick={async () => {
                          if (seriesAccessPanel === s.id) {
                            setSeriesAccessPanel(null)
                            return
                          }
                          setSeriesAccessPanel(s.id)
                          setSeriesAccessLoading(true)
                          try {
                            const data = await FantasyService.adminGetSeriesAccess(s.id)
                            setSeriesAccessUsers(data.users || [])
                          } catch (err) { alert(err.message) }
                          finally { setSeriesAccessLoading(false) }
                        }}
                      >{seriesAccessPanel === s.id ? 'Hide Access' : 'Access'}</button>
                      <button
                        className="series-toggle-btn"
                        onClick={async () => {
                          try {
                            await FantasyService.adminUpdateSeries(s.id, { is_active: !s.is_active })
                            loadData()
                          } catch (err) { alert(err.message) }
                        }}
                      >
                        {s.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  </div>

                  {/* Access Management Panel */}
                  {seriesAccessPanel === s.id && (
                    <div className="access-panel">
                      <div className="access-panel-header">
                        <span>Users with Access ({seriesAccessUsers.length})</span>
                      </div>
                      {seriesAccessLoading ? (
                        <p style={{color:'#555', fontSize:'0.82rem', padding:'8px 0'}}>Loading...</p>
                      ) : seriesAccessUsers.length === 0 ? (
                        <p style={{color:'#555', fontSize:'0.82rem', padding:'8px 0'}}>No users have access yet.</p>
                      ) : (
                        <table className="access-users-table">
                          <thead>
                            <tr>
                              <th>User</th>
                              <th>Email</th>
                              <th>Type</th>
                              <th>Granted</th>
                              <th></th>
                            </tr>
                          </thead>
                          <tbody>
                            {seriesAccessUsers.map(u => (
                              <tr key={u.user_id}>
                                <td>{u.display_name}</td>
                                <td style={{color:'#888'}}>{u.email}</td>
                                <td>
                                  <span className={`access-type-badge ${u.access_type}`}>
                                    {u.access_type === 'whitelisted' ? '✅ Whitelisted' : '💳 Paid'}
                                  </span>
                                </td>
                                <td style={{color:'#666', fontSize:'0.78rem'}}>
                                  {u.granted_at ? new Date(u.granted_at).toLocaleDateString() : '—'}
                                </td>
                                <td>
                                  <button
                                    className="revoke-btn"
                                    onClick={async () => {
                                      if (!confirm(`Revoke access for ${u.display_name}?`)) return
                                      try {
                                        await FantasyService.adminRevokeAccess(s.id, u.user_id)
                                        setSeriesAccessUsers(prev => prev.filter(x => x.user_id !== u.user_id))
                                      } catch (err) { alert(err.message) }
                                    }}
                                  >Revoke</button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                      <div className="whitelist-add-form">
                        <input
                          className="series-input"
                          placeholder="Email or User ID to whitelist"
                          value={whitelistInput}
                          onChange={e => setWhitelistInput(e.target.value)}
                          onKeyDown={e => e.key === 'Enter' && whitelistInput.trim() && (async () => {
                            try {
                              await FantasyService.adminWhitelistUser(s.id, whitelistInput.trim())
                              setWhitelistInput('')
                              const data = await FantasyService.adminGetSeriesAccess(s.id)
                              setSeriesAccessUsers(data.users || [])
                            } catch (err) { alert(err.message) }
                          })()}
                        />
                        <button
                          className="primary-btn"
                          disabled={!whitelistInput.trim()}
                          onClick={async () => {
                            try {
                              await FantasyService.adminWhitelistUser(s.id, whitelistInput.trim())
                              setWhitelistInput('')
                              const data = await FantasyService.adminGetSeriesAccess(s.id)
                              setSeriesAccessUsers(data.users || [])
                            } catch (err) { alert(err.message) }
                          }}
                        >+ Whitelist</button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="series-add-form">
              <input
                className="series-input"
                placeholder="Series name (e.g. IPL 2027)"
                value={newSeriesName}
                onChange={e => setNewSeriesName(e.target.value)}
              />
              <input
                className="series-input"
                placeholder="StatPal Tournament ID (integer)"
                type="number"
                value={newSeriesTournamentId}
                onChange={e => setNewSeriesTournamentId(e.target.value)}
              />
              <input
                className="series-input"
                placeholder="Tournament type (intl or tour)"
                value={newSeriesTournamentType}
                onChange={e => setNewSeriesTournamentType(e.target.value)}
              />
              <button
                className="primary-btn"
                disabled={!newSeriesName.trim() || !parseInt(newSeriesTournamentId)}
                onClick={async () => {
                  try {
                    await FantasyService.adminCreateSeries({
                      name: newSeriesName.trim(),
                      statpal_tournament_id: parseInt(newSeriesTournamentId, 10),
                      tournament_type: newSeriesTournamentType.trim() || 'intl',
                    })
                    setNewSeriesName('')
                    setNewSeriesTournamentId('')
                    setNewSeriesTournamentType('intl')
                    loadData()
                  } catch (err) { alert(err.message) }
                }}
              >+ Add Series</button>
            </div>
            {/* API Usage */}
            <div className="fa-section-header">
              <h3 className="fa-section-title">API Usage Today</h3>
              <button
                className="fa-action-btn"
                onClick={async () => {
                  try { await FantasyService.adminTriggerSync(); alert('Sync triggered!'); loadData() }
                  catch (err) { alert(err.message) }
                }}
              >🔄 Sync Schedule</button>
            </div>
            <div className="fa-api-card">
              <div className="fa-api-row">
                <span className="fa-api-label">Calls today</span>
                <span className="fa-api-value">{fantasyApiUsage.calls_made || 0} <span className="fa-api-max">/ 2000</span></span>
              </div>
              <div className="fa-api-bar-track">
                <div className="fa-api-bar-fill" style={{width:`${Math.min(100,((fantasyApiUsage.calls_made||0)/2000)*100)}%`}} />
              </div>
              {fantasyApiUsage.last_call_type && (
                <div className="fa-api-last">Last call: {fantasyApiUsage.last_call_type}</div>
              )}
            </div>

            {/* Fantasy Matches */}
            <div className="fa-section-header" style={{marginTop:24}}>
              <h3 className="fa-section-title">Matches ({fantasyMatches.length})</h3>
            </div>
            <div className="fa-matches-grid">
              {fantasyMatches.map(m => (
                <div key={m.id} className="fa-match-card">
                  <div className="fa-match-top">
                    <span className={`fa-status-pill ${m.status}`}>{m.status === 'live' ? '🔴 Live' : m.status === 'completed' ? '✓ Done' : '⏳ Up'}</span>
                    <span className="fa-match-name">{m.match_name}</span>
                  </div>
                  <div className="fa-match-badges">
                    <span className={`fa-badge ${m.squad_fetched ? 'ok' : 'warn'}`}>{m.squad_fetched ? '✓ Squad' : '✗ Squad'}</span>
                  </div>
                  <div className="fa-match-actions">
                    <button className="fa-sm-btn" onClick={async () => { try { await FantasyService.adminTriggerSquad(m.id); alert('Squad triggered!'); loadData() } catch(e){alert(e.message)} }}>Fetch Squad</button>
                    <button className="fa-sm-btn" onClick={async () => { try { await FantasyService.adminTriggerScorecard(m.id); alert('Scorecard triggered!'); loadData() } catch(e){alert(e.message)} }}>Fetch Score</button>
                  </div>
                </div>
              ))}
            </div>

            {/* Fantasy Players */}
            <div className="fa-section-header" style={{marginTop:24}}>
              <h3 className="fa-section-title">Players ({fantasyPlayers.length})</h3>
            </div>
            {fantasyPlayers.length === 0 ? (
              <p className="fa-empty-msg">No players yet — fetch a squad first.</p>
            ) : (
              <div className="fa-players-list">
                {fantasyPlayers.map(p => {
                  const edits = editingPlayer[p.id] || {}
                  const isDirty = Object.keys(edits).length > 0
                  return (
                    <div key={p.id} className={`fa-player-row${isDirty ? ' dirty' : ''}`}>
                      <div className="fa-player-avatar">
                        {(edits.image_url !== undefined ? edits.image_url : p.image_url)
                          ? <img src={edits.image_url !== undefined ? edits.image_url : p.image_url} alt={p.name} className="fa-player-img" onError={e => { e.target.style.display='none' }} />
                          : <div className="fa-player-initials">{p.name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()}</div>
                        }
                      </div>
                      <div className="fa-player-info">
                        <div className="fa-player-name">{p.name}</div>
                        <div className="fa-player-meta">
                          <span className="fa-player-team">{p.team_short}</span>
                          <select
                            className="fa-role-select"
                            value={edits.role !== undefined ? edits.role : p.role}
                            onChange={e => setEditingPlayer({...editingPlayer, [p.id]: {...edits, role: e.target.value}})}
                          >
                            {['WK','BAT','AR','BOWL'].map(r => <option key={r} value={r}>{r}</option>)}
                          </select>
                        </div>
                        <input
                          className="fa-img-input"
                          placeholder="Photo URL"
                          value={edits.image_url !== undefined ? edits.image_url : (p.image_url || '')}
                          onChange={e => setEditingPlayer({...editingPlayer, [p.id]: {...edits, image_url: e.target.value}})}
                        />
                      </div>
                      <div className="fa-player-credits">
                        <input
                          type="number" step="0.5" min="5" max="15"
                          className="fa-credits-input"
                          value={edits.credits !== undefined ? edits.credits : p.credits}
                          onChange={e => setEditingPlayer({...editingPlayer, [p.id]: {...edits, credits: e.target.value}})}
                        />
                        <span className="fa-credits-label">cr</span>
                      </div>
                      {isDirty && (
                        <button
                          className="fa-save-btn"
                          onClick={async () => {
                            try {
                              const payload = {}
                              if (edits.credits !== undefined) payload.credits = parseFloat(edits.credits)
                              if (edits.role !== undefined) payload.role = edits.role
                              if (edits.image_url !== undefined) payload.image_url = edits.image_url
                              await FantasyService.adminUpdatePlayer(p.id, payload)
                              const next = {...editingPlayer}
                              delete next[p.id]
                              setEditingPlayer(next)
                              setFantasyPlayers(prev => prev.map(x => x.id === p.id ? {...x, ...payload} : x))
                            } catch(e) { alert(e.message) }
                          }}
                        >Save</button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* PROFILES TAB */}
        {activeTab === 'profiles' && !loading && (
          <div className="section">
            <div className="section-header">
              <h2>Scoring Profiles</h2>
              <button onClick={() => openModal('addProfile')} className="primary-btn">+ Create Profile</button>
            </div>
            <div className="profiles-grid">
              {profiles.map(profile => (
                <div key={profile.id} className="modern-card">
                  <div className="card-header">
                    <h3>{profile.name} {profile.is_default && '⭐'}</h3>
                  </div>
                  <div className="card-body">
                    <p className="profile-desc">{profile.description}</p>
                    {profile.is_multiplier && (
                      <div className="multiplier-badge">{profile.multiplier}x Multiplier</div>
                    )}
                    <div className="points-preview">
                      {Object.entries(profile.point_distribution).slice(0, 5).map(([rank, pts]) => (
                        <span key={rank} className="point-chip">P{rank}: {pts}</span>
                      ))}
                      {Object.keys(profile.point_distribution).length > 5 && <span className="point-chip">+{Object.keys(profile.point_distribution).length - 5} more</span>}
                    </div>
                  </div>
                  <div className="card-actions">
                    <button onClick={(e) => { e.stopPropagation(); openModal('editProfile', profile); }} className="edit-btn-small">Edit</button>
                    {!profile.is_default && (
                      <button onClick={(e) => handleDeleteProfile(profile.id, e)} className="delete-btn-small">Delete</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* MODAL */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content-large" onClick={(e) => e.stopPropagation()}>
            {modalType === 'addGame' && (
              <form onSubmit={handleGameSubmit} className="modern-form">
                <h2>Add New Game</h2>
                <div className="form-group">
                  <label>Match Name *</label>
                  <input
                    type="text"
                    value={formData.match_name}
                    onChange={(e) => setFormData({...formData, match_name: e.target.value})}
                    placeholder="e.g., MI vs CSK"
                    required
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Date *</label>
                    <input
                      type="date"
                      value={formData.match_date}
                      onChange={(e) => setFormData({...formData, match_date: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Time</label>
                    <input
                      type="time"
                      value={formData.match_time}
                      onChange={(e) => setFormData({...formData, match_time: e.target.value})}
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Venue</label>
                  <input
                    type="text"
                    value={formData.venue}
                    onChange={(e) => setFormData({...formData, venue: e.target.value})}
                    placeholder="e.g., Wankhede Stadium, Mumbai"
                  />
                </div>
                <div className="form-group">
                  <label>Scoring Profile *</label>
                  <select
                    value={formData.scoring_profile_id || ''}
                    onChange={(e) => setFormData({...formData, scoring_profile_id: parseInt(e.target.value)})}
                    required
                  >
                    {profiles.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-actions">
                  <button type="submit" className="primary-btn">Create Game</button>
                  <button type="button" onClick={() => setShowModal(false)} className="cancel-btn">Cancel</button>
                </div>
              </form>
            )}

            {(modalType === 'addProfile' || modalType === 'editProfile') && (
              <form onSubmit={handleProfileSubmit} className="modern-form">
                <h2>{modalType === 'editProfile' ? 'Edit Profile' : 'Create Scoring Profile'}</h2>
                
                <div className="template-shortcuts">
                  <button type="button" onClick={() => applyProfileTemplate('double')} className="template-btn">2x Points</button>
                  <button type="button" onClick={() => applyProfileTemplate('top15')} className="template-btn">Top 15</button>
                  <button type="button" onClick={() => applyProfileTemplate('winner')} className="template-btn">Winner Only</button>
                </div>

                <div className="form-group">
                  <label>Profile Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    rows="2"
                  />
                </div>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.is_multiplier}
                      onChange={(e) => setFormData({...formData, is_multiplier: e.target.checked})}
                    />
                    Use Multiplier Mode
                  </label>
                </div>
                {formData.is_multiplier && (
                  <div className="form-group">
                    <label>Multiplier</label>
                    <input
                      type="number"
                      step="0.1"
                      value={formData.multiplier}
                      onChange={(e) => setFormData({...formData, multiplier: parseFloat(e.target.value)})}
                    />
                  </div>
                )}
                <div className="form-group">
                  <label>Max Ranks to Award Points</label>
                  <input
                    type="number"
                    value={formData.max_ranks}
                    onChange={(e) => setFormData({...formData, max_ranks: parseInt(e.target.value)})}
                  />
                </div>
                <div className="form-actions">
                  <button type="submit" className="primary-btn">{modalType === 'editProfile' ? 'Update' : 'Create'}</button>
                  <button type="button" onClick={() => setShowModal(false)} className="cancel-btn">Cancel</button>
                </div>
              </form>
            )}

            {modalType === 'enterPoints' && (
              <div className="modern-form">
                <h2>Enter Fantasy Points - {selectedItem?.match_name}</h2>
                <p className="help-text">Enter each player's fantasy cricket points. Ranks will be calculated automatically.</p>
                <div className="points-entry-list">
                  {users.map(user => (
                    <div key={user.id} className="points-entry-item">
                      <div className="user-info">
                        <span className="user-name">{user.display_name}</span>
                        <span className="user-email">{user.email}</span>
                      </div>
                      <input
                        type="number"
                        min="0"
                        placeholder="Points"
                        value={fantasyPoints[user.id] || ''}
                        onChange={(e) => setFantasyPoints({...fantasyPoints, [user.id]: e.target.value})}
                        className="points-input"
                      />
                    </div>
                  ))}
                </div>
                <div className="form-actions">
                  <button onClick={handlePointsSubmit} className="primary-btn">Submit Points</button>
                  <button onClick={() => setShowModal(false)} className="cancel-btn">Cancel</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <BottomNav />

      {/* Series Edit Modal */}
      {seriesEditModal && (
        <div className="modal-overlay-admin" onClick={() => setSeriesEditModal(null)}>
          <div className="admin-edit-modal" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3>Edit Series: {seriesEditModal.name}</h3>
              <button className="modal-close-btn" onClick={() => setSeriesEditModal(null)}>✕</button>
            </div>
            <div className="admin-modal-body">
              <label className="admin-form-label">Entry Price (USD)</label>
              <input
                className="admin-form-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="e.g. 5.00 — leave blank for admin-grant only"
                value={seriesEditPrice}
                onChange={e => setSeriesEditPrice(e.target.value)}
              />
              <label className="admin-form-label" style={{marginTop:14}}>Custom Payment Message</label>
              <textarea
                className="admin-form-textarea"
                rows={3}
                placeholder="Shown to users in the payment modal (optional)"
                value={seriesEditMessage}
                onChange={e => setSeriesEditMessage(e.target.value)}
              />
            </div>
            <div className="admin-modal-footer">
              <button className="primary-btn" onClick={async () => {
                try {
                  const priceDollars = seriesEditPrice.trim()
                  const priceCents = priceDollars ? Math.round(parseFloat(priceDollars) * 100) : -1
                  await FantasyService.adminUpdateSeries(seriesEditModal.id, {
                    price_cents: priceCents,
                    payment_message: seriesEditMessage.trim() || '',
                  })
                  setSeriesEditModal(null)
                  loadData()
                } catch (err) { alert(err.message) }
              }}>Save Changes</button>
              <button className="cancel-btn" onClick={() => setSeriesEditModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Admin
