"""
Profile Viewer Service
Displays user profile in a step-by-step interactive format using WhatsApp List Messages
Mimics the onboarding flow structure for consistent UX
"""
from typing import Dict, Optional
from utils.logger import log_info, log_error


class ProfileViewer:
    """Interactive profile viewer using WhatsApp List Messages"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
    
    def show_profile_menu(self, phone: str, role: str, user_id: str) -> Dict:
        """
        Show main profile menu with sections to view
        
        Args:
            phone: User's phone number
            role: 'trainer' or 'client'
            user_id: User's UUID (trainer_id or client_id)
        
        Returns:
            Dict with success status and response
        """
        try:
            log_info(f"Showing profile menu for {phone} ({role})")
            
            # Get profile data (pass phone for fallback)
            profile_data = self._get_profile_data(role, user_id, phone)
            
            if not profile_data:
                return {
                    'success': False,
                    'response': "❌ I couldn't find your profile information.",
                    'handler': 'profile_viewer_not_found'
                }
            
            # Build menu message
            if role == 'trainer':
                menu_msg = self._build_trainer_menu_message(profile_data)
                sections = self._build_trainer_menu_sections()
            else:
                menu_msg = self._build_client_menu_message(profile_data)
                sections = self._build_client_menu_sections()
            
            # Send list message
            self.whatsapp.send_list_message(
                phone=phone,
                body=menu_msg,
                button_text="View Sections",
                sections=sections
            )
            
            return {
                'success': True,
                'response': menu_msg,
                'handler': 'profile_viewer_menu'
            }
            
        except Exception as e:
            log_error(f"Error showing profile menu: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I couldn't load your profile menu.",
                'handler': 'profile_viewer_error'
            }
    
    def show_profile_section(self, phone: str, role: str, user_id: str, section_id: str) -> Dict:
        """
        Show specific profile section with data
        
        Args:
            phone: User's phone number
            role: 'trainer' or 'client'
            user_id: User's UUID
            section_id: Section to display (e.g., 'basic_info', 'business_details')
        
        Returns:
            Dict with success status and response
        """
        try:
            log_info(f"Showing profile section '{section_id}' for {phone} ({role})")
            
            # Get profile data (pass phone for fallback)
            profile_data = self._get_profile_data(role, user_id, phone)
            
            if not profile_data:
                return {
                    'success': False,
                    'response': "❌ I couldn't find your profile information.",
                    'handler': 'profile_viewer_section_not_found'
                }
            
            # Build section message
            if role == 'trainer':
                section_msg = self._build_trainer_section(section_id, profile_data)
            else:
                section_msg = self._build_client_section(section_id, profile_data)
            
            if not section_msg:
                return {
                    'success': False,
                    'response': f"❌ Unknown section: {section_id}",
                    'handler': 'profile_viewer_unknown_section'
                }
            
            # Add navigation buttons
            buttons = [
                {'id': '/view-profile', 'title': '📋 Back to Menu'}
            ]
            
            self.whatsapp.send_button_message(phone, section_msg, buttons)
            
            return {
                'success': True,
                'response': section_msg,
                'handler': 'profile_viewer_section'
            }
            
        except Exception as e:
            log_error(f"Error showing profile section: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I couldn't load that section.",
                'handler': 'profile_viewer_section_error'
            }
    
    def _get_profile_data(self, role: str, user_id: str, phone: str = None) -> Optional[Dict]:
        """
        Get profile data from database
        
        Args:
            role: 'trainer' or 'client'
            user_id: Custom ID from users.trainer_id or users.client_id (e.g., TR_ASRA_111)
        
        Returns:
            Profile data dict or None
        """
        try:
            from utils.logger import log_info
            
            table = 'trainers' if role == 'trainer' else 'clients'
            # Both users and trainers/clients tables have trainer_id/client_id as custom IDs
            # users.trainer_id (e.g., TR_ASRA_111) should match trainers.trainer_id
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            if result.data:
                return result.data[0]
            
            
            # Fallback: Try to find by phone number (for legacy data or mismatched IDs)
            if phone:
                phone_column = 'whatsapp'  # Both trainers and clients use 'whatsapp' column
                
                # Try with original phone format (with +)
                fallback_result = self.db.table(table).select('*').eq(phone_column, phone).execute()
                
                if fallback_result.data:
                    return fallback_result.data[0]
                
                # Try without + prefix
                clean_phone = phone.replace('+', '')
                fallback_result2 = self.db.table(table).select('*').eq(phone_column, clean_phone).execute()
                
                if fallback_result2.data:
                    return fallback_result2.data[0]
            
            log_error(f"[ProfileViewer._get_profile_data] DATA INTEGRITY ISSUE: users.{id_column}={user_id} doesn't exist in {table}.{id_column}")
            log_error(f"[ProfileViewer._get_profile_data] Phone fallback also failed. Profile not found.")
            
            return None
            
        except Exception as e:
            log_error(f"[ProfileViewer._get_profile_data] Error: {str(e)}")
            import traceback
            log_error(f"[ProfileViewer._get_profile_data] Traceback: {traceback.format_exc()}")
            return None
    
    # ==================== TRAINER MENU ====================
    
    def _build_trainer_menu_message(self, data: Dict) -> str:
        """Build trainer profile menu message"""
        name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or data.get('name', 'N/A')
        
        return (
            f"👤 *Your Trainer Profile*\n\n"
            f"*Name:* {name}\n"
            f"*Email:* {data.get('email', 'N/A')}\n\n"
            f"📋 Select a section below to view details:\n\n"
        )
    
    def _build_trainer_menu_sections(self) -> list:
        """Build trainer menu sections for list message"""
        return [
            {
                "title": "Profile Sections",
                "rows": [
                    {
                        "id": "view_basic_info",
                        "title": "📋 Basic Information",
                        "description": "Name, email, location, birthday"
                    },
                    {
                        "id": "view_business_details",
                        "title": "💼 Business Details",
                        "description": "Specializations, experience, pricing"
                    },
                    {
                        "id": "view_availability",
                        "title": "📅 Weekly Availability",
                        "description": "Your schedule for each day"
                    },
                    {
                        "id": "view_services",
                        "title": "🎯 Services & Preferences",
                        "description": "Services offered, subscription plan"
                    }
                ]
            }
        ]
    
    # ==================== CLIENT MENU ====================
    
    def _build_client_menu_message(self, data: Dict) -> str:
        """Build client profile menu message"""
        name = data.get('name', 'N/A')
        
        return (
            f"👤 *Your Client Profile*\n\n"
            f"*Name:* {name}\n"
            f"*Email:* {data.get('email', 'N/A')}\n\n"
            f"📋 Select a section below to view details:\n\n"
        )
    
    def _build_client_menu_sections(self) -> list:
        """Build client menu sections for list message"""
        return [
            {
                "title": "Profile Sections",
                "rows": [
                    {
                        "id": "view_basic_info",
                        "title": "📋 Basic Information",
                        "description": "Name, email, contact details"
                    },
                    {
                        "id": "view_fitness_goals",
                        "title": "🎯 Fitness Goals",
                        "description": "Your fitness objectives"
                    },
                    {
                        "id": "view_health_info",
                        "title": "💪 Health & Experience",
                        "description": "Experience level, health conditions"
                    },
                    {
                        "id": "view_preferences",
                        "title": "⚙️ Preferences",
                        "description": "Availability, training preferences"
                    }
                ]
            }
        ]
    
    # ==================== TRAINER SECTIONS ====================
    
    def _build_trainer_section(self, section_id: str, data: Dict) -> Optional[str]:
        """Build trainer section content"""
        # Handle both 'view_basic_info' and 'basic_info' formats
        if section_id in ['view_basic_info', 'basic_info']:
            return self._build_trainer_basic_info(data)
        elif section_id in ['view_business_details', 'business_details']:
            return self._build_trainer_business_details(data)
        elif section_id in ['view_availability', 'availability']:
            return self._build_trainer_availability(data)
        elif section_id in ['view_services', 'services']:
            return self._build_trainer_services(data)
        return None
    
    def _build_trainer_basic_info(self, data: Dict) -> str:
        """Build trainer basic info section"""
        name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or data.get('name', 'N/A')
        
        msg = (
            f"📋 *Basic Information*\n\n"
            f"*Full Name:* {name}\n"
            f"*Email:* {data.get('email', 'N/A')}\n"
            f"*Phone:* {data.get('whatsapp', 'N/A')}\n"
            f"*Location:* {data.get('city', 'N/A')}\n"
        )
        
        if data.get('sex'):
            msg += f"*Gender:* {data['sex']}\n"
        
        if data.get('birthdate'):
            msg += f"*Birthday:* {data['birthdate']}\n"
        
        return msg
    
    def _build_trainer_business_details(self, data: Dict) -> str:
        """Build trainer business details section"""
        msg = f"💼 *Business Details*\n\n"
        
        if data.get('business_name'):
            msg += f"*Business Name:* {data['business_name']}\n"
        
        if data.get('specialization'):
            spec = self._format_list_value(data['specialization'])
            if spec:
                msg += f"*Specializations:* {spec}\n"
        
        if data.get('experience_years'):
            msg += f"*Experience:* {data['experience_years']}\n"
        
        if data.get('pricing_per_session'):
            msg += f"*Price per Session:* R{data['pricing_per_session']}\n"
        
        if not any([data.get('business_name'), data.get('specialization'), 
                   data.get('experience_years'), data.get('pricing_per_session')]):
            msg += "_No business details set_\n"
        
        return msg
    
    def _build_trainer_availability(self, data: Dict) -> str:
        """Build trainer availability section"""
        msg = f"📅 *Weekly Availability*\n\n"
        
        # Check for working_hours JSONB structure (new format)
        working_hours = data.get('working_hours')
        
        if working_hours and isinstance(working_hours, dict):
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            for day in days:
                day_schedule = working_hours.get(day, {})
                preset = day_schedule.get('preset', 'not_available')
                
                day_name = day.capitalize()
                
                if preset == 'not_available':
                    msg += f"*{day_name}:* ❌ Not available\n"
                elif preset == 'morning':
                    msg += f"*{day_name}:* 🌅 Morning (6am-12pm)\n"
                elif preset == 'evening':
                    msg += f"*{day_name}:* 🌆 Evening (5pm-9pm)\n"
                elif preset == 'business':
                    msg += f"*{day_name}:* 💼 Business hours (9am-5pm)\n"
                elif preset == 'full_day':
                    msg += f"*{day_name}:* ⏰ Full day (6am-9pm)\n"
                elif preset == 'custom':
                    hours = day_schedule.get('hours', [])
                    if hours:
                        msg += f"*{day_name}:* ⚙️ Custom ({len(hours)} slots)\n"
                    else:
                        msg += f"*{day_name}:* ⚙️ Custom\n"
        else:
            # Fallback to old format
            if data.get('available_days'):
                days = self._format_list_value(data['available_days'])
                msg += f"*Available Days:* {days}\n"
            
            if data.get('preferred_time_slots'):
                msg += f"*Preferred Times:* {data['preferred_time_slots']}\n"
            
            if not data.get('available_days') and not data.get('preferred_time_slots'):
                msg += "_No availability set_\n"
        
        return msg
    
    def _build_trainer_services(self, data: Dict) -> str:
        """Build trainer services section"""
        msg = f"🎯 *Services & Preferences*\n\n"
        
        if data.get('services_offered'):
            services = self._format_list_value(data['services_offered'])
            if services:
                msg += f"*Services Offered:*\n{services}\n\n"
        
        if data.get('subscription_plan'):
            plan = data['subscription_plan'].replace('_', ' ').title()
            msg += f"*Subscription Plan:* {plan}\n"
        
        if data.get('pricing_flexibility'):
            pricing = self._format_list_value(data['pricing_flexibility'])
            if pricing:
                msg += f"*Pricing Options:* {pricing}\n"
        
        if data.get('additional_notes'):
            msg += f"\n*Additional Notes:*\n{data['additional_notes']}\n"
        
        if not any([data.get('services_offered'), data.get('subscription_plan'), 
                   data.get('pricing_flexibility'), data.get('additional_notes')]):
            msg += "_No services or preferences set_\n"
        
        return msg
    
    # ==================== CLIENT SECTIONS ====================
    
    def _build_client_section(self, section_id: str, data: Dict) -> Optional[str]:
        """Build client section content"""
        # Handle both 'view_basic_info' and 'basic_info' formats
        if section_id in ['view_basic_info', 'basic_info']:
            return self._build_client_basic_info(data)
        elif section_id in ['view_fitness_goals', 'fitness_goals']:
            return self._build_client_fitness_goals(data)
        elif section_id in ['view_health_info', 'health_info']:
            return self._build_client_health_info(data)
        elif section_id in ['view_preferences', 'preferences']:
            return self._build_client_preferences(data)
        return None
    
    def _build_client_basic_info(self, data: Dict) -> str:
        """Build client basic info section"""
        msg = (
            f"📋 *Basic Information*\n\n"
            f"*Name:* {data.get('name', 'N/A')}\n"
            f"*Email:* {data.get('email', 'N/A')}\n"
            f"*Phone:* {data.get('whatsapp', 'N/A')}\n"
        )
        
        return msg
    
    def _build_client_fitness_goals(self, data: Dict) -> str:
        """Build client fitness goals section"""
        msg = f"🎯 *Fitness Goals*\n\n"
        
        if data.get('fitness_goals'):
            goals = self._format_list_value(data['fitness_goals'])
            if goals:
                msg += f"{goals}\n"
        else:
            msg += "_No fitness goals set_\n"
        
        return msg
    
    def _build_client_health_info(self, data: Dict) -> str:
        """Build client health info section"""
        msg = f"💪 *Health & Experience*\n\n"
        
        if data.get('experience_level'):
            msg += f"*Experience Level:* {data['experience_level']}\n"
        
        if data.get('health_conditions'):
            msg += f"*Health Conditions:* {data['health_conditions']}\n"
        
        if not data.get('experience_level') and not data.get('health_conditions'):
            msg += "_No health information set_\n"
        
        return msg
    
    def _build_client_preferences(self, data: Dict) -> str:
        """Build client preferences section"""
        msg = f"⚙️ *Preferences*\n\n"
        
        if data.get('availability'):
            avail = self._format_list_value(data['availability'])
            if avail:
                msg += f"*Availability:* {avail}\n"
        
        if data.get('preferred_training_times'):
            training = self._format_list_value(data['preferred_training_times'])
            if training:
                msg += f"*Preferred Training:* {training}\n"
        
        if not data.get('availability') and not data.get('preferred_training_times'):
            msg += "_No preferences set_\n"
        
        return msg
    
    # ==================== HELPERS ====================
    
    def _format_list_value(self, value) -> str:
        """Helper function to format list values consistently"""
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        elif isinstance(value, str) and value.startswith('['):
            # Handle string representation of list
            import ast
            try:
                value_list = ast.literal_eval(value)
                if isinstance(value_list, list):
                    return ', '.join(str(v) for v in value_list)
            except:
                pass
        return str(value) if value else ""
