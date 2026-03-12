"""
FastAPI Backend for Cricket Scorecard App
Handles authentication, user management, and password reset functionality
"""

import os
import secrets
import bcrypt
import jwt
import mysql.connector
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from dotenv import load_dotenv
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Cricket Scorecard API",
    description="Authentication and user management for Cricket Scorecard App",
    version="1.0.0"
)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': int(os.getenv('DB_PORT', 3306))
}

# Password requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SignupRequest(BaseModel):
    displayName: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

class ValidateTokenRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: int
    displayName: str
    email: str
    isAdmin: Optional[bool] = False
    profilePicture: Optional[str] = None

class UserDetailResponse(UserResponse):
    createdAt: Optional[str] = None
    lastLogin: Optional[str] = None

class AuthResponse(BaseModel):
    message: str
    token: str
    user: UserResponse

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    error: str

class PasswordRequirementsResponse(BaseModel):
    minLength: int
    requireUppercase: bool
    requireLowercase: bool
    requireDigit: bool
    requireSpecial: bool

class HealthResponse(BaseModel):
    status: str
    database: str

class ValidateTokenResponse(BaseModel):
    valid: bool

class MatchResponse(BaseModel):
    id: int
    match_name: str
    match_date: str
    user_rank: int
    points: int
    created_at: str

class LeaderboardEntry(BaseModel):
    user_id: int
    display_name: str
    profilePicture: Optional[str] = None
    total_points: int
    matches_played: int
    average_points: float
    best_rank: Optional[int] = None

class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardEntry]

# Admin Models
class ScoringProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    point_distribution: dict[str, int]
    is_multiplier: Optional[bool] = False
    multiplier: Optional[float] = 1.0
    max_ranks: Optional[int] = 10

class ScoringProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    point_distribution: Optional[dict[str, int]] = None
    is_multiplier: Optional[bool] = None
    multiplier: Optional[float] = None
    max_ranks: Optional[int] = None

class ScoringProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_default: bool
    point_distribution: dict[str, int]
    is_multiplier: bool
    multiplier: float
    max_ranks: int

class GameScheduleCreate(BaseModel):
    match_name: str
    match_date: str
    match_time: Optional[str] = None
    venue: Optional[str] = None
    scoring_profile_id: Optional[int] = None

class GameScheduleResponse(BaseModel):
    id: int
    match_name: str
    match_date: str
    match_time: Optional[str] = None
    venue: Optional[str] = None
    scoring_profile_id: Optional[int] = None
    is_completed: bool

class PointsEntry(BaseModel):
    user_id: int
    fantasy_points: int

class PointsSubmit(BaseModel):
    game_id: int
    points: list[PointsEntry]

class UpdateDisplayNameRequest(BaseModel):
    displayName: str

class UpdatePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str

class UpdateProfilePictureRequest(BaseModel):
    profilePicture: str


def get_db_connection():
    """Create and return a database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def send_email(to_email, subject, html_body, text_body=None):
    """
    Send an email using SMTP configuration from .env
    Returns (success: bool, error_message: str)
    """
    # Check if email is enabled
    if os.getenv('EMAIL_VERIFICATION_ENABLED', 'False') != 'True':
        print(f"Email sending is disabled. Would have sent to: {to_email}")
        return False, "Email sending is disabled"
    
    try:
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL')
        from_name = os.getenv('FROM_NAME', 'Cricket Scorecard')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f'{from_name} <{from_email}>'
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach text and HTML versions
        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(error_msg)
        return False, error_msg

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f'Password must be at least {PASSWORD_MIN_LENGTH} characters long'
    
    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
    
    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
    
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        return False, 'Password must contain at least one number'
    
    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, 'Password must contain at least one special character (!@#$%^&*...)'
    
    return True, None

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=int(os.getenv('BCRYPT_ROUNDS', 12))))

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8') if isinstance(hashed, str) else hashed)

def generate_token(user_id, email, expires_hours=24):
    """Generate a JWT token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=expires_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

