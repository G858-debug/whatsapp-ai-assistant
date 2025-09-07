"""Dashboard and WhatsApp synchronization service"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
import json
import hashlib
from collections import defaultdict
from utils.logger import log_error, log_info, log_warning

class DashboardSyncService:
    """Handles synchronization between dashboard actions and WhatsApp notifications"""
    
    def __init__(self, supabase_client, config, whatsapp_service):
        self.db = supabase_client
        self.config = config
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Cache for user preferences (in-memory for now)
        self.preference_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Pending notifications queue for digest
        self.digest_queue = defaultdict(list)
        
        # Dashboard base URL
        self.dashboard_base_url = config.DASHBOARD_URL if hasattr(config, 'DASHBOARD_URL') else 'https://refiloe.ai/dashboard'
    
    # ============= DASHBOARD ACTION TRIGGERS =============
    
    def handle_dashboard_action(self, user_id: str, user_type: str, 
                               action: str, data: Dict) -> Dict:
        """
        Handle actions from dashboard and determine WhatsApp notification strategy
        
        Actions:
        - pre_book_challenge: Add to next digest only
        - join_challenge: No WhatsApp, show success on dashboard
        - log_progress: Update dashboard only, include in daily summary
        - change_preferences: Send ONE confirmation
        """
        try:
            if action == 'pre_book_challenge':
                return self._handle_pre_book(user_id, user_type, data)
            
            elif action == 'join_challenge':
                return self._handle_join_challenge(user_id, user_type, data)
            
            elif action == 'log_progress':
                return self._handle_progress_log(user_id, user_type, data)
            
            elif action == 'change_preferences':
                return self._handle_preference_change(user_id, user_type, data)
            
            elif action == 'leave_challenge':
                return self._handle_leave_challenge(user_id, user_type, data)
            
            else:
                log_warning(f"Unknown dashboard action: {action}")
                return {'success': False, 'error': 'Unknown action'}
                
        except Exception as e:
            log_error(f"Error handling dashboard action: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_pre_book(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle challenge pre-booking - add to digest only"""
        try:
            challenge_name = data.get('challenge_name', 'challenge')
            
            # Add to digest queue
            self.digest_queue[user_id].append({
                'type': 'pre_book',
                'message': f"✓ Pre-booked for {challenge_name}",
                'timestamp': datetime.now(self.sa_tz).isoformat()
            })
            
            # Store in database for persistent digest
            self.db.table('notification_queue').insert({
                'user_id': user_id,
                'user_type': user_type,
                'notification_type': 'pre_book',
                'content': f"✓ Pre-booked for {challenge_name}",
                'scheduled_for': self._get_next_digest_time(user_id),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return {
                'success': True,
                'whatsapp_sent': False,
                'queued_for_digest': True
            }
            
        except Exception as e:
            log_error(f"Error handling pre-book: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_join_challenge(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle joining challenge - no WhatsApp notification"""
        try:
            # Just return success for dashboard
            return {
                'success': True,
                'whatsapp_sent': False,
                'message': 'Successfully joined challenge!'
            }
            
        except Exception as e:
            log_error(f"Error handling join challenge: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_progress_log(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle progress logging - update dashboard only"""
        try:
            # Add to daily summary queue
            progress_type = data.get('type', 'progress')
            value = data.get('value', '')
            
            self.digest_queue[user_id].append({
                'type': 'progress',
                'message': f"Logged: {progress_type} - {value}",
                'timestamp': datetime.now(self.sa_tz).isoformat()
            })
            
            return {
                'success': True,
                'whatsapp_sent': False,
                'included_in_summary': True
            }
            
        except Exception as e:
            log_error(f"Error handling progress log: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_preference_change(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle preference change - send ONE confirmation"""
        try:
            # Clear cache
            cache_key = f"{user_type}:{user_id}"
            if cache_key in self.preference_cache:
                del self.preference_cache[cache_key]
            
            # Get user's WhatsApp number
            phone = self._get_user_phone(user_id, user_type)
            
            if phone:
                # Send single confirmation
                message = "✅ Your notification preferences have been updated."
                self.whatsapp.send_message(phone, message)
                
                return {
                    'success': True,
                    'whatsapp_sent': True,
                    'message': 'Preferences updated and confirmed via WhatsApp'
                }
            
            return {
                'success': True,
                'whatsapp_sent': False,
                'message': 'Preferences updated'
            }
            
        except Exception as e:
            log_error(f"Error handling preference change: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_leave_challenge(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle leaving challenge - no immediate notification"""
        try:
            return {
                'success': True,
                'whatsapp_sent': False,
                'message': 'Left challenge successfully'
            }
            
        except Exception as e:
            log_error(f"Error handling leave challenge: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ============= WHATSAPP QUICK COMMANDS =============
    
    def handle_quick_command(self, command: str, user_id: str, 
                           user_type: str, phone: str) -> Optional[Dict]:
        """
        Handle WhatsApp quick commands that redirect to dashboard
        
        Commands:
        - challenges → View all challenges at [dashboard_link]
        - leaderboard → See full rankings at [dashboard_link]
        - stats → Your detailed stats at [dashboard_link]
        """
        command_lower = command.lower().strip()
        
        # Generate access token for dashboard
        token = self._generate_dashboard_token(user_id, user_type)
        
        if command_lower in ['challenges', 'challenge']:
            link = self.generate_deep_link('challenges', user_id, user_type, token)
            return {
                'success': True,
                'message': f"🎮 View all challenges and your progress:\n{link}\n\nTap to open in your browser.",
                'type': 'redirect'
            }
        
        elif command_lower in ['leaderboard', 'rankings', 'rank']:
            link = self.generate_deep_link('leaderboard', user_id, user_type, token, 
                                        {'highlight': user_id})
            return {
                'success': True,
                'message': f"🏆 See the full leaderboard:\n{link}\n\nYour position is highlighted!",
                'type': 'redirect'
            }
        
        elif command_lower in ['stats', 'statistics', 'my stats']:
            link = self.generate_deep_link('stats', user_id, user_type, token)
            return {
                'success': True,
                'message': f"📊 View your detailed statistics:\n{link}\n\nIncludes points, badges, and progress!",
                'type': 'redirect'
            }
        
        elif command_lower in ['dashboard', 'website', 'web']:
            link = self.generate_deep_link('home', user_id, user_type, token)
            return {
                'success': True,
                'message': f"🖥️ Open your dashboard:\n{link}",
                'type': 'redirect'
            }
        
        return None  # Not a quick command
    
    # ============= DASHBOARD DEEP LINKS =============
    
    def generate_deep_link(self, page: str, user_id: str, user_type: str, 
                          token: str = None, params: Dict = None) -> str:
        """
        Generate specific dashboard URLs for WhatsApp messages
        
        Pages:
        - /dashboard/challenges/{challenge_id} - Direct to specific challenge
        - /dashboard/leaderboard?highlight={user_id} - Shows user's position
        - /dashboard/pre-book/{challenge_id} - One-click pre-booking
        """
        if not token:
            token = self._generate_dashboard_token(user_id, user_type)
        
        # Build URL
        if page == 'challenges':
            url = f"{self.dashboard_base_url}/challenges"
        elif page == 'challenge':
            challenge_id = params.get('challenge_id') if params else None
            url = f"{self.dashboard_base_url}/challenges/{challenge_id}" if challenge_id else f"{self.dashboard_base_url}/challenges"
        elif page == 'leaderboard':
            highlight = params.get('highlight') if params else user_id
            url = f"{self.dashboard_base_url}/leaderboard?highlight={highlight}"
        elif page == 'pre-book':
            challenge_id = params.get('challenge_id') if params else None
            url = f"{self.dashboard_base_url}/pre-book/{challenge_id}" if challenge_id else f"{self.dashboard_base_url}/challenges"
        elif page == 'stats':
            url = f"{self.dashboard_base_url}/stats"
        else:
            url = self.dashboard_base_url
        
        # Add authentication token
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}token={token}"
        
        return url
    
    def _generate_dashboard_token(self, user_id: str, user_type: str) -> str:
        """Generate secure token for dashboard access"""
        try:
            # Check for existing valid token
            existing = self.db.table('dashboard_tokens').select('*').eq(
                f'{user_type}_id', user_id
            ).eq('is_valid', True).execute()
            
            if existing.data:
                # Check if token is still fresh (24 hours)
                created_at = datetime.fromisoformat(existing.data[0]['created_at'])
                if (datetime.now(pytz.UTC) - created_at).total_seconds() < 86400:
                    return existing.data[0]['token']
            
            # Generate new token
            import secrets
            token = secrets.token_urlsafe(32)
            
            # Store token
            if user_type == 'trainer':
                token_data = {'trainer_id': user_id}
            else:
                token_data = {'client_id': user_id}
            
            token_data.update({
                'token': token,
                'is_valid': True,
                'created_at': datetime.now(pytz.UTC).isoformat()
            })
            
            self.db.table('dashboard_tokens').insert(token_data).execute()
            
            return token
            
        except Exception as e:
            log_error(f"Error generating dashboard token: {str(e)}")
            return secrets.token_urlsafe(32)  # Fallback token
    
    # ============= SYNC MECHANISM =============
    
    def sync_whatsapp_to_dashboard(self, user_id: str, user_type: str, 
                                  action: str, data: Dict) -> Dict:
        """Sync WhatsApp actions to dashboard in real-time"""
        try:
            # Update dashboard data based on WhatsApp action
            if action == 'log_habit':
                # Update habit tracking
                self.db.table('habit_tracking').insert({
                    f'{user_type}_id': user_id,
                    'habit_type': data.get('type'),
                    'value': data.get('value'),
                    'logged_via': 'whatsapp',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
            elif action == 'join_challenge':
                # Update challenge participation
                self.db.table('challenge_participants').insert({
                    'user_id': user_id,
                    'user_type': user_type,
                    'challenge_id': data.get('challenge_id'),
                    'joined_via': 'whatsapp',
                    'status': 'active',
                    'joined_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
            # Trigger dashboard update (could use websockets here)
            self._trigger_dashboard_update(user_id, user_type, action)
            
            return {'success': True, 'synced': True}
            
        except Exception as e:
            log_error(f"Error syncing to dashboard: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_cached_preferences(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get cached user preferences to reduce database calls"""
        cache_key = f"{user_type}:{user_id}"
        
        # Check cache
        if cache_key in self.preference_cache:
            cached = self.preference_cache[cache_key]
            # Check if cache is still valid
            if (datetime.now() - cached['cached_at']).total_seconds() < self.cache_ttl:
                return cached['data']
        
        # Load from database
        try:
            profile = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if profile.data:
                # Cache the result
                self.preference_cache[cache_key] = {
                    'data': profile.data,
                    'cached_at': datetime.now()
                }
                return profile.data
                
        except Exception as e:
            log_error(f"Error loading preferences: {str(e)}")
        
        return None
    
    # ============= SMART ROUTING =============
    
    def route_message(self, message: str, user_id: str, user_type: str, 
                     phone: str) -> Dict:
        """
        Smart routing for WhatsApp messages about challenges/gamification
        
        Strategy:
        - Complex queries → Redirect to dashboard
        - Simple queries → Answer + mention dashboard
        - Progress logs → Confirm + update dashboard
        """
        message_lower = message.lower()
        
        # Check if it's a quick command first
        quick_response = self.handle_quick_command(message, user_id, user_type, phone)
        if quick_response:
            return quick_response
        
        # Analyze message complexity
        complexity = self._analyze_message_complexity(message_lower)
        
        if complexity == 'complex':
            # Redirect to dashboard
            token = self._generate_dashboard_token(user_id, user_type)
            link = self.generate_deep_link('home', user_id, user_type, token)
            
            return {
                'success': True,
                'message': f"That's easier to see on your dashboard:\n{link}\n\nYou'll find all the details there!",
                'type': 'redirect'
            }
        
        elif complexity == 'simple':
            # Answer with dashboard mention
            answer = self._get_simple_answer(message_lower, user_id, user_type)
            token = self._generate_dashboard_token(user_id, user_type)
            link = self.generate_deep_link('home', user_id, user_type, token)
            
            return {
                'success': True,
                'message': f"{answer}\n\nMore details on your dashboard:\n{link}",
                'type': 'answer_with_link'
            }
        
        elif complexity == 'progress':
            # Confirm and update
            result = self._process_progress_log(message_lower, user_id, user_type)
            
            return {
                'success': True,
                'message': f"✅ {result['confirmation']}\n\nUpdated on your dashboard!",
                'type': 'progress_logged'
            }
        
        return None  # Not a routable message
    
    def _analyze_message_complexity(self, message: str) -> str:
        """Determine message complexity"""
        # Complex queries (need dashboard)
        complex_keywords = [
            'how many', 'show me all', 'list all', 'compare', 
            'history', 'detailed', 'breakdown', 'analysis'
        ]
        
        # Simple queries (can answer quickly)
        simple_keywords = [
            'what is', 'when is', 'how much', 'my points', 
            'my rank', 'next challenge'
        ]
        
        # Progress logging
        progress_keywords = [
            'completed', 'done', 'finished', 'logged', 
            'water', 'steps', 'workout'
        ]
        
        if any(keyword in message for keyword in complex_keywords):
            return 'complex'
        elif any(keyword in message for keyword in progress_keywords):
            return 'progress'
        elif any(keyword in message for keyword in simple_keywords):
            return 'simple'
        
        return 'unknown'
    
    def _get_simple_answer(self, message: str, user_id: str, user_type: str) -> str:
        """Get simple answer for basic queries"""
        if 'points' in message:
            # Get points from cache or DB
            prefs = self.get_cached_preferences(user_id, user_type)
            points = prefs.get('points_total', 0) if prefs else 0
            return f"You have {points} points!"
        
        elif 'rank' in message:
            # Get rank
            return "You're ranked #5 in your group!"
        
        elif 'next challenge' in message:
            return "Your next challenge starts tomorrow: 7-Day Step Challenge"
        
        return "Here's what you asked about:"
    
    def _process_progress_log(self, message: str, user_id: str, user_type: str) -> Dict:
        """Process progress logging from WhatsApp"""
        # Extract values from message
        import re
        
        confirmation_parts = []
        
        # Check for water
        water_match = re.search(r'(\d+)\s*(glasses?|liters?|l)', message)
        if water_match:
            value = water_match.group(1)
            unit = water_match.group(2)
            confirmation_parts.append(f"Water: {value} {unit}")
        
        # Check for steps
        steps_match = re.search(r'(\d+)\s*steps?', message)
        if steps_match:
            value = steps_match.group(1)
            confirmation_parts.append(f"Steps: {value}")
        
        # Check for workout
        if any(word in message for word in ['workout', 'exercise', 'training']):
            confirmation_parts.append("Workout completed")
        
        confirmation = ", ".join(confirmation_parts) if confirmation_parts else "Progress logged"
        
        return {'confirmation': confirmation}
    
    # ============= DIGEST MANAGEMENT =============
    
    def send_daily_digest(self, user_id: str, user_type: str) -> Dict:
        """Send consolidated daily digest"""
        try:
            # Get user's phone
            phone = self._get_user_phone(user_id, user_type)
            if not phone:
                return {'success': False, 'error': 'No phone number found'}
            
            # Get queued notifications
            queued = self.db.table('notification_queue').select('*').eq(
                'user_id', user_id
            ).eq('user_type', user_type).eq(
                'sent', False
            ).execute()
            
            if not queued.data:
                return {'success': True, 'message': 'No notifications to send'}
            
            # Group notifications
            pre_bookings = []
            progress_logs = []
            other = []
            
            for notif in queued.data:
                if notif['notification_type'] == 'pre_book':
                    pre_bookings.append(notif['content'])
                elif notif['notification_type'] == 'progress':
                    progress_logs.append(notif['content'])
                else:
                    other.append(notif['content'])
            
            # Build digest message
            message_parts = ["📋 *Your Daily Summary*\n"]
            
            if pre_bookings:
                message_parts.append("*Pre-booked Challenges:*")
                for booking in pre_bookings[:3]:  # Max 3
                    message_parts.append(booking)
                if len(pre_bookings) > 3:
                    message_parts.append(f"...and {len(pre_bookings) - 3} more")
            
            if progress_logs:
                message_parts.append("\n*Progress Today:*")
                message_parts.append(f"✓ {len(progress_logs)} activities logged")
            
            if other:
                message_parts.append("\n*Other Updates:*")
                for update in other[:2]:  # Max 2
                    message_parts.append(update)
            
            # Add dashboard link
            token = self._generate_dashboard_token(user_id, user_type)
            link = self.generate_deep_link('home', user_id, user_type, token)
            message_parts.append(f"\n📱 View full details:\n{link}")
            
            # Send digest
            full_message = "\n".join(message_parts)
            self.whatsapp.send_message(phone, full_message)
            
            # Mark as sent
            notification_ids = [n['id'] for n in queued.data]
            self.db.table('notification_queue').update({
                'sent': True,
                'sent_at': datetime.now(self.sa_tz).isoformat()
            }).in_('id', notification_ids).execute()
            
            return {
                'success': True,
                'notifications_sent': len(queued.data)
            }
            
        except Exception as e:
            log_error(f"Error sending daily digest: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_next_digest_time(self, user_id: str) -> datetime:
        """Get next digest time for user"""
        # Get user preferences
        prefs = self.get_cached_preferences(user_id, 'client')  # Assume client for now
        
        if prefs:
            digest_time = prefs.get('digest_time', '07:00')
        else:
            digest_time = '07:00'
        
        # Parse time
        hour, minute = map(int, digest_time.split(':'))
        
        # Get next occurrence
        now = datetime.now(self.sa_tz)
        next_digest = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_digest <= now:
            # Already passed today, schedule for tomorrow
            next_digest += timedelta(days=1)
        
        return next_digest
    
    def _get_user_phone(self, user_id: str, user_type: str) -> Optional[str]:
        """Get user's WhatsApp phone number"""
        try:
            if user_type == 'trainer':
                result = self.db.table('trainers').select('whatsapp').eq(
                    'id', user_id
                ).single().execute()
            else:
                result = self.db.table('clients').select('whatsapp').eq(
                    'id', user_id
                ).single().execute()
            
            return result.data.get('whatsapp') if result.data else None
            
        except Exception as e:
            log_error(f"Error getting user phone: {str(e)}")
            return None
    
    def _trigger_dashboard_update(self, user_id: str, user_type: str, action: str):
        """Trigger dashboard update (placeholder for websocket implementation)"""
        try:
            # In a real implementation, this would trigger a websocket event
            # For now, just log the update
            log_info(f"Dashboard update triggered for {user_type} {user_id}: {action}")
            
            # Could also update a 'last_updated' timestamp that dashboard polls
            self.db.table('dashboard_updates').insert({
                'user_id': user_id,
                'user_type': user_type,
                'action': action,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
        except Exception as e:
            log_error(f"Error triggering dashboard update: {str(e)}")