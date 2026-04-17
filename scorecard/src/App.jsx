import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './Login'
import Signup from './Signup'
import Dashboard from './Dashboard'
import ForgotPassword from './ForgotPassword'
import ResetPassword from './ResetPassword'
import VerifyEmail from './VerifyEmail'
import Admin from './Admin'
import Profile from './Profile'
import Fantasy from './Fantasy'
import FantasyTeamBuilder from './FantasyTeamBuilder'
import FantasyLeaderboard from './FantasyLeaderboard'
import './App.css'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/dashboard" element={<Navigate to="/fantasy" replace />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/fantasy" element={<Fantasy />} />
        <Route path="/fantasy/match/:matchId" element={<FantasyTeamBuilder />} />
        <Route path="/fantasy/match/:matchId/leaderboard" element={<FantasyLeaderboard />} />
      </Routes>
    </Router>
  )
}

export default App
