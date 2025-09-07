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
                result = self.db.table('challenge_participants').select('id').eq(
                    'user_id', user_id
                ).eq('user_type', user_type).eq('final_position', 1).execute()
                return len(result.data or []) >= criteria_value
                
            elif criteria_type == 'points_milestone':
                # Check total points
                result = self.db.table('gamification_profiles').select('points_total').eq(
                    f'{user_type}_id', user_id
                ).single().execute()
                if result.data:
                    return result.data['points_total'] >= criteria_value
            
            elif criteria_type == 'total_workouts':
                # Check total workout count
                result = self.db.table('workout_history').select('id').eq(
                    f'{user_type}_id', user_id
                ).eq('completed', True).execute()
                return len(result.data or []) >= criteria_value
                
            elif criteria_type == 'improvement':
                # Check for 10% improvement in assessments
                return self._check_improvement(user_id, user_type, criteria_value)
            
            return False
            
        except Exception as e:
            log_error(f"Error checking badge criteria: {str(e)}")
            return False
    
    def _check_improvement(self, user_id: str, user_type: str, required_percentage: float) -> bool:
        """Check if user has improved by required percentage"""
        try:
            # Get latest two assessments
            assessments = self.db.table('fitness_assessments').select('*').eq(
                f'{user_type}_id', user_id
            ).order('assessment_date', desc=True).limit(2).execute()
            
            if not assessments.data or len(assessments.data) < 2:
                return False
            
            latest = assessments.data[0]
            previous = assessments.data[1]
            
            # Check weight improvement (loss)
            if latest.get('weight_kg') and previous.get('weight_kg'):
                weight_change = ((previous['weight_kg'] - latest['weight_kg']) / previous['weight_kg']) * 100
                if weight_change >= required_percentage:
                    return True
            
            return False
            
        except Exception as e:
            log_error(f"Error checking improvement: {str(e)}")
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
                self._add_points(user_id, user_type, badge['points_value'], f"Badge earned: {badge['name']}")
            
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
    
    def _add_points(self, user_id: str, user_type: str, points: int, reason: str = "Points earned"):
        """Add points to user's total"""
        try:
            # Add to points ledger
            self.db.table('points_ledger').insert({
                'user_id': user_id,
                'user_type': user_type,
                'points': points,
                'reason': reason,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Update gamification profile
            profile = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if profile.data:
                # Update existing
                new_total = profile.data['points_total'] + points
                self.db.table('gamification_profiles').update({
                    'points_total': new_total,
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq(f'{user_type}_id', user_id).execute()
            else:
                # Create new profile
                self.db.table('gamification_profiles').insert({
                    f'{user_type}_id': user_id,
                    'points_total': points,
                    'is_public': True,
                    'opted_in_global': True,
                    'opted_in_trainer': True,
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
        except Exception as e:
            log_error(f"Error adding points: {str(e)}")
    
    def _get_current_streak(self, user_id: str, user_type: str) -> int:
        """Calculate current workout streak"""
        try:
            # Get workouts ordered by date
            result = self.db.table('workout_history').select('*').eq(
                f'{user_type}_id', user_id
            ).order('sent_at', desc=True).execute()
            
            if not result.data:
                return 0
            
            streak = 0
            last_date = None
            today = datetime.now(self.sa_tz).date()
            
            for workout in result.data:
                workout_date = datetime.fromisoformat(workout['sent_at']).date()
                
                # Skip if in the future
                if workout_date > today:
                    continue
                
                if last_date is None:
                    # First workout - check if it's recent enough
                    if (today - workout_date).days <= 1:
                        last_date = workout_date
                        streak = 1
                    else:
                        break
                else:
                    # Check if consecutive
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


class ChallengeManager:
    """Manages challenge creation and administration for trainers"""
    
    def __init__(self, config, supabase_client, whatsapp_service):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
    def create_challenge(self, trainer_id: str, name: str, challenge_type: str, 
                        duration_days: int, target_value: float = None, 
                        description: str = None, max_participants: int = None) -> Dict:
        """Create a new challenge for trainer's clients"""
        try:
            # Calculate dates
            start_date = datetime.now(self.sa_tz).date()
            end_date = start_date + timedelta(days=duration_days)
            
            # Determine challenge type details
            challenge_types = {
                'water': {'description': 'Daily water intake challenge', 'unit': 'liters', 'default_target': 2.5},
                'steps': {'description': 'Daily steps challenge', 'unit': 'steps', 'default_target': 10000},
                'workout': {'description': 'Workout completion challenge', 'unit': 'sessions', 'default_target': duration_days * 0.7},
                'sleep': {'description': 'Sleep tracking challenge', 'unit': 'hours', 'default_target': 8},
                'weight_loss': {'description': 'Weight loss challenge', 'unit': 'kg', 'default_target': 2},
                'custom': {'description': description or 'Custom fitness challenge', 'unit': 'points', 'default_target': 100}
            }
            
            type_info = challenge_types.get(challenge_type, challenge_types['custom'])
            
            # Use provided target or default
            if target_value is None:
                target_value = type_info['default_target']
            
            # Calculate points reward based on duration and difficulty
            base_points = 100
            duration_multiplier = min(duration_days / 7, 4)  # Max 4x for long challenges
            points_reward = int(base_points * duration_multiplier)
            
            # Create challenge
            challenge_data = {
                'created_by': trainer_id,
                'name': name,
                'description': description or type_info['description'],
                'type': 'trainer_wide',  # Trainer-created challenges are trainer-wide
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'target_value': target_value,
                'points_reward': points_reward,
                'is_active': True,
                'max_participants': max_participants,
                'challenge_rules': {
                    'challenge_type': challenge_type,
                    'unit': type_info['unit'],
                    'daily_tracking': challenge_type in ['water', 'steps', 'sleep'],
                    'cumulative': challenge_type in ['workout', 'weight_loss'],
                    'duration_days': duration_days
                }
            }
            
            result = self.db.table('challenges').insert(challenge_data).execute()
            
            if result.data:
                challenge_id = result.data[0]['id']
                log_info(f"Created challenge {name} (ID: {challenge_id}) for trainer {trainer_id}")
                
                return {
                    'success': True,
                    'challenge_id': challenge_id,
                    'message': f"""✨ *Challenge Created Successfully!*

📋 *{name}*
⏱️ Duration: {duration_days} days
🎯 Target: {target_value} {type_info['unit']}
🏆 Reward: {points_reward} points
📅 Starts: {start_date.strftime('%d %B')}

Ready to invite your clients! Use "invite clients to {name}" to send invitations."""
                }
            
            return {'success': False, 'error': 'Failed to create challenge'}
            
        except Exception as e:
            log_error(f"Error creating challenge: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def list_trainer_challenges(self, trainer_id: str, active_only: bool = True) -> Dict:
        """List all challenges created by a trainer"""
        try:
            query = self.db.table('challenges').select('*').eq('created_by', trainer_id)
            
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('created_at', desc=True).execute()
            
            if not result.data:
                return {
                    'success': True,
                    'challenges': [],
                    'message': "No challenges found. Create one with 'create challenge'!"
                }
            
            # Format challenges for display
            challenges_text = "📊 *Your Active Challenges*\n\n"
            
            for idx, challenge in enumerate(result.data, 1):
                # Get participant count
                participants = self.db.table('challenge_participants').select('id').eq(
                    'challenge_id', challenge['id']
                ).execute()
                
                participant_count = len(participants.data) if participants.data else 0
                
                # Calculate days remaining
                end_date = datetime.strptime(challenge['end_date'], '%Y-%m-%d').date()
                days_remaining = (end_date - datetime.now(self.sa_tz).date()).days
                
                status_emoji = "🟢" if days_remaining > 0 else "🔴"
                
                challenges_text += f"""{idx}. {status_emoji} *{challenge['name']}*
   👥 Participants: {participant_count}
   📅 Ends: {end_date.strftime('%d %B')} ({days_remaining} days left)
   🏆 Reward: {challenge['points_reward']} points
   
"""
            
            return {
                'success': True,
                'challenges': result.data,
                'message': challenges_text
            }
            
        except Exception as e:
            log_error(f"Error listing challenges: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def invite_clients_to_challenge(self, trainer_id: str, challenge_id: str, 
                                   client_ids: List[str] = None) -> Dict:
        """Send WhatsApp invitations to clients for a challenge"""
        try:
            # Get challenge details
            challenge = self.db.table('challenges').select('*').eq(
                'id', challenge_id
            ).eq('created_by', trainer_id).single().execute()
            
            if not challenge.data:
                return {'success': False, 'error': 'Challenge not found'}
            
            # Get clients to invite
            if client_ids:
                # Specific clients
                clients = self.db.table('clients').select('*').in_('id', client_ids).execute()
            else:
                # All trainer's clients
                clients = self.db.table('clients').select('*').eq(
                    'trainer_id', trainer_id
                ).eq('status', 'active').execute()
            
            if not clients.data:
                return {'success': False, 'error': 'No clients to invite'}
            
            invited_count = 0
            failed_invites = []
            
            for client in clients.data:
                try:
                    # Check if already participating
                    existing = self.db.table('challenge_participants').select('id').eq(
                        'challenge_id', challenge_id
                    ).eq('user_id', client['id']).eq('user_type', 'client').execute()
                    
                    if existing.data:
                        continue  # Skip if already participating
                    
                    # Add to challenge
                    self.db.table('challenge_participants').insert({
                        'challenge_id': challenge_id,
                        'user_id': client['id'],
                        'user_type': 'client',
                        'joined_at': datetime.now(self.sa_tz).isoformat(),
                        'status': 'active'
                    }).execute()
                    
                    # Send WhatsApp invitation
                    invitation_message = f"""🎯 *Challenge Invitation!*

Hi {client['name']}! You've been invited to join:

*{challenge.data['name']}*

📝 {challenge.data['description']}
🎯 Target: {challenge.data['target_value']} {challenge.data['challenge_rules'].get('unit', '')}
⏱️ Duration: {challenge.data['challenge_rules'].get('duration_days', 0)} days
🏆 Reward: {challenge.data['points_reward']} points

Ready to crush this challenge? 💪

Reply "YES" to accept or "NO" to decline."""
                    
                    self.whatsapp.send_message(client['whatsapp'], invitation_message)
                    invited_count += 1
                    
                except Exception as e:
                    log_error(f"Failed to invite client {client['id']}: {str(e)}")
                    failed_invites.append(client['name'])
            
            # Create summary message
            summary = f"✅ Invitations sent to {invited_count} clients!"
            if failed_invites:
                summary += f"\n⚠️ Failed to invite: {', '.join(failed_invites)}"
            
            return {
                'success': True,
                'invited_count': invited_count,
                'message': summary
            }
            
        except Exception as e:
            log_error(f"Error inviting clients: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def end_challenge(self, trainer_id: str, challenge_id: str) -> Dict:
        """End a challenge, calculate winners, and award points"""
        try:
            # Verify challenge ownership
            challenge = self.db.table('challenges').select('*').eq(
                'id', challenge_id
            ).eq('created_by', trainer_id).single().execute()
            
            if not challenge.data:
                return {'success': False, 'error': 'Challenge not found'}
            
            # Get all participants with their progress
            participants = self.db.table('challenge_participants').select(
                '*, challenge_progress(*)'
            ).eq('challenge_id', challenge_id).eq('status', 'active').execute()
            
            if not participants.data:
                return {'success': False, 'error': 'No active participants'}
            
            # Calculate final scores for each participant
            participant_scores = []
            
            for participant in participants.data:
                # Sum up all progress values
                total_value = sum(
                    p.get('value_achieved', 0) 
                    for p in participant.get('challenge_progress', [])
                )
                
                participant_scores.append({
                    'participant_id': participant['id'],
                    'user_id': participant['user_id'],
                    'user_type': participant['user_type'],
                    'total_value': total_value,
                    'target_reached': total_value >= challenge.data['target_value']
                })
            
            # Sort by total value to determine winners
            participant_scores.sort(key=lambda x: x['total_value'], reverse=True)
            
            # Award points and update positions
            winners_text = "🏆 *Challenge Results*\n\n"
            
            for position, scorer in enumerate(participant_scores, 1):
                # Calculate points based on position and target achievement
                if position == 1:
                    points = challenge.data['points_reward']
                    medal = "🥇"
                elif position == 2:
                    points = int(challenge.data['points_reward'] * 0.75)
                    medal = "🥈"
                elif position == 3:
                    points = int(challenge.data['points_reward'] * 0.5)
                    medal = "🥉"
                elif scorer['target_reached']:
                    points = int(challenge.data['points_reward'] * 0.25)
                    medal = "✅"
                else:
                    points = 10  # Participation points
                    medal = "👏"
                
                # Update participant record
                self.db.table('challenge_participants').update({
                    'status': 'completed',
                    'final_position': position
                }).eq('id', scorer['participant_id']).execute()
                
                # Award points
                self._award_points(scorer['user_id'], scorer['user_type'], points, challenge_id)
                
                # Get user name for display
                if scorer['user_type'] == 'client':
                    user = self.db.table('clients').select('name').eq(
                        'id', scorer['user_id']
                    ).single().execute()
                else:
                    user = self.db.table('trainers').select('name').eq(
                        'id', scorer['user_id']
                    ).single().execute()
                
                user_name = user.data['name'] if user.data else 'Unknown'
                
                # Add to results text
                if position <= 10:  # Show top 10
                    winners_text += f"{medal} {position}. {user_name}: {scorer['total_value']:.1f} ({points} points)\n"
            
            # Mark challenge as inactive
            self.db.table('challenges').update({
                'is_active': False
            }).eq('id', challenge_id).execute()
            
            winners_text += f"\n*Challenge "{challenge.data['name']}" has ended!*"
            
            # Send notifications to all participants
            self._notify_challenge_results(challenge_id, participant_scores)
            
            return {
                'success': True,
                'message': winners_text,
                'winner_count': len([s for s in participant_scores if s['target_reached']])
            }
            
        except Exception as e:
            log_error(f"Error ending challenge: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _award_points(self, user_id: str, user_type: str, points: int, challenge_id: str):
        """Award points to a user for challenge completion"""
        try:
            # Add to points ledger
            self.db.table('points_ledger').insert({
                'user_id': user_id,
                'user_type': user_type,
                'points': points,
                'reason': f'Challenge completion reward',
                'challenge_id': challenge_id,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            log_info(f"Awarded {points} points to {user_type} {user_id}")
            
        except Exception as e:
            log_error(f"Error awarding points: {str(e)}")
    
    def _notify_challenge_results(self, challenge_id: str, participant_scores: List[Dict]):
        """Send WhatsApp notifications to all participants about challenge results"""
        try:
            # Get challenge details
            challenge = self.db.table('challenges').select('*').eq(
                'id', challenge_id
            ).single().execute()
            
            if not challenge.data:
                return
            
            for scorer in participant_scores[:3]:  # Notify top 3
                # Get user contact
                if scorer['user_type'] == 'client':
                    user = self.db.table('clients').select('name, whatsapp').eq(
                        'id', scorer['user_id']
                    ).single().execute()
                else:
                    user = self.db.table('trainers').select('name, whatsapp').eq(
                        'id', scorer['user_id']
                    ).single().execute()
                
                if user.data:
                    position = participant_scores.index(scorer) + 1
                    
                    if position == 1:
                        message = f"🥇 *CONGRATULATIONS CHAMPION!*\n\nYou WON the {challenge.data['name']}! Amazing work! 🎉"
                    elif position == 2:
                        message = f"🥈 *Fantastic Achievement!*\n\nYou placed 2nd in the {challenge.data['name']}! Well done! 👏"
                    elif position == 3:
                        message = f"🥉 *Great Job!*\n\nYou placed 3rd in the {challenge.data['name']}! Keep it up! 💪"
                    
                    self.whatsapp.send_message(user.data['whatsapp'], message)
                    
        except Exception as e:
            log_error(f"Error notifying challenge results: {str(e)}")
    
    def set_challenge_reward(self, trainer_id: str, challenge_id: str, 
                            reward_type: str, reward_value: str) -> Dict:
        """Add a custom reward to a challenge"""
        try:
            # Verify challenge ownership
            challenge = self.db.table('challenges').select('*').eq(
                'id', challenge_id
            ).eq('created_by', trainer_id).single().execute()
            
            if not challenge.data:
                return {'success': False, 'error': 'Challenge not found'}
            
            # Update challenge rules with custom reward
            current_rules = challenge.data.get('challenge_rules', {})
            current_rules['custom_rewards'] = current_rules.get('custom_rewards', [])
            current_rules['custom_rewards'].append({
                'type': reward_type,
                'value': reward_value,
                'added_at': datetime.now(self.sa_tz).isoformat()
            })
            
            # Update challenge
            self.db.table('challenges').update({
                'challenge_rules': current_rules
            }).eq('id', challenge_id).execute()
            
            return {
                'success': True,
                'message': f"✅ Reward added to challenge!\n\n🎁 {reward_type}: {reward_value}"
            }
            
        except Exception as e:
            log_error(f"Error setting challenge reward: {str(e)}")
            return {'success': False, 'error': str(e)}


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
            
            # Find user's position
            user_entry = None
            user_rank = None
            total_participants = len(all_entries.data)
            
            for entry in all_entries.data:
                if entry['user_id'] == user_id and entry['user_type'] == user_type:
                    user_entry = entry
                    user_rank = entry['rank']
                    break
            
            # Build leaderboard display
            display_text = f"🏆 *{leaderboard.data['name']}*\n"
            display_text += f"_Total participants: {total_participants}_\n\n"
            
            # Show top 10
            for entry in all_entries.data[:10]:
                rank = entry['rank']
                nickname = entry.get('nickname', 'Anonymous')
                points = entry['points']
                
                # Add medals for top 3
                if rank == 1:
                    medal = "🥇"
                elif rank == 2:
                    medal = "🥈"
                elif rank == 3:
                    medal = "🥉"
                else:
                    medal = f"{rank}."
                
                # Highlight if it's the current user
                if entry['user_id'] == user_id and entry['user_type'] == user_type:
                    display_text += f"➡️ {medal} *You ({nickname})* - {points:,} pts"
                else:
                    display_text += f"{medal} {nickname} - {points:,} pts"
                
                # Add trend indicator
                if entry.get('trend') == 'up':
                    display_text += f" ↑{abs(entry.get('previous_rank', rank) - rank)}"
                elif entry.get('trend') == 'down':
                    display_text += f" ↓{abs(entry.get('previous_rank', rank) - rank)}"
                
                display_text += "\n"
            
            # If user is not in top 10, show their context window
            if user_rank and user_rank > 10:
                display_text += "\n📍 *Your Neighborhood:*\n"
                
                # Show 2 above and 2 below user's position
                start_idx = max(0, user_rank - 3)
                end_idx = min(total_participants, user_rank + 2)
                
                for i in range(start_idx, end_idx):
                    entry = all_entries.data[i]
                    rank = entry['rank']
                    nickname = entry.get('nickname', 'Anonymous')
                    points = entry['points']
                    
                    if entry['user_id'] == user_id and entry['user_type'] == user_type:
                        display_text += f"➡️ *{rank}. You ({nickname})* - {points:,} pts"
                    else:
                        display_text += f"{rank}. {nickname} - {points:,} pts"
                    
                    # Add trend
                    if entry.get('trend') == 'up':
                        display_text += f" ↑{abs(entry.get('previous_rank', rank) - rank)}"
                    elif entry.get('trend') == 'down':
                        display_text += f" ↓{abs(entry.get('previous_rank', rank) - rank)}"
                    elif entry.get('trend') == 'new':
                        display_text += " 🆕"
                    
                    display_text += "\n"
            
            # Add user stats
            if user_entry:
                display_text += "\n📊 *Your Stats:*\n"
                display_text += f"Position: #{user_rank}"
                
                # Add movement indicator
                if user_entry.get('trend') == 'up':
                    change = abs(user_entry.get('previous_rank', user_rank) - user_rank)
                    display_text += f" (↑ moved up {change} spots today!)\n"
                elif user_entry.get('trend') == 'down':
                    change = abs(user_entry.get('previous_rank', user_rank) - user_rank)
                    display_text += f" (↓ moved down {change} spots)\n"
                elif user_entry.get('trend') == 'new':
                    display_text += " (🆕 New to leaderboard!)\n"
                else:
                    display_text += " (↔️ Same as yesterday)\n"
                
                # Points to next rank
                if user_rank > 1:
                    next_entry = all_entries.data[user_rank - 2]
                    points_needed = next_entry['points'] - user_entry['points']
                    display_text += f"Points to next: {points_needed:,} pts\n"
                
                # Points to milestones
                if user_rank > 100:
                    top_100_entry = all_entries.data[99] if len(all_entries.data) > 99 else None
                    if top_100_entry:
                        points_to_100 = top_100_entry['points'] - user_entry['points']
                        display_text += f"Points to top 100: {points_to_100:,} pts\n"
                
                if user_rank > 10:
                    top_10_entry = all_entries.data[9]
                    points_to_10 = top_10_entry['points'] - user_entry['points']
                    display_text += f"Points to top 10: {points_to_10:,} pts\n"
                
                # Percentage ranking
                percentile = round((1 - (user_rank / total_participants)) * 100)
                display_text += f"\nYou're in the top {percentile}% of participants!"
                
                # Motivational message based on performance
                if user_entry.get('trend') == 'up':
                    display_text += "\n\n💪 Great progress! Keep pushing!"
                elif user_rank <= 10:
                    display_text += "\n\n🌟 Amazing work! You're in the elite!"
                else:
                    display_text += "\n\n🎯 Keep going! Every point counts!"
            
            return display_text
            
        except Exception as e:
            log_error(f"Error getting leaderboard: {str(e)}")
            return "Error loading leaderboard. Please try again."
    
    def _get_user_gamification_profile(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get user's gamification profile"""
        try:
            result = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            log_error(f"Error getting gamification profile: {str(e)}")
            return None
    
    def create_or_update_leaderboard_entry(self, leaderboard_id: str, user_id: str, 
                                          user_type: str, points: int, nickname: str = None):
        """Create or update a user's leaderboard entry"""
        try:
            # Check if entry exists
            existing = self.db.table('leaderboard_entries').select('*').eq(
                'leaderboard_id', leaderboard_id
            ).eq('user_id', user_id).eq('user_type', user_type).single().execute()
            
            if existing.data:
                # Update existing entry
                self.db.table('leaderboard_entries').update({
                    'points': points,
                    'nickname': nickname or existing.data.get('nickname', 'Anonymous'),
                    'last_updated': datetime.now(self.sa_tz).isoformat()
                }).eq('id', existing.data['id']).execute()
            else:
                # Create new entry
                self.db.table('leaderboard_entries').insert({
                    'leaderboard_id': leaderboard_id,
                    'user_id': user_id,
                    'user_type': user_type,
                    'nickname': nickname or 'Anonymous',
                    'points': points,
                    'rank': 999999,  # Will be updated by ranking job
                    'trend': 'new',
                    'last_updated': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
            # Trigger ranking update
            self.update_leaderboard_rankings(leaderboard_id)
            
        except Exception as e:
            log_error(f"Error creating/updating leaderboard entry: {str(e)}")


class GamificationService:
    """Main gamification service that coordinates all components"""
    
    def __init__(self, config, supabase_client, whatsapp_service):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize sub-services
        self.badges = BadgeChecker(config, supabase_client, whatsapp_service)
        self.challenges = ChallengeManager(config, supabase_client, whatsapp_service)
        self.leaderboards = LeaderboardService(config, supabase_client, whatsapp_service)
    
    def process_action(self, user_id: str, user_type: str, action: str, value: int = 1):
        """Process a user action and award appropriate points/badges"""
        try:
            points_earned = 0
            
            # Determine points for action
            action_points = {
                'habit_logged': 10,
                'workout_completed': 25,
                'assessment_improved': 50,
                'challenge_joined': 5,
                'streak_bonus': 5  # Multiplied by streak days
            }
            
            if action in action_points:
                points_earned = action_points[action] * value
                
                # Add points to user
                self._add_points(user_id, user_type, points_earned, f"Action: {action}")
                
                # Update leaderboards
                self._update_user_leaderboards(user_id, user_type)
                
                # Check for new badges
                new_badges = self.badges.check_badges(user_id, user_type)
                
                return {
                    'points_earned': points_earned,
                    'new_badges': new_badges
                }
            
            return {'points_earned': 0, 'new_badges': []}
            
        except Exception as e:
            log_error(f"Error processing gamification action: {str(e)}")
            return {'points_earned': 0, 'new_badges': []}
    
    def _add_points(self, user_id: str, user_type: str, points: int, reason: str):
        """Add points to user's total"""
        try:
            # Add to ledger
            self.db.table('points_ledger').insert({
                'user_id': user_id,
                'user_type': user_type,
                'points': points,
                'reason': reason,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Update profile
            profile = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if profile.data:
                new_total = profile.data['points_total'] + points
                self.db.table('gamification_profiles').update({
                    'points_total': new_total
                }).eq(f'{user_type}_id', user_id).execute()
            else:
                # Create profile if doesn't exist
                self.db.table('gamification_profiles').insert({
                    f'{user_type}_id': user_id,
                    'points_total': points,
                    'is_public': True,
                    'opted_in_global': True,
                    'opted_in_trainer': True
                }).execute()
                
        except Exception as e:
            log_error(f"Error adding points: {str(e)}")
    
    def _update_user_leaderboards(self, user_id: str, user_type: str):
        """Update user's position on all relevant leaderboards"""
        try:
            # Get user's current points
            profile = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if not profile.data:
                return
            
            points = profile.data['points_total']
            nickname = profile.data.get('nickname', 'Anonymous')
            
            # Update global leaderboard if opted in
            if profile.data.get('opted_in_global', True):
                global_board = self.db.table('leaderboards').select('id').eq(
                    'type', 'global'
                ).eq('is_active', True).single().execute()
                
                if global_board.data:
                    self.leaderboards.create_or_update_leaderboard_entry(
                        global_board.data['id'], user_id, user_type, points, nickname
                    )
            
            # Update trainer group leaderboard if client
            if user_type == 'client' and profile.data.get('opted_in_trainer', True):
                # Get client's trainer
                client = self.db.table('clients').select('trainer_id').eq(
                    'id', user_id
                ).single().execute()
                
                if client.data:
                    trainer_board = self.db.table('leaderboards').select('id').eq(
                        'type', 'trainer_group'
                    ).eq('scope', client.data['trainer_id']).eq(
                        'is_active', True
                    ).single().execute()
                    
                    if trainer_board.data:
                        self.leaderboards.create_or_update_leaderboard_entry(
                            trainer_board.data['id'], user_id, user_type, points, nickname
                        )
                        
        except Exception as e:
            log_error(f"Error updating user leaderboards: {str(e)}")
