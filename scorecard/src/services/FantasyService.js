const API_BASE = `${import.meta.env.VITE_API_URL || 'http://localhost:5000/api'}/fantasy`

function getAuthHeader() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse(res) {
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.detail || data.error || 'An error occurred')
  }
  return data
}

const FantasyService = {
  async getMatches() {
    const res = await fetch(`${API_BASE}/matches`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  async getMatchPlayers(matchId) {
    const res = await fetch(`${API_BASE}/matches/${matchId}/players`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  async getMyTeam(matchId) {
    const res = await fetch(`${API_BASE}/matches/${matchId}/my-team`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  async submitTeam(matchId, players) {
    const res = await fetch(`${API_BASE}/matches/${matchId}/team`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ players }),
    })
    return handleResponse(res)
  },

  async getMatchLeaderboard(matchId) {
    const res = await fetch(`${API_BASE}/matches/${matchId}/leaderboard`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  async getPointsBreakdown(matchId) {
    const res = await fetch(`${API_BASE}/matches/${matchId}/points`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  // Admin
  async adminGetPlayers() {
    const res = await fetch(`${API_BASE}/admin/players`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  async adminUpdatePlayer(playerId, update) {
    const res = await fetch(`${API_BASE}/admin/players/${playerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(update),
    })
    return handleResponse(res)
  },

  async adminGetApiUsage() {
    const res = await fetch(`${API_BASE}/admin/api-usage`, { headers: getAuthHeader() })
    return handleResponse(res)
  },

  async adminTriggerSync() {
    const res = await fetch(`${API_BASE}/admin/trigger-sync`, {
      method: 'POST',
      headers: getAuthHeader(),
    })
    return handleResponse(res)
  },

  async adminTriggerSquad(matchId) {
    const res = await fetch(`${API_BASE}/admin/trigger-squad/${matchId}`, {
      method: 'POST',
      headers: getAuthHeader(),
    })
    return handleResponse(res)
  },

  async adminTriggerScorecard(matchId) {
    const res = await fetch(`${API_BASE}/admin/trigger-scorecard/${matchId}`, {
      method: 'POST',
      headers: getAuthHeader(),
    })
    return handleResponse(res)
  },

  async adminGetMatches() {
    const res = await fetch(`${API_BASE}/admin/matches`, { headers: getAuthHeader() })
    return handleResponse(res)
  },
}

export default FantasyService
