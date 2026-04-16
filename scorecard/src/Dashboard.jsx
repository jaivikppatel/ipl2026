import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthService from './services/AuthService'
import Leaderboard from './Leaderboard'
import BottomNav from './BottomNav'
import AajFantasyLogo from './AajFantasyLogo'
import './Dashboard.css'

function Dashboard() {
  const [user, setUser] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    // Check if user is authenticated
    if (!AuthService.isAuthenticated()) {
      navigate('/login')
      return
    }

    // Get user from localStorage and refresh from server
    const loadUser = async () => {
      try {
        const currentUser = await AuthService.getCurrentUser()
        localStorage.setItem('user', JSON.stringify(currentUser.user))
        setUser(currentUser.user)
      } catch (err) {
        // Fallback to localStorage if API fails
        const userData = AuthService.getUser()
        setUser(userData)
      }
    }

    loadUser()
  }, [navigate])

  if (!user) {
    return (
      <div className="dashboard-container">
        <div className="loading">Loading...</div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="header-content">
          <div className="logo-section">
            <AajFantasyLogo size="md" />
          </div>
        </div>
      </div>

      <Leaderboard />
      <BottomNav />
    </div>
  )
}

export default Dashboard
