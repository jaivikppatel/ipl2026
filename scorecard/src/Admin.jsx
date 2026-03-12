import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthService from './services/AuthService'
import AdminService from './services/AdminService'
import BottomNav from './BottomNav'
import './Admin.css'

function Admin() {
  const [activeTab, setActiveTab] = useState('schedule')
  const [games, setGames] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [modalType, setModalType] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [formData, setFormData] = useState({})
  const [fantasyPoints, setFantasyPoints] = useState({})
  const [users, setUsers] = useState([])
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
        {['schedule', 'rankings', 'profiles'].map(tab => (
          <button 
            key={tab}
            className={activeTab === tab ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'schedule' && '📅 Schedule'}
            {tab === 'rankings' && '🎯 Enter Points'}
            {tab === 'profiles' && '🏆 Scoring Profiles'}
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
    </div>
  )
}

export default Admin
