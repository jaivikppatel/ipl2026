# Cricket Scorecard Application - AI Coding Guide

## Architecture Overview

Full-stack IPL fantasy cricket scoring app with admin features, leaderboard, and game management:
- **Frontend**: `scorecard/` - React 19 + Vite 7 + React Router (HashRouter)
- **Backend**: `server/` - FastAPI + MariaDB with JWT authentication
- **Database**: MariaDB with manual SQL migrations in `server/migrations/`
- **Domain**: IPL fantasy scoring with F1-style points system (configurable via scoring profiles)

## Critical Setup & Workflows

### Running the Application
```bash
# Backend (from root) - Port 5000
cd server
python app.py

# Frontend (from root) - Port 5173
cd scorecard
npm run dev
```

### Database Migrations
- **Manual SQL only** - Located in `server/migrations/`
- Run via: `python server/run_migrations.py`
- No ORM - All queries use direct MySQL connector with parameterized queries
- **Key tables**: `users`, `ipl_game_schedule`, `match_rankings`, `scoring_profiles`

### Environment Configuration
- Backend: `server/.env` (see `server/.env.example`)
- Email verification is **optional** - Set `EMAIL_VERIFICATION_ENABLED=False` for dev
- JWT secrets, database credentials, and SMTP config required for production

## Key Conventions

### Backend (FastAPI)
- **File**: [server/app.py](server/app.py) (~1366 lines, monolithic)
- **API Prefixes**: `/api/auth/`, `/api/admin/`, `/api/leaderboard`, `/api/players/`, `/api/health`
- **Models**: Pydantic models at top of app.py (lines 67-200)
- **Auth Pattern**: JWT tokens in localStorage, verified via `Authorization: Bearer <token>` header
- **Admin Auth**: Uses `verify_admin()` dependency - checks JWT + `is_admin` field in DB
- **Password Rules**: 8+ chars, uppercase, lowercase, digit, special char
- **Database**: Direct `mysql.connector` - no ORM, use `get_db_connection()` helper

**API Endpoints**:
```
# Authentication
POST /api/auth/signup                      - Register user
POST /api/auth/login                       - Login (returns JWT)
GET  /api/auth/me                          - Get current user
POST /api/auth/forgot-password             - Send reset token
POST /api/auth/reset-password              - Reset with token

# Profile Management
PUT  /api/profile/display-name             - Update display name
PUT  /api/profile/password                 - Update password (requires current password)
PUT  /api/profile/picture                  - Upload profile picture (base64, max 2MB)
DELETE /api/profile/picture                - Delete profile picture

# Leaderboard & Player Data
GET  /api/leaderboard                      - Get top 50 players ranked by points
GET  /api/players/{user_id}/games          - Get match history for player

# Admin - Scoring Profiles
GET  /api/admin/scoring-profiles           - List all scoring profiles
POST /api/admin/scoring-profiles           - Create new profile
PUT  /api/admin/scoring-profiles/{id}      - Update profile
DELETE /api/admin/scoring-profiles/{id}    - Delete profile (non-default only)

# Admin - Game Schedule
GET  /api/admin/games                      - List all games
POST /api/admin/games                      - Create game
PUT  /api/admin/games/{id}                 - Update game
DELETE /api/admin/games/{id}               - Delete game

# Admin - Rankings
GET  /api/admin/games/{id}/rankings        - Get rankings for game
POST /api/admin/points                     - Submit fantasy points (auto-calculates ranks)
```

### Frontend (React + Vite)
- **Router**: HashRouter (not BrowserRouter) - URLs use `#/` prefix
- **Services**: 
  - [AuthService.js](scorecard/src/services/AuthService.js) - Auth + leaderboard + player games
  - [AdminService.js](scorecard/src/services/AdminService.js) - Admin operations
  - [ProfileService.js](scorecard/src/services/ProfileService.js) - Profile management & picture upload
- **API Base**: Hardcoded `http://localhost:5000/api` (no proxy configured)
- **Storage**: JWT and user object in `localStorage`
- **Navigation**: [BottomNav.jsx](scorecard/src/BottomNav.jsx) - Shows Admin button if `user.isAdmin`

**Page Components**:
- [Login.jsx](scorecard/src/Login.jsx) - Email/password login
- [Signup.jsx](scorecard/src/Signup.jsx) - Registration with real-time password validation
- [Dashboard.jsx](scorecard/src/Dashboard.jsx) - Shows Leaderboard component
- [Profile.jsx](scorecard/src/Profile.jsx) - User profile management (display name, password, picture)
- [Leaderboard.jsx](scorecard/src/Leaderboard.jsx) - Displays top players, clickable rows
- [PlayerGames.jsx](scorecard/src/PlayerGames.jsx) - Modal showing player's match history
- [Admin.jsx](scorecard/src/Admin.jsx) - Admin panel with tabs (Schedule, Profiles, Rankings)
- [ForgotPassword.jsx](scorecard/src/ForgotPassword.jsx) / [ResetPassword.jsx](scorecard/src/ResetPassword.jsx)

### Data Models & Domain Logic