async def get_current_user(authorization: Optional[str] = Header(None)):
    """FastAPI dependency to get current user from JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token is missing'
        )
    
    try:
        token = authorization
        if token.startswith('Bearer '):
            token = token[7:]
        
        data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return {
            'user_id': data['user_id'],
            'email': data['email']
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired'
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token'
        )

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post('/api/auth/signup', response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    """Register a new user"""
    try:
        display_name = request.displayName.strip()
        email = request.email.lower()
        password = request.password
        
        # Validate display name
        if len(display_name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Display name must be at least 2 characters'
            )
        
        if len(display_name) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Display name must be less than 100 characters'
            )
        
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Hash password
        password_hash = hash_password(password)
        
        # Insert user into database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO users (display_name, email, password_hash, email_verified) 
                   VALUES (%s, %s, %s, %s)""",
                (display_name, email, password_hash, not bool(os.getenv('EMAIL_VERIFICATION_ENABLED', 'False') == 'True'))
            )
            conn.commit()
            user_id = cursor.lastrowid
            
            # Generate JWT token
            token = generate_token(user_id, email)
            
            return {
                'message': 'User registered successfully',
                'token': token,
                'user': {
                    'id': user_id,
                    'displayName': display_name,
                    'email': email,
                    'isAdmin': False,
                    'profilePicture': None
                }
            }
            
        except mysql.connector.IntegrityError as e:
            if 'idx_email_unique' in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Email already exists. Please login instead'
                )
            raise
        
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred during registration'
        )

@app.post('/api/auth/login', response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user"""
    try:
        email = request.email.lower()
        password = request.password
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get user by email
            cursor.execute(
                """SELECT id, display_name, email, password_hash, is_active, profile_picture 
                   FROM users WHERE email = %s""",
                (email,)
            )
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid email or password'
                )
            
            if not user['is_active']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Account is deactivated'
                )
            
            # Verify password
            if not verify_password(password, user['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid email or password'
                )
            
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE id = %s",
                (datetime.now(timezone.utc), user['id'])
            )
            conn.commit()
            
            # Generate JWT token
            token = generate_token(user['id'], user['email'])
            
            return {
                'message': 'Login successful',
                'token': token,
                'user': {
                    'id': user['id'],
                    'displayName': user['display_name'],
                    'email': user['email'],
                    'isAdmin': bool(user.get('is_admin', 0)),
                    'profilePicture': user.get('profile_picture')
                }
            }
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred during login'
        )

@app.get('/api/auth/me')
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                """SELECT id, display_name, email, is_admin, created_at, last_login, profile_picture 
                   FROM users WHERE id = %s AND is_active = TRUE""",
                (current_user['user_id'],)
            )
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='User not found'
                )
            
            return {
                'user': {
                    'id': user['id'],
                    'displayName': user['display_name'],
                    'email': user['email'],
                    'isAdmin': bool(user.get('is_admin', 0)),
                    'createdAt': user['created_at'].isoformat() if user['created_at'] else None,
                    'lastLogin': user['last_login'].isoformat() if user['last_login'] else None,
                    'profilePicture': user.get('profile_picture')
                }
            }
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred'
        )

# ============================================================================
# PASSWORD RESET ENDPOINTS
# ============================================================================

@app.post('/api/auth/forgot-password', response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """Send password reset email"""
    try:
        email = request.email.lower()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE email = %s AND is_active = TRUE", (email,))
            user = cursor.fetchone()
            
            # Always return success to prevent email enumeration
            if user:
                # Invalidate any existing reset tokens
                cursor.execute(
                    "UPDATE password_reset_tokens SET used = TRUE WHERE user_id = %s AND used = FALSE",
                    (user['id'],)
                )
                
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
                
                # Store reset token
                cursor.execute(
                    """INSERT INTO password_reset_tokens (user_id, token, expires_at) 
                       VALUES (%s, %s, %s)""",
                    (user['id'], reset_token, expires_at)
                )
                conn.commit()
                
                # Generate reset link
                reset_link = f"http://localhost:5173/#/reset-password?token={reset_token}"
                
                # Prepare email content
                subject = "Password Reset Request - Cricket Scorecard"
                
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #ec008c 0%, #ff6b00 100%);
                            color: white;
                            padding: 30px;
                            border-radius: 10px;
                            text-align: center;
                        }}
                        .content {{
                            background: #f9f9f9;
                            padding: 30px;
                            border-radius: 10px;
                            margin-top: 20px;
                        }}
                        .button {{
                            display: inline-block;
                            padding: 15px 30px;
                            background: linear-gradient(135deg, #ec008c 0%, #ff6b00 100%);
                            color: white;
                            text-decoration: none;
                            border-radius: 10px;
                            font-weight: bold;
                            margin: 20px 0;
                        }}
                        .footer {{
                            text-align: center;
                            margin-top: 20px;
                            color: #666;
                            font-size: 12px;
                        }}
                        .warning {{
                            background: #fff3cd;
                            border-left: 4px solid #ffc107;
                            padding: 15px;
                            margin: 20px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🏏 Cricket Scorecard</h1>
                        <p>Password Reset Request</p>
                    </div>
                    <div class="content">
                        <p>Hi {user['display_name']},</p>
                        <p>We received a request to reset your password for your Cricket Scorecard account.</p>
                        <p>Click the button below to reset your password:</p>
                        <div style="text-align: center;">
                            <a href="{reset_link}" class="button">Reset Password</a>
                        </div>
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background: #fff; padding: 10px; border-radius: 5px;">
                            {reset_link}
                        </p>
                        <div class="warning">
                            <strong>⚠️ Important:</strong>
                            <ul>
                                <li>This link will expire in 1 hour</li>
                                <li>If you didn't request this, please ignore this email</li>
                                <li>Never share this link with anyone</li>
                            </ul>
                        </div>
                    </div>
                    <div class="footer">
                        <p>This is an automated email from Cricket Scorecard.</p>
                        <p>If you didn't request a password reset, you can safely ignore this email.</p>
                    </div>
                </body>
                </html>
                """
                
                text_body = f"""
                Cricket Scorecard - Password Reset Request
                
                Hi {user['display_name']},
                
                We received a request to reset your password for your Cricket Scorecard account.
                
                Click the link below to reset your password:
                {reset_link}
                
                IMPORTANT:
                - This link will expire in 1 hour
                - If you didn't request this, please ignore this email
                - Never share this link with anyone
                
                If the link doesn't work, copy and paste it into your browser.
                
                ---
                This is an automated email from Cricket Scorecard.
                If you didn't request a password reset, you can safely ignore this email.
                """
                
                # Send email
                email_sent, email_error = send_email(email, subject, html_body, text_body)
                
                if not email_sent:
                    # Email failed, but still log it and show the link in console for development
                    print(f"Password reset link for {email}: {reset_link}")
                    print(f"Email error: {email_error}")
                else:
                    print(f"Password reset email sent successfully to {email}")
            
            return {'message': 'If the email exists, a password reset link has been sent'}
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred'
        )

