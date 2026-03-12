const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

class ProfileService {
  static getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }

  // Get current user profile
  static async getProfile() {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this.getAuthHeaders()
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Failed to fetch profile');
    }
    return response.json();
  }

  // Update display name
  static async updateDisplayName(displayName) {
    const response = await fetch(`${API_BASE_URL}/profile/display-name`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ displayName })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Failed to update display name');
    }
    const data = await response.json();
    
    // Update localStorage
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    user.displayName = displayName;
    localStorage.setItem('user', JSON.stringify(user));
    
    return data;
  }

  // Update password
  static async updatePassword(currentPassword, newPassword) {
    const response = await fetch(`${API_BASE_URL}/profile/password`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ currentPassword, newPassword })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Failed to update password');
    }
    return response.json();
  }

  // Upload profile picture (base64)
  static async uploadProfilePicture(base64Image) {
    const response = await fetch(`${API_BASE_URL}/profile/picture`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ profilePicture: base64Image })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Failed to upload profile picture');
    }
    const data = await response.json();
    
    // Update localStorage
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    user.profilePicture = base64Image;
    localStorage.setItem('user', JSON.stringify(user));
    
    return data;
  }

  // Delete profile picture
  static async deleteProfilePicture() {
    const response = await fetch(`${API_BASE_URL}/profile/picture`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Failed to delete profile picture');
    }
    const data = await response.json();
    
    // Update localStorage
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    delete user.profilePicture;
    localStorage.setItem('user', JSON.stringify(user));
    
    return data;
  }

  // Convert file to base64
  static fileToBase64(file) {
    return new Promise((resolve, reject) => {
      if (file.size > 2 * 1024 * 1024) { // 2MB limit
        reject(new Error('File size must be less than 2MB'));
        return;
      }

      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
}

export default ProfileService;