**Scoring Profiles** (table: `scoring_profiles`):
- Configurable point distributions (e.g., `{"1": 25, "2": 18, "3": 15, ...}`)
- Two modes: Standard (fixed points) or Multiplier (base points × multiplier)
- `max_ranks` determines cutoff (ranks beyond get 0 points)
- Example: Default F1-style profile has 10 ranks

**Game Lifecycle**:
1. Admin creates game in schedule → Sets match name, date, venue, scoring profile
2. Users submit fantasy team points externally (not tracked in app)
3. Admin enters fantasy points via Rankings tab → POST `/api/admin/points`
4. Backend sorts by points, assigns ranks, calculates earned points using profile
5. Inserts into `match_rankings` table with `user_rank`, `fantasy_points`, `points_earned`
6. Marks game as completed (`is_completed = 1`)
7. Leaderboard auto-updates (aggregates `points_earned` from `match_rankings`)

**Database Schema Pattern**:
- `users` - Core auth + `is_admin` flag
- `ipl_game_schedule` - Match metadata + FK to `scoring_profiles`
- `match_rankings` - Links user + game + fantasy_points + calculated rank/points
- `scoring_profiles` - JSON `point_distribution` + multiplier config

### Auth & Authorization

**Standard Auth Check**:
```javascript
// Frontend component
useEffect(() => {
  if (!AuthService.isAuthenticated()) {
    navigate('/login')
  }
}, [])
```

**Admin Auth Check**:
```javascript
// Frontend
const user = AuthService.getUser()
if (!user?.isAdmin) {
  navigate('/dashboard')
}

// Backend (automatic via dependency)
@app.get('/api/admin/games')
async def get_games(admin_id: int = Depends(verify_admin)):
```

## Project-Specific Patterns

### Component Styling
- Each `.jsx` component has a paired `.css` file (e.g., `Admin.jsx` + `Admin.css`)
- Gradients used for branding: `linear-gradient(135deg, #ec008c 0%, #ff6b00 100%)`

### Modal Pattern (See PlayerGames.jsx)
```jsx
<div className="modal-overlay" onClick={onClose}>
  <div className="modal-content" onClick={(e) => e.stopPropagation()}>
    {/* Modal content */}
  </div>
</div>
```

### Error Handling
- Backend: Returns `{"error": "message"}` or `{"detail": "message"}`
- Frontend: `catch (err) { alert(err.message) }` or state-based `setError()`

### Date Formatting
- Backend stores dates as `DATE` or `TIMESTAMP`
- API returns ISO strings: `.isoformat()`
- Frontend displays via `new Date(dateString).toLocaleDateString()`

## Development Gotchas

1. **HashRouter URLs**: Always use `#/` prefix (e.g., `http://localhost:5173/#/admin`)
2. **CORS**: Backend allows `localhost:5173` and `localhost:3000` by default
3. **Database Connection**: No connection pooling - Creates new connection per request
4. **Email in Dev**: Set `EMAIL_VERIFICATION_ENABLED=False` to skip SMTP, reset tokens print to console
5. **No TypeScript**: Pure JavaScript - no type checking
6. **No Tests**: Manual testing workflow only
7. **Admin Flag**: Must manually set `is_admin=1` in database to access admin features
9. **Profile Pictures**: Stored as base64 in MEDIUMTEXT column, 2MB size limit enforced
10. **Mobile UI**: All containers have `max-width: 100vw` and `overflow-x: hidden` to prevent horizontal scroll
11. **Bottom Navigation**: Fixed position with `z-index: 100`, shows profile picture if uploaded
8. **JSON Fields**: `point_distribution` stored as JSON TEXT, requires `json.loads()`/`json.dumps()` in Python

## File Structure Reference
```
scorecard/               # Frontend
├── src/
│   ├── App.jsx          # Router config (HashRouter) - all routes
│   ├── services/
│   │   ├── AuthService.js   # Auth + leaderboard + player games
│   │   └── AdminService.js  # Admin CRUD operations
│   ├── BottomNav.jsx    # Conditional admin nav button
│   ├── Leaderboard.jsx  # Embedded in Dashboard
│   ├── PlayerGames.jsx  # Modal component
│   ├── Admin.jsx        # 3-tab admin panel (~466 lines)
│   └── [Component].jsx + .css pairs
└── package.json         # React 19, Vite 7, react-router-dom 7

server/                  # Backend
├── app.py               # FastAPI app (1366 lines, monolithic)
├── .env.example         # Config template
├── migrations/          # SQL files
│   ├── 001_create_users_table.sql
│   └── 002_create_games_table.sql
├── run_migrations.py    # Migration runner
└── EMAIL_SETUP_GUIDE.md # SMTP setup instructions
```

## When Adding Features

- **New API endpoint**: Add Pydantic models at top of app.py, then `@app.<method>` decorator
- **New frontend page**: Create `Component.jsx` + `Component.css`, add route to `App.jsx`
- **Database changes**: Create new SQL file in `migrations/`, increment number (003_, 004_)
- **Admin features**: Use `Depends(verify_admin)` in backend, check `user.isAdmin` in frontend
- **New scoring rule**: Update `scoring_profiles` schema + admin UI for point_distribution editing