@app.post('/api/auth/reset-password', response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """Reset password using token"""
    try:
        token = request.token.strip()
        new_password = request.password
        
        # Validate new password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get reset token
            cursor.execute(
                """SELECT id, user_id, expires_at, used 
                   FROM password_reset_tokens 
                   WHERE token = %s""",
                (token,)
            )
            reset_token = cursor.fetchone()
            
            if not reset_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Invalid or expired reset token'
                )
            
            if reset_token['used']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Reset token has already been used'
                )
            
            # Make expires_at timezone-aware for comparison
            expires_at_utc = reset_token['expires_at'].replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at_utc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Reset token has expired'
                )
            
            # Hash new password
            password_hash = hash_password(new_password)
            
            # Update password
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (password_hash, reset_token['user_id'])
            )
            
            # Mark token as used
            cursor.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE id = %s",
                (reset_token['id'],)
            )
            
            conn.commit()
            
            return {'message': 'Password reset successfully'}
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred'
        )

@app.post('/api/auth/validate-reset-token', response_model=ValidateTokenResponse)
async def validate_reset_token(request: ValidateTokenRequest):
    """Validate if a reset token is still valid"""
    try:
        token = request.token.strip()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                """SELECT expires_at, used FROM password_reset_tokens WHERE token = %s""",
                (token,)
            )
            reset_token = cursor.fetchone()
            
            # Make expires_at timezone-aware for comparison
            if not reset_token or reset_token['used']:
                return {'valid': False}
            
            expires_at_utc = reset_token['expires_at'].replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at_utc:
                return {'valid': False}
            
            return {'valid': True}
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Validate token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred'
        )

