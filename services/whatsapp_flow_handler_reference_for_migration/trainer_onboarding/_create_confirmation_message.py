    def _create_confirmation_message(self, trainer_data: Dict) -> str:
        """Create confirmation message for successful registration"""
        return f"""🎉 Welcome to Refiloe, {trainer_data['name']}!

Your trainer profile has been created successfully! Here's what happens next:

✅ **Profile Created**: {trainer_data['specialization']} trainer
✅ **Pricing Set**: R{trainer_data['pricing_per_session']} per session
✅ **Plan Selected**: {trainer_data['subscription_plan'].title()} Plan

📋 **Next Steps**:
1. We'll review your application within 24 hours
2. You'll receive an approval notification
3. Once approved, you can start accepting clients!

💡 **In the meantime**:
- Check your email for a confirmation message
- Review our trainer guidelines
- Set up your availability calendar

Questions? Just reply to this message and I'll help you out!

Welcome to the Refiloe family! 💪"""