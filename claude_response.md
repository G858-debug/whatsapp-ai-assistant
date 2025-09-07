<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5386 -->
<!-- Tokens: ~102,575 -->

## ANALYSIS
Need to implement the LeaderboardService class in services/gamification.py to handle leaderboard functionality with personal ranking visibility, context windows, and milestone notifications. The service will update rankings hourly, handle different scopes, respect privacy settings, and generate WhatsApp-friendly leaderboard displays.

## FILES TO CHANGE

### FILE: services/gamification.py
```python
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional
from utils.logger import log_error, log_info

class BadgeChecker:
    """Handles badge evaluation and awarding"""
    
    def __init__(self, config, supabase_client, whatsapp_service):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
    def check_badges(self, user_id: str, user_type: str = 'client') -> List[Dict]:
        """Check if user has earned any new badges"""
        try:
            # Get all available badges
            badges = self.db.table('badges').select('*').execute()
            
            # Get user's existing badges
            user_badges = self.db.table('user_badges').select('badge_id').eq(
                'user_id', user_id
            ).eq('user_type', user_type).execute()
            
            earned_badge_ids = [b['badge_id'] for b in (user_badges.data or [])]
            newly_earned = []
            
            for badge in (badges.data or []):
                # Skip if already earned
                if badge['id'] in earned_badge_ids:
                    continue
                
                # Check if badge criteria is met
                if self._check_badge_criteria(user_id, user_type, badge):
                    # Award the badge
                    self._award_badge(user_id, user_type, badge)
                    newly_earned.append(badge)
            
            return newly_earned
            
        except Exception as e:
            log_error(f"Error checking badges: {str(e)}")
            return []
    
    def _check_badge_criteria(self, user_id: str, user_type: str, badge: Dict) -> bool:
        """Check if user meets badge criteria"""
        try:
            criteria_type = badge['criteria_type']
            criteria_value = badge['criteria_value']
            
            if criteria_type == 'first_workout':
                # Check if user has completed at least one workout
                result = self.db.table('workout_history').select('id').eq(
                    f'{user_type}_id', user_id
                ).eq('completed', True).limit(1).execute()
                return bool(result.data)
                
            elif criteria_type == 'workout_streak':
                # Check workout streak
                streak = self._get_current_streak(user_id, user_type)
                return streak >= criteria_value
                
            elif criteria_type == 'challenge_wins':
                # Check challenge wins
                result = self.db.table('challenge_history').select('id').eq(
                    f'{user_type}_id', user_id
                ).eq('status', 'won').execute()
                return len(result.data or []) >= criteria_value
                
            elif criteria_type == 'points_milestone':
                # Check total points
                result = self.db.table('user_points').select('total_points').eq(
                    f'{user_type}_id', user_id
                ).single().execute()
                if result.data:
                    return result.data['total_points'] >= criteria_value
            
            return False
            
        except Exception as e:
            log_error(f"Error checking badge criteria: {str(e)}")
            return False
    
    def _award_badge(self, user_id: str, user_type: str, badge: Dict):
        """Award badge to user"""
        try:
            # Add badge to user's collection
            self.db.table('user_badges').insert({
                'user_id': user_id,
                'user_type': user_type,
                'badge_id': badge['id'],
                'earned_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Award points if specified
            if badge.get('points_value'):
                self._add_points(user_id, user_type, badge['points_value'])
            
            # Get user's contact info
            if user_type == 'client':
                user = self.db.table('clients').select('name, whatsapp').eq(
                    'id', user_id
                ).single().execute()
            else:
                user = self.db.table('trainers').select('name, whatsapp').eq(
                    'id', user_id
                ).single().execute()
            
            if user.data:
                # Send WhatsApp notification
                message = f"""🏆 *Achievement Unlocked!*

Congratulations {user.data['name']}!
You've earned the {badge['icon_emoji']} *{badge['name']}* badge!

_{badge['description']}_

+{badge['points_value']} points added to your profile! 🌟"""
                
                self.whatsapp.send_message(user.data['whatsapp'], message)
            
        except Exception as e:
            log_error(f"Error awarding badge: {str(e)}")
    
    def _add_points(self, user_id: str, user_type: str, points: int):
        """Add points to user's total"""
        try:
            # Get current points
            result = self.db.table('user_points').select('total_points').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if result.data:
                # Update existing
                new_total = result.data['total_points'] + points
                self.db.table('user_points').update({
                    'total_points': new_total,
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq(f'{user_type}_id', user_id).execute()
            else:
                # Create new entry
                self.db.table('user_points').insert({
                    f'{user_type}_id': user_id,
                    'total_points': points,
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
        except Exception as e:
            log_error(f"Error adding points: {str(e)}")
    
    def _get_current_streak(self, user_id: str, user_type: str) -> int:
        """Calculate current workout streak"""
        try:
            # Get workouts ordered by date
            result = self.db.table('workout_history').select('*').eq(
                f'{user_type}_id', user_id
            ).order('completed_at', desc=True).execute()
            
            if not result.data:
                return 0
            
            streak = 0
            last_date = None
            
            for workout in result.data:
                workout_date = datetime.fromisoformat(workout['completed_at']).date()
                
                if last_date is None:
                    last_date = workout_date
                    streak = 1
                    continue
                
                # Check if this workout is consecutive
                date_diff = (last_date - workout_date).days
                
                if date_diff == 1:
                    streak += 1
                    last_date = workout_date
                else:
                    break
            
            return streak
            
        except Exception as e:
            log_error(f"Error calculating streak: {str(e)}")
            return 0


class LeaderboardService:
    """Handles leaderboard management with personal ranking visibility"""
    
    def __init__(self, config, supabase_client, whatsapp_service):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
    def update_leaderboard_rankings(self, leaderboard_id: str) -> bool:
        """Update rankings for a specific leaderboard (called hourly)"""
        try:
            log_info(f"Updating rankings for leaderboard {leaderboard_id}")
            
            # Get all entries for this leaderboard
            entries = self.db.table('leaderboard_entries').select('*').eq(
                'leaderboard_id', leaderboard_id
            ).order('points', desc=True).execute()
            
            if not entries.data:
                return True
            
            # Update rankings with trend tracking
            for idx, entry in enumerate(entries.data, 1):
                current_rank = idx
                previous_rank = entry.get('rank', current_rank)
                
                # Determine trend
                if previous_rank == current_rank:
                    trend = 'same'
                elif previous_rank > current_rank:
                    trend = 'up'
                else:
                    trend = 'down'
                
                # Update entry
                self.db.table('leaderboard_entries').update({
                    'previous_rank': previous_rank,
                    'rank': current_rank,
                    'trend': trend,
                    'last_updated': datetime.now(self.sa_tz).isoformat()
                }).eq('id', entry['id']).execute()
                
                # Check for milestone achievements
                self._check_ranking_milestones(entry, current_rank, previous_rank)
            
            log_info(f"Updated {len(entries.data)} rankings for leaderboard {leaderboard_id}")
            return True
            
        except Exception as e:
            log_error(f"Error updating leaderboard rankings: {str(e)}")
            return False
    
    def _check_ranking_milestones(self, entry: Dict, current_rank: int, previous_rank: int):
        """Check and notify for ranking milestones"""
        try:
            # Skip if no improvement
            if current_rank >= previous_rank and previous_rank != 0:
                return
            
            # Determine milestone
            milestone_message = None
            
            if current_rank <= 10 and previous_rank > 10:
                milestone_message = "🏆 CHAMPION STATUS! You've made the TOP 10!"
            elif current_rank <= 50 and previous_rank > 50:
                milestone_message = "🌟 Incredible! You're in the TOP 50!"
            elif current_rank <= 100 and previous_rank > 100:
                milestone_message = "🎉 Amazing! You've broken into the TOP 100!"
            
            # Check for personal best
            if current_rank < entry.get('best_rank', float('inf')):
                self.db.table('leaderboard_entries').update({
                    'best_rank': current_rank
                }).eq('id', entry['id']).execute()
                
                if not milestone_message:
                    milestone_message = f"🎯 New personal best! Rank #{current_rank} is your highest yet!"
            
            # Send notification if milestone achieved
            if milestone_message:
                self._send_milestone_notification(entry, milestone_message)
                
        except Exception as e:
            log_error(f"Error checking ranking milestones: {str(e)}")
    
    def _send_milestone_notification(self, entry: Dict, message: str):
        """Send milestone achievement notification"""
        try:
            # Get user contact info
            if entry['user_type'] == 'client':
                user = self.db.table('clients').select('whatsapp').eq(
                    'id', entry['user_id']
                ).single().execute()
            else:
                user = self.db.table('trainers').select('whatsapp').eq(
                    'id', entry['user_id']
                ).single().execute()
            
            if user.data and user.data.get('whatsapp'):
                self.whatsapp.send_message(user.data['whatsapp'], message)
                
        except Exception as e:
            log_error(f"Error sending milestone notification: {str(e)}")
    
    def get_leaderboard(self, leaderboard_id: str, user_id: str, user_type: str) -> str:
        """Get formatted leaderboard with user's position and context"""
        try:
            # Get leaderboard info
            leaderboard = self.db.table('leaderboards').select('*').eq(
                'id', leaderboard_id
            ).single().execute()
            
            if not leaderboard.data:
                return "Leaderboard not found."
            
            # Check privacy settings
            profile = self._get_user_gamification_profile(user_id, user_type)
            if not profile:
                return "Please set up your gamification profile first."
            
            # Get all entries
            all_entries = self.db.table('leaderboard_entries').select('*').eq(
                'leaderboard_id', leaderboard_id
            ).order('rank').execute()
            
            if not all_entries.data:
                return f"🏆 *{leaderboard.data['name']}*\n\nNo participants yet. Be the first!"
            
            # Find user's entry
            user_entry = None
            user_rank = None
            for entry in all_entries.data:
                if entry['user_id'] == user_id and entry['user_type'] == user_type:
                    user_entry = entry
                    user_rank = entry['rank']
                    break
            
            # Generate formatted leaderboard
            return self._format_leaderboard_display(
                leaderboard.data,
                all_entries.data,
                user_entry,
                user_rank,
                profile
            )
            
        except Exception as e:
            log_error(f"Error getting leaderboard: {str(e)}")
            return "Error loading leaderboard. Please try again."
    
    def _format_leaderboard_display(self, leaderboard: Dict, entries: List[Dict], 
                                   user_entry: Optional[Dict], user_rank: Optional[int],
                                   profile: Dict) -> str:
        """Format leaderboard for WhatsApp display"""
        try:
            lines = [f"🏆 *{leaderboard['name']}*\n"]
            
            # Check if user is in top 10
            if user_rank and user_rank <= 10:
                # Show top 10 with user highlighted
                for entry in entries[:10]:
                    rank = entry['rank']
                    
                    # Add medal for top 3
                    if rank == 1:
                        medal = "🥇"
                    elif rank == 2:
                        medal = "🥈"
                    elif rank == 3:
                        medal = "🥉"
                    else:
                        medal = ""
                    
                    # Check if this is the user
                    if entry['user_id'] == user_entry['user_id']:
                        # Highlight user's position
                        trend_symbol = self._get_trend_symbol(entry)
                        nickname = profile.get('nickname', 'You')
                        lines.append(f"{rank}. ➡️ You ({nickname}) - {entry['points']} pts {trend_symbol}")
                    else:
                        # Show other users (respecting privacy)
                        display_name = self._get_display_name(entry)
                        lines.append(f"{rank}. {medal} {display_name} - {entry['points']} pts")
            
            elif user_rank and user_rank > 10:
                # Show top 10
                for entry in entries[:10]:
                    rank = entry['rank']
                    
                    if rank == 1:
                        medal = "🥇"
                    elif rank == 2:
                        medal = "🥈"
                    elif rank == 3:
                        medal = "🥉"
                    else:
                        medal = ""
                    
                    display_name = self._get_display_name(entry)
                    lines.append(f"{rank}. {medal} {display_name} - {entry['points']} pts")
                
                # If user is rank 11-15, show both top 10 and context
                if 11 <= user_rank <= 15:
                    lines.append("")  # Empty line
                
                # Show ellipsis if user is not immediately after top 10
                if user_rank > 15:
                    lines.append("...")
                    lines.append("")
                
                # Show user's neighborhood (context window)
                lines.append("📍 *Your Neighborhood:*")
                
                # Get 2 users above and 2 below
                start_idx = max(0, user_rank - 3)
                end_idx = min(len(entries), user_rank + 2)
                
                for i in range(start_idx, end_idx):
                    entry = entries[i]
                    rank = entry['rank']
                    
                    if entry['user_id'] == user_entry['user_id']:
                        # Highlight user
                        trend_symbol = self._get_trend_symbol(entry)
                        nickname = profile.get('nickname', 'You')
                        lines.append(f"➡️ {rank}. You ({nickname}) - {entry['points']} pts {trend_symbol}")
                    else:
                        display_name = self._get_display_name(entry)
                        lines.append(f"{rank}. {display_name} - {entry['points']} pts")
            
            # Add user stats if they're participating
            if user_entry:
                lines.extend(self._format_user_stats(user_entry, entries))
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error formatting leaderboard display: {str(e)}")
            return "Error formatting leaderboard."
    
    def _format_user_stats(self, user_entry: Dict, all_entries: List[Dict]) -> List[str]:
        """Format user statistics section"""
        lines = ["\n📊 *Your Stats:*"]
        
        # Position and movement
        rank = user_entry['rank']
        previous_rank = user_entry.get('previous_rank', rank)
        
        if previous_rank != rank:
            if previous_rank > rank:
                movement = f"↑ moved up {previous_rank - rank} spots today!"
            else:
                movement = f"↓ moved down {rank - previous_rank} spots"
            lines.append(f"Position: #{rank} ({movement})")
        else:
            lines.append(f"Position: #{rank} (no change)")
        
        # Points to next position
        if rank > 1:
            next_entry = all_entries[rank - 2]  # Entry above current user
            points_needed = next_entry['points'] - user_entry['points']
            lines.append(f"Points to #{rank-1}: {points_needed} pts")
        
        # Points to milestones (if not already achieved)
        if rank > 10:
            top_10_entry = all_entries[9] if len(all_entries) > 9 else None
            if top_10_entry:
                points_to_top10 = top_10_entry['points'] - user_entry['points']
                lines.append(f"Points to top 10: {points_to_top10} pts")
        
        if rank > 100:
            top_100_entry = all_entries[99] if len(all_entries) > 99 else None
            if top_100_entry:
                points_to_top100 = top_100_entry['points'] - user_entry['points']
                lines.append(f"Points to top 100: {points_to_top100} pts")
        
        # Percentage ranking
        total_participants = len(all_entries)
        percentile = ((total_participants - rank + 1) / total_participants) * 100
        lines.append(f"You're in the top {percentile:.1f}% of all participants")
        
        # Motivational message
        if rank <= 10:
            lines.append("\n🏆 Outstanding performance! Keep it up!")
        elif rank <= 50:
            lines.append("\n💪 Great job! You're doing amazing!")
        elif rank <= 100:
            lines.append("\n🎯 Good progress! Keep pushing!")
        else:
            lines.append("\n📈 Keep going! Every point counts!")
        
        return lines
    
    def _get_trend_symbol(self, entry: Dict) -> str:
        """Get trend symbol for ranking change"""
        trend = entry.get('trend', 'same')
        previous_rank = entry.get('previous_rank', entry['rank'])
        current_rank = entry['rank']
        
        if trend == 'up' and previous_rank > current_rank:
            change = previous_rank - current_rank
            return f"↑{change}"
        elif trend == 'down' and previous_rank < current_rank:
            change = current_rank - previous_rank
            return f"↓{change}"
        else:
            return ""
    
    def _get_display_name(self, entry: Dict) -> str:
        """Get display name respecting privacy settings"""
        try:
            # Check if user has public profile
            profile = self._get_user_gamification_profile(entry['user_id'], entry['user_type'])
            
            if profile and profile.get('is_public'):
                return entry.get('nickname', 'Anonymous')
            else:
                # Show anonymous for private profiles
                return 'Anonymous'
                
        except Exception:
            return 'Anonymous'
    
    def _get_user_gamification_profile(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get user's gamification profile"""
        try:
            if user_type == 'client':
                result = self.db.table('gamification_profiles').select('*').eq(
                    'client_id', user_id
                ).single().execute()
            else:
                result = self.db.table('gamification_profiles').select('*').eq(
                    'trainer_id', user_id
                ).single().execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            log_error(f"Error getting gamification profile: {str(e)}")
            return None
    
    def create_leaderboard(self, name: str, leaderboard_type: str, scope: str,
                          start_date: str, end_date: str) -> Dict:
        """Create a new leaderboard"""
        try:
            result = self.db.table('leaderboards').insert({
                'name': name,
                'type': leaderboard_type,
                'scope': scope,
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            if result.data:
                log_info(f"Created leaderboard: {name}")
                return {'success': True, 'leaderboard_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to create leaderboard'}
            
        except Exception as e:
            log_error(f"Error creating leaderboard: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_user_to_leaderboard(self, leaderboard_id: str, user_id: str, 
                               user_type: str, nickname: str) -> bool:
        """Add user to a leaderboard"""
        try:
            # Check if user already in leaderboard
            existing = self.db.table('leaderboard_entries').select('id').eq(
                'leaderboard_id', leaderboard_id
            ).eq('user_id', user_id).eq('user_type', user_type).execute()
            
            if existing.data:
                return True  # Already in leaderboard
            
            # Add user to leaderboard
            result = self.db.table('leaderboard_entries').insert({
                'leaderboard_id': leaderboard_id,
                'user_id': user_id,
                'user_type': user_type,
                'nickname': nickname,
                'points': 0,
                'rank': 999999,  # Will be updated on next ranking update
                'trend': 'same',
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'last_updated': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error adding user to leaderboard: {str(e)}")
            return False
    
    def update_user_points(self, leaderboard_id: str, user_id: str, 
                          user_type: str, points_to_add: int) -> bool:
        """Update user's points in a leaderboard"""
        try:
            # Get current entry
            entry = self.db.table('leaderboard_entries').select('*').eq(
                'leaderboard_id', leaderboard_id
            ).eq('user_id', user_id).eq('user_type', user_type).single().execute()
            
            if not entry.data:
                return False
            
            # Update points
            new_points = entry.data['points'] + points_to_add
            
            result = self.db.table('leaderboard_entries').update({
                'points': new_points,
                'last_updated': datetime.now(self.sa_tz).isoformat()
            }).eq('id', entry.data['id']).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating user points: {str(e)}")
            return False
    
    def get_active_leaderboards(self, scope: Optional[str] = None) -> List[Dict]:
        """Get all active leaderboards, optionally filtered by scope"""
        try:
            query = self.db.table('leaderboards').select('*').eq('is_active', True)
            
            if scope:
                query = query.eq('scope', scope)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting active leaderboards: {str(e)}")
            return []
```