# ============================================================================
# PASSWORD REQUIREMENTS ENDPOINT
# ============================================================================

@app.get('/api/auth/password-requirements', response_model=PasswordRequirementsResponse)
async def get_password_requirements():
    """Get password requirements for client-side validation"""
    return {
        'minLength': PASSWORD_MIN_LENGTH,
        'requireUppercase': PASSWORD_REQUIRE_UPPERCASE,
        'requireLowercase': PASSWORD_REQUIRE_LOWERCASE,
        'requireDigit': PASSWORD_REQUIRE_DIGIT,
        'requireSpecial': PASSWORD_REQUIRE_SPECIAL
    }

# ============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# ============================================================================

@app.put('/api/profile/display-name', response_model=MessageResponse)
async def update_display_name(
    request: UpdateDisplayNameRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user's display name"""
    try:
        display_name = request.displayName.strip()
        
        # Validate display name
        if len(display_name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Display name must be at least 2 characters'
            )
        
        if len(display_name) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Display name must be less than 100 characters'
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET display_name = %s WHERE id = %s",
                (display_name, current_user['user_id'])
            )
            conn.commit()
            
            return {'message': 'Display name updated successfully'}
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update display name error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while updating display name'
        )

@app.put('/api/profile/password', response_model=MessageResponse)
async def update_password(
    request: UpdatePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user's password"""
    try:
        current_password = request.currentPassword
        new_password = request.newPassword
        
        # Validate new password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get current password hash
            cursor.execute(
                "SELECT password_hash FROM users WHERE id = %s",
                (current_user['user_id'],)
            )
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='User not found'
                )
            
            # Verify current password
            if not verify_password(current_password, user['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Current password is incorrect'
                )
            
            # Hash new password
            password_hash = hash_password(new_password)
            
            # Update password
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (password_hash, current_user['user_id'])
            )
            conn.commit()
            
            return {'message': 'Password updated successfully'}
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while updating password'
        )

@app.put('/api/profile/picture', response_model=MessageResponse)
async def update_profile_picture(
    request: UpdateProfilePictureRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user's profile picture"""
    try:
        profile_picture = request.profilePicture
        
        # Validate base64 image (basic check)
        if not profile_picture.startswith('data:image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid image format'
            )
        
        # Check size (roughly 2MB limit for base64)
        if len(profile_picture) > 2.7 * 1024 * 1024:  # base64 is ~33% larger
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Image size too large (max 2MB)'
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET profile_picture = %s WHERE id = %s",
                (profile_picture, current_user['user_id'])
            )
            conn.commit()
            
            return {'message': 'Profile picture updated successfully'}
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update profile picture error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while updating profile picture'
        )

@app.delete('/api/profile/picture', response_model=MessageResponse)
async def delete_profile_picture(current_user: dict = Depends(get_current_user)):
    """Delete user's profile picture"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET profile_picture = NULL WHERE id = %s",
                (current_user['user_id'],)
            )
            conn.commit()
            
            return {'message': 'Profile picture deleted successfully'}
            
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        print(f"Delete profile picture error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while deleting profile picture'
        )

# ============================================================================
# LEADERBOARD ENDPOINTS
# ============================================================================

@app.get('/api/leaderboard', response_model=LeaderboardResponse)
async def get_leaderboard():
    """Get leaderboard with player rankings based on total scores"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get aggregated stats for all players from match_rankings
            cursor.execute("""
                SELECT 
                    u.id as user_id,
                    u.display_name,
                    u.profile_picture,
                    COALESCE(SUM(r.points_earned), 0) as total_points,
                    COUNT(r.id) as matches_played,
                    COALESCE(AVG(r.points_earned), 0) as average_points,
                    COALESCE(MIN(r.user_rank), 999) as best_rank
                FROM users u
                LEFT JOIN match_rankings r ON u.id = r.user_id
                GROUP BY u.id, u.display_name, u.profile_picture
                HAVING total_points > 0 OR matches_played > 0
                ORDER BY total_points DESC, best_rank ASC
                LIMIT 50
            """)
            
            results = cursor.fetchall()
            
            def get_profile_picture(row):
                pp = row.get('profile_picture')
                if pp is None:
                    return None
                if isinstance(pp, bytes):
                    return pp.decode('utf-8')
                return pp
            
            leaderboard = [
                {
                    'user_id': row['user_id'],
                    'display_name': row['display_name'],
                    'profilePicture': get_profile_picture(row),
                    'total_points': int(row['total_points']),
                    'matches_played': int(row['matches_played']),
                    'average_points': round(float(row['average_points']), 1),
                    'best_rank': int(row['best_rank']) if row['best_rank'] != 999 else None
                }
                for row in results
            ]
            
            return {'leaderboard': leaderboard}
            
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        print(f"Leaderboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while fetching leaderboard'
        )

