const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

class AuthService {
  static async signup(displayName, email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ displayName, email, password }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Signup failed');
    }

    // No token stored — user must verify email before logging in
    return data;
  }

  static async verifyEmail(token) {
    const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Verification failed');
    }

    return data;
  }

  static async resendVerification(email) {
    const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Request failed');
    }

    return data;
  }

  static async login(email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Login failed');
    }

    // Store token in localStorage
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    return data;
  }

  static async forgotPassword(email) {
    const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Request failed');
    }
    
    return data;
  }

  static async resetPassword(token, password) {
    const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token, password }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Password reset failed');
    }
    
    return data;
  }

  static async validateResetToken(token) {
    const response = await fetch(`${API_BASE_URL}/auth/validate-reset-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Validation failed');
    }
    
    return data;
  }

  static async getPasswordRequirements() {
    const response = await fetch(`${API_BASE_URL}/auth/password-requirements`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error('Failed to fetch password requirements');
    }
    
    return data;
  }

  static async getCurrentUser() {
    const token = this.getToken();
    
    if (!token) {
      throw new Error('No token found');
    }

    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to get user');
    }
    
    return data;
  }

  static logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  static getToken() {
    return localStorage.getItem('token');
  }

  static getUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  static isAuthenticated() {
    return !!this.getToken();
  }

  static async getLeaderboard() {
    const response = await fetch(`${API_BASE_URL}/leaderboard`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to fetch leaderboard');
    }
    
    return data;
  }

  static async getPlayerGames(userId) {
    const response = await fetch(`${API_BASE_URL}/players/${userId}/games`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to fetch player games');
    }
    
    return data;
  }
}

export default AuthService;
