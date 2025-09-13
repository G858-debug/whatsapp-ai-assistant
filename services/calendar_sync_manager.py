from .calendar_service import CalendarService

class CalendarSyncManager:
    def __init__(self, calendar_service):
        self.calendar_service = calendar_service

    def sync_all_trainers(self):
        """
        Sync calendar events for all trainers.
        """
        trainers = self.get_all_trainers()
        for trainer in trainers:
            self.calendar_service.sync_calendar_events(trainer.id)

    def get_all_trainers(self):
        """
        Fetch all trainers from the database.
        """
        # Implement the logic to fetch all trainers
        # This could involve a database query or other data retrieval method
        pass