## MIGRATION: 20250103000001_leaderboard_tables.sql
```sql
-- Create leaderboards table
CREATE TABLE IF NOT EXISTS leaderboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'points', 'challenge', 'workout', 'habit'
    scope VARCHAR(50) NOT NULL, -- 'global', 'trainer-only', 'client-group'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create leaderboard_entries table
CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    leaderboard_id UUID NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('client', 'trainer')),
    nickname VARCHAR(100),
    points INTEGER NOT NULL DEFAULT 0,
    rank INTEGER,
    previous_rank INTEGER,
    best_rank INTEGER,
    trend VARCHAR(10) CHECK (trend IN ('up', 'down', 'same')),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leaderboard_id, user_id, user_type)
);

-- Create indexes for performance
CREATE INDEX idx_leaderboards_active ON leaderboards(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_leaderboards_scope ON leaderboards(scope);
CREATE INDEX idx_leaderboards_dates ON leaderboards(start_date, end_date);

CREATE INDEX idx_leaderboard_entries_leaderboard ON leaderboard_entries(leaderboard_id);
CREATE INDEX idx_leaderboard_entries_user ON leaderboard_entries(user_id, user_type);
CREATE INDEX idx_leaderboard_entries_rank ON leaderboard_entries(leaderboard_id, rank);
CREATE INDEX idx_leaderboard_entries_points ON leaderboard_entries(leaderboard_id, points DESC);

-- Insert sample leaderboards
INSERT INTO leaderboards (name, type, scope, start_date, end_date) VALUES
('Water Challenge Leaderboard', 'habit', 'global', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days'),
('January Fitness Challenge', 'points', 'global', '2025-01-01', '2025-01-31'),
('Weekly Steps Challenge', 'habit', 'trainer-only', CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days');
```

## SUMMARY
1. Added `LeaderboardService` class to `services/gamification.py` with complete functionality for:
   - Hourly ranking updates with trend tracking
   - Different scopes (global, trainer-only, client-group)
   - Privacy-respecting display names
   - WhatsApp-formatted leaderboard displays with context windows
   - Milestone notifications for ranking achievements
   - Personal best tracking
   - User stats including percentile ranking and points to next positions

2. Created migration for leaderboard database tables with proper indexes for performance

3. The service provides intelligent leaderboard displays that:
   - Show top 10 with user highlighted if they're in it
   - Show user's neighborhood (context window) if they're outside top 10
   - Display both top 10 and context for users ranked 11-15
   - Include trend indicators and motivational messages
   - Calculate percentile rankings and points needed for milestones