@app.get('/api/players/{user_id}/games')
async def get_player_games(user_id: int):
    """Get all games for a specific player"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # First verify the user exists
            cursor.execute("SELECT id as user_id, display_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Player not found'
                )
            
            # Get all matches for this player from match_rankings
            cursor.execute("""
                SELECT 
                    r.id,
                    g.match_name,
                    g.match_date,
                    r.user_rank,
                    r.points_earned as points,
                    r.created_at
                FROM match_rankings r
                JOIN ipl_game_schedule g ON r.game_id = g.id
                WHERE r.user_id = %s
                ORDER BY g.match_date DESC, r.created_at DESC
            """, (user_id,))
            
            games = cursor.fetchall()
            
            # Convert dates to strings
            matches_list = []
            for match in games:
                matches_list.append({
                    'id': match['id'],
                    'match_name': match['match_name'],
                    'match_date': match['match_date'].isoformat() if match['match_date'] else None,
                    'user_rank': match['user_rank'],
                    'points': match['points'],
                    'created_at': match['created_at'].isoformat() if match['created_at'] else None
                })
            
            return {
                'user': {
                    'user_id': user['user_id'],
                    'display_name': user['display_name']
                },
                'matches': matches_list
            }
            
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get player games error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while fetching player games'
        )

# ============================================================================
# ADMIN HELPER FUNCTIONS
# ============================================================================

async def verify_admin(authorization: str = Header(None)):
    """Verify user is an admin"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authorized'
        )
    
    token = authorization.replace('Bearer ', '')
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user or not user.get('is_admin'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Admin access required'
            )
        
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token'
        )

# ============================================================================
# ADMIN ENDPOINTS - SCORING PROFILES
# ============================================================================

@app.get('/api/admin/scoring-profiles')
async def get_scoring_profiles(admin_id: int = Depends(verify_admin)):
    """Get all scoring profiles"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT id, name, description, is_default, point_distribution,
                   is_multiplier, multiplier, max_ranks
            FROM scoring_profiles
            ORDER BY is_default DESC, name ASC
        """)
        
        profiles = []
        for row in cursor.fetchall():
            import json
            profiles.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'is_default': bool(row['is_default']),
                'point_distribution': json.loads(row['point_distribution']),
                'is_multiplier': bool(row.get('is_multiplier', 0)),
                'multiplier': float(row.get('multiplier', 1.0)),
                'max_ranks': int(row.get('max_ranks', 10))
            })
        
        return {'profiles': profiles}
    finally:
        cursor.close()
        conn.close()

@app.post('/api/admin/scoring-profiles')
async def create_scoring_profile(
    profile: ScoringProfileCreate,
    admin_id: int = Depends(verify_admin)
):
    """Create a new scoring profile"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        import json
        cursor.execute("""
            INSERT INTO scoring_profiles 
            (name, description, point_distribution, is_multiplier, multiplier, max_ranks)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (profile.name, profile.description, json.dumps(profile.point_distribution),
              profile.is_multiplier, profile.multiplier, profile.max_ranks))
        
        conn.commit()
        profile_id = cursor.lastrowid
        
        return {'message': 'Scoring profile created', 'id': profile_id}
    finally:
        cursor.close()
        conn.close()

