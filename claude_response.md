<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0719 -->
<!-- Tokens: ~23,982 -->

## ANALYSIS
The task requires implementing client challenge participation features in the gamification system. We need to modify the existing gamification.py file to add challenge participation methods and integrate with habit/workout tracking.

## FILES TO CHANGE

### FILE: services/gamification.py
```python
# Previous content stays the same up until line ~1000, then add:

def join_challenge(self, client_id: str, challenge_id: str) -> Dict:
    """Client joins a challenge"""
    try:
        # Verify challenge exists and is active
        challenge = self.db.table('challenges').select('*').eq(
            'id', challenge_id
        ).eq('is_active', True).single().execute()
        
        if not challenge.data:
            return {
                'success': False,
                'error': 'Challenge not found or inactive'
            }
        
        # Check if already participating
        existing = self.db.table('challenge_participants').select('*').eq(
            'challenge_id', challenge_id
        ).eq('user_id', client_id).eq('user_type', 'client').single().execute()
        
        if existing.data:
            return {
                'success': False, 
                'error': 'Already participating in this challenge'
            }
        
        # Check max participants if set
        if challenge.data.get('max_participants'):
            participant_count = len(self.db.table('challenge_participants').select(
                'id'
            ).eq('challenge_id', challenge_id).execute().data or [])
            
            if participant_count >= challenge.data['max_participants']:
                return {
                    'success': False,
                    'error': 'Challenge is full'
                }
        
        # Join challenge
        result = self.db.table('challenge_participants').insert({
            'challenge_id': challenge_id,
            'user_id': client_id,
            'user_type': 'client',
            'status': 'active',
            'joined_at': datetime.now(self.sa_tz).isoformat()
        }).execute()
        
        if result.data:
            # Award points for joining
            self.process_action(client_id, 'client', 'challenge_joined')
            
            return {
                'success': True,
                'message': f"""🎯 *Challenge Joined!*

You've joined: {challenge.data['name']}

Target: {challenge.data['target_value']} {challenge.data['challenge_rules'].get('unit', '')}
Duration: {challenge.data['challenge_rules'].get('duration_days', 0)} days
Reward: {challenge.data['points_reward']} points

Let's crush this! 💪"""
            }
        
        return {
            'success': False,
            'error': 'Failed to join challenge'
        }
        
    except Exception as e:
        log_error(f"Error joining challenge: {str(e)}")
        return {'success': False, 'error': str(e)}

def log_challenge_progress(self, client_id: str, action_type: str, value: float) -> Dict:
    """Log progress for active challenges based on actions"""
    try:
        # Get active challenges for client
        active = self.db.table('challenge_participants').select(
            '*, challenges(*)'
        ).eq('user_id', client_id).eq('user_type', 'client').eq(
            'status', 'active'
        ).execute()
        
        if not active.data:
            return {'success': True, 'message': None}  # No active challenges
        
        progress_updates = []
        notifications = []
        
        for participation in active.data:
            challenge = participation['challenges']
            rules = challenge['challenge_rules']
            
            # Check if action applies to this challenge
            if rules['challenge_type'] == action_type:
                # Log progress
                progress = self.db.table('challenge_progress').insert({
                    'challenge_id': challenge['id'],
                    'participant_id': participation['id'],
                    'value_achieved': value,
                    'logged_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                if progress.data:
                    progress_updates.append(progress.data[0])
                    
                    # Calculate total progress
                    total = sum(p.get('value_achieved', 0) for p in progress_updates)
                    percentage = (total / challenge['target_value']) * 100
                    
                    # Check for milestones
                    if percentage >= 25 and percentage < 50:
                        notifications.append("🎯 25% of your challenge goal reached!")
                    elif percentage >= 50 and percentage < 75:
                        notifications.append("💪 Halfway there! 50% complete!")
                    elif percentage >= 75 and percentage < 100:
                        notifications.append("🔥 Almost there! 75% complete!")
                    elif percentage >= 100:
                        notifications.append("🎉 Challenge goal achieved! Amazing work!")
                        
                        # Award bonus points for completion
                        self.process_action(client_id, 'client', 'challenge_completed')
        
        if notifications:
            return {
                'success': True,
                'message': "\n\n".join(notifications)
            }
        
        return {'success': True, 'message': None}
        
    except Exception as e:
        log_error(f"Error logging challenge progress: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_my_challenges(self, client_id: str) -> Dict:
    """Get client's active challenges with progress"""
    try:
        # Get active challenge participations
        active = self.db.table('challenge_participants').select(
            '*, challenges(*), challenge_progress(*)'
        ).eq('user_id', client_id).eq('user_type', 'client').eq(
            'status', 'active'
        ).execute()
        
        if not active.data:
            return {
                'success': True,
                'message': "You're not in any active challenges.\nJoin one to start earning points! 🎯"
            }
        
        # Format challenges list
        challenges_text = "🏆 *Your Active Challenges*\n\n"
        
        for participation in active.data:
            challenge = participation['challenges']
            progress = participation.get('challenge_progress', [])
            
            # Calculate progress
            total_progress = sum(p.get('value_achieved', 0) for p in progress)
            percentage = min((total_progress / challenge['target_value']) * 100, 100)
            
            # Get participant count and ranking
            all_participants = self.db.table('challenge_participants').select(
                '*, challenge_progress(*)'
            ).eq('challenge_id', challenge['id']).eq('status', 'active').execute()
            
            participant_scores = []
            for p in all_participants.data:
                p_total = sum(prog.get('value_achieved', 0) for prog in p.get('challenge_progress', []))
                participant_scores.append((p['id'], p_total))
            
            # Sort by score and find ranking
            participant_scores.sort(key=lambda x: x[1], reverse=True)
            ranking = next((i + 1 for i, (pid, _) in enumerate(participant_scores) 
                          if pid == participation['id']), len(participant_scores))
            
            # Build progress bar
            progress_bar = "▓" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
            
            challenges_text += f"""*{challenge['name']}*
📊 Progress: {progress_bar} ({percentage:.1f}%)
🎯 Target: {total_progress:.1f}/{challenge['target_value']} {challenge['challenge_rules'].get('unit', '')}
👥 Rank: #{ranking} of {len(participant_scores)}
🏆 Reward: {challenge['points_reward']} points

"""
        
        return {
            'success': True,
            'message': challenges_text
        }
        
    except Exception as e:
        log_error(f"Error getting challenges: {str(e)}")
        return {'success': False, 'error': str(e)}

def calculate_points(self, client_id: str, action: str, value: float = 1.0) -> int:
    """Calculate points for an achievement"""
    try:
        # Base points for different actions
        points_table = {
            'workout_completed': 25,
            'habit_logged': 10,
            'assessment_improved': 50,
            'challenge_milestone': 20,
            'challenge_completed': 100,
            'streak_bonus': 5  # Per day
        }
        
        # Get base points
        base_points = points_table.get(action, 0)
        
        # Apply multipliers based on context
        multiplier = 1.0
        
        # Streak multiplier
        if action in ['workout_completed', 'habit_logged']:
            streak = self._get_current_streak(client_id)
            if streak >= 7:
                multiplier *= 1.5  # 50% bonus for week+ streak
            elif streak >= 3:
                multiplier *= 1.25  # 25% bonus for 3+ day streak
        
        # Value multiplier for certain actions
        if action in ['workout_completed', 'habit_logged']:
            multiplier *= value  # Multiple entries = multiple points
        
        # Calculate final points
        final_points = int(base_points * multiplier)
        
        return final_points
        
    except Exception as e:
        log_error(f"Error calculating points: {str(e)}")
        return 0
```

