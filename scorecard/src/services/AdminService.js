const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

class AdminService {
  static getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }

  // Scoring Profiles
  static async getScoringProfiles() {
    const response = await fetch(`${API_BASE_URL}/admin/scoring-profiles`, {
      headers: this.getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to fetch scoring profiles');
    return response.json();
  }

  static async createScoringProfile(profileData) {
    const response = await fetch(`${API_BASE_URL}/admin/scoring-profiles`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(profileData)
    });
    if (!response.ok) throw new Error('Failed to create scoring profile');
    return response.json();
  }

  static async updateScoringProfile(profileId, profileData) {
    const response = await fetch(`${API_BASE_URL}/admin/scoring-profiles/${profileId}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(profileData)
    });
    if (!response.ok) throw new Error('Failed to update scoring profile');
    return response.json();
  }

  static async deleteScoringProfile(profileId) {
    const response = await fetch(`${API_BASE_URL}/admin/scoring-profiles/${profileId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete scoring profile');
    return response.json();
  }

  // Game Schedule
  static async getGames() {
    const response = await fetch(`${API_BASE_URL}/admin/games`, {
      headers: this.getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to fetch games');
    return response.json();
  }

  static async createGame(gameData) {
    const response = await fetch(`${API_BASE_URL}/admin/games`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(gameData)
    });
    if (!response.ok) throw new Error('Failed to create game');
    return response.json();
  }

  static async updateGame(gameId, gameData) {
    const response = await fetch(`${API_BASE_URL}/admin/games/${gameId}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(gameData)
    });
    if (!response.ok) throw new Error('Failed to update game');
    return response.json();
  }

  static async deleteGame(gameId) {
    const response = await fetch(`${API_BASE_URL}/admin/games/${gameId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete game');
    return response.json();
  }

  // Rankings
  static async getGameRankings(gameId) {
    const response = await fetch(`${API_BASE_URL}/admin/games/${gameId}/rankings`, {
      headers: this.getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to fetch rankings');
    return response.json();
  }

  static async submitRankings(data) {
    const response = await fetch(`${API_BASE_URL}/admin/points`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to submit points');
    return response.json();
  }
}

export default AdminService;