@app.put('/api/admin/scoring-profiles/{profile_id}')
async def update_scoring_profile(
    profile_id: int,
    profile: ScoringProfileUpdate,
    admin_id: int = Depends(verify_admin)
):
    """Update a scoring profile"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        import json
        updates = []
        params = []
        
        if profile.name is not None:
            updates.append("name = %s")
            params.append(profile.name)
        if profile.description is not None:
            updates.append("description = %s")
            params.append(profile.description)
        if profile.point_distribution is not None:
            updates.append("point_distribution = %s")
            params.append(json.dumps(profile.point_distribution))
        if profile.is_multiplier is not None:
            updates.append("is_multiplier = %s")
            params.append(profile.is_multiplier)
        if profile.multiplier is not None:
            updates.append("multiplier = %s")
            params.append(profile.multiplier)
        if profile.max_ranks is not None:
            updates.append("max_ranks = %s")
            params.append(profile.max_ranks)
        
        if updates:
            params.append(profile_id)
            cursor.execute(f"""
                UPDATE scoring_profiles 
                SET {', '.join(updates)}
                WHERE id = %s
            """, params)
            conn.commit()
        
        return {'message': 'Profile updated'}
    finally:
        cursor.close()
        conn.close()

@app.delete('/api/admin/scoring-profiles/{profile_id}')
async def delete_scoring_profile(profile_id: int, admin_id: int = Depends(verify_admin)):
    """Delete a scoring profile"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM scoring_profiles WHERE id = %s AND is_default = 0", (profile_id,))
        conn.commit()
        return {'message': 'Profile deleted'}
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# ADMIN ENDPOINTS - GAME SCHEDULE
# ============================================================================

@app.get('/api/admin/games')
async def get_game_schedule(admin_id: int = Depends(verify_admin)):
    """Get all scheduled games"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                g.id, g.match_name, g.match_date, g.match_time, g.venue,
                g.scoring_profile_id, g.is_completed,
                s.name as scoring_profile_name
            FROM ipl_game_schedule g
            LEFT JOIN scoring_profiles s ON g.scoring_profile_id = s.id
            ORDER BY g.match_date DESC, g.match_time DESC
        """)
        
        games = []
        for row in cursor.fetchall():
            games.append({
                'id': row['id'],
                'match_name': row['match_name'],
                'match_date': row['match_date'].isoformat() if row['match_date'] else None,
                'match_time': str(row['match_time']) if row['match_time'] else None,
                'venue': row['venue'],
                'scoring_profile_id': row['scoring_profile_id'],
                'scoring_profile_name': row['scoring_profile_name'],
                'is_completed': bool(row['is_completed'])
            })
        
        return {'games': games}
    finally:
        cursor.close()
        conn.close()

@app.post('/api/admin/games')
async def create_game(
    game: GameScheduleCreate,
    admin_id: int = Depends(verify_admin)
):
    """Create a new game in the schedule"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get default profile if none specified
        scoring_profile_id = game.scoring_profile_id
        if not scoring_profile_id:
            cursor.execute("SELECT id FROM scoring_profiles WHERE is_default = 1 LIMIT 1")
            default = cursor.fetchone()
            scoring_profile_id = default[0] if default else None
        
        cursor.execute("""
            INSERT INTO ipl_game_schedule 
            (match_name, match_date, match_time, venue, scoring_profile_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (game.match_name, game.match_date, game.match_time, game.venue, scoring_profile_id))
        
        conn.commit()
        game_id = cursor.lastrowid
        
        return {'message': 'Game created', 'id': game_id}
    finally:
        cursor.close()
        conn.close()

@app.put('/api/admin/games/{game_id}')
async def update_game(
    game_id: int,
    game: GameScheduleCreate,
    admin_id: int = Depends(verify_admin)
):
    """Update a game"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE ipl_game_schedule
            SET match_name = %s, match_date = %s, match_time = %s, 
                venue = %s, scoring_profile_id = %s
            WHERE id = %s
        """, (game.match_name, game.match_date, game.match_time, 
              game.venue, game.scoring_profile_id, game_id))
        
        conn.commit()
        return {'message': 'Game updated'}
    finally:
        cursor.close()
        conn.close()