## MIGRATION: 20250907053853_20250103000002_challenge_progress_tables.sql
```sql
-- Add challenge progress tracking tables
CREATE TABLE IF NOT EXISTS challenge_progress (
    id uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    challenge_id uuid REFERENCES challenges(id) ON DELETE CASCADE,
    participant_id uuid REFERENCES challenge_participants(id) ON DELETE CASCADE,
    value_achieved float NOT NULL DEFAULT 0,
    logged_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_challenge_progress_challenge ON challenge_progress(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_participant ON challenge_progress(participant_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_logged_at ON challenge_progress(logged_at);

-- Add trigger for updated_at
CREATE TRIGGER set_challenge_progress_updated_at
    BEFORE UPDATE ON challenge_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## SUMMARY
Added core challenge participation features:
1. join_challenge() - Handles client joining challenges
2. log_challenge_progress() - Tracks progress from habits/workouts 
3. get_my_challenges() - Lists active challenges with progress
4. calculate_points() - Awards points based on achievements

Created challenge_progress table to track participation metrics. The system now automatically tracks challenge progress when habits or workouts are logged, and sends encouraging messages for milestones reached.

The implementation includes:
- Progress tracking and visualization
- Point calculation with streak multipliers
- Milestone notifications
- Progress bars in challenge status
- Ranking among participants
- Integration with existing habit/workout tracking