@app.delete('/api/admin/games/{game_id}')
async def delete_game(game_id: int, admin_id: int = Depends(verify_admin)):
    """Delete a game"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM ipl_game_schedule WHERE id = %s", (game_id,))
        conn.commit()
        return {'message': 'Game deleted'}
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# ADMIN ENDPOINTS - RANKINGS
# ============================================================================

@app.get('/api/admin/games/{game_id}/rankings')
async def get_game_rankings(game_id: int, admin_id: int = Depends(verify_admin)):
    """Get rankings for a specific game"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get game info
        cursor.execute("""
            SELECT g.id, g.match_name, g.scoring_profile_id, 
                   s.point_distribution, s.is_multiplier, s.multiplier, s.max_ranks
            FROM ipl_game_schedule g
            LEFT JOIN scoring_profiles s ON g.scoring_profile_id = s.id
            WHERE g.id = %s
        """, (game_id,))
        
        game = cursor.fetchone()
        if not game:
            raise HTTPException(status_code=404, detail='Game not found')
        
        # Get existing points
        cursor.execute("""
            SELECT r.id, r.user_id, u.display_name, u.email,
                   r.fantasy_points, r.user_rank, r.points_earned
            FROM match_rankings r
            JOIN users u ON r.user_id = u.id
            WHERE r.game_id = %s
            ORDER BY r.fantasy_points DESC, u.display_name ASC
        """, (game_id,))
        
        rankings = cursor.fetchall()
        
        # Get all users for selection
        cursor.execute("SELECT id, display_name, email FROM users ORDER BY display_name")
        users = cursor.fetchall()
        
        import json
        return {
            'game': {
                'id': game['id'],
                'match_name': game['match_name'],
                'point_distribution': json.loads(game['point_distribution']) if game['point_distribution'] else{},
                'is_multiplier': bool(game.get('is_multiplier', 0)),
                'multiplier': float(game.get('multiplier', 1.0)),
                'max_ranks': int(game.get('max_ranks', 10))
            },
            'rankings': rankings,
            'users': users
        }
    finally:
        cursor.close()
        conn.close()

@app.post('/api/admin/points')
async def submit_points(
    data: PointsSubmit,
    admin_id: int = Depends(verify_admin)
):
    """Submit or update fantasy points for a game"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get scoring profile
        cursor.execute("""
            SELECT s.point_distribution, s.is_multiplier, s.multiplier, s.max_ranks
            FROM ipl_game_schedule g
            JOIN scoring_profiles s ON g.scoring_profile_id = s.id
            WHERE g.id = %s
        """, (data.game_id,))
        
        game = cursor.fetchone()
        if not game:
            raise HTTPException(status_code=404, detail='Game not found')
        
        import json
        point_dist = json.loads(game['point_distribution'])
        is_multiplier = bool(game.get('is_multiplier', 0))
        multiplier = float(game.get('multiplier', 1.0))
        max_ranks = int(game.get('max_ranks', 10))
        
        # Sort by fantasy points descending to calculate ranks
        sorted_points = sorted(data.points, key=lambda x: x.fantasy_points, reverse=True)
        
        # Delete existing rankings
        cursor.execute("DELETE FROM match_rankings WHERE game_id = %s", (data.game_id,))
        
        # Insert new rankings with calculated ranks and points
        for idx, entry in enumerate(sorted_points):
            rank = idx + 1
            
            # Calculate points earned based on rank
            if is_multiplier:
                # Multiplier profile - apply multiplier to base points
                base_points = point_dist.get(str(rank), 0) if rank <= max_ranks else 0
                points_earned = int(base_points * multiplier)
            else:
                # Standard profile
                points_earned = point_dist.get(str(rank), 0) if rank <= max_ranks else 0
            
            cursor.execute("""
                INSERT INTO match_rankings 
                (game_id, user_id, fantasy_points, user_rank, points_earned)
                VALUES (%s, %s, %s, %s, %s)
            """, (data.game_id, entry.user_id, entry.fantasy_points, rank, points_earned))
        
        # Mark game as completed
        cursor.execute("""
            UPDATE ipl_game_schedule SET is_completed = 1 WHERE id = %s
        """, (data.game_id,))
        
        conn.commit()
        return {'message': 'Points submitted successfully'}
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get('/api/health', response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        return {'status': 'healthy', 'database': 'connected'}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={'status': 'unhealthy', 'error': str(e)}
        )

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 5000))
    uvicorn.run(
        "app:app",
        host='0.0.0.0',
        port=port,
        reload=os.getenv('FLASK_DEBUG', 'True') == 'True'
    )

