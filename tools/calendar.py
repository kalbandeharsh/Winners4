"""
EcoSphere - Calendar Tool
Schedule meetings with human sales agents.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Try to import google calendar, fallback to mock if not available
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    HAS_GOOGLE_CALENDAR = True
except ImportError:
    HAS_GOOGLE_CALENDAR = False


class MeetingScheduler:
    """
    Schedules meetings with human sales agents.
    Supports both Google Calendar integration and mock scheduling.
    """
    
    def __init__(self, use_mock: bool = True):
        """
        Initialize the scheduler.
        
        Args:
            use_mock: If True, use mock scheduling (no real calendar)
        """
        self.use_mock = use_mock or not HAS_GOOGLE_CALENDAR
        self.scheduled_meetings: List[Dict[str, Any]] = []
        
        if not self.use_mock:
            self._init_google_calendar()
        else:
            print("📅 Using mock calendar (no Google Calendar integration)")
    
    def _init_google_calendar(self):
        """Initialize Google Calendar API."""
        # Look for credentials file
        creds_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json")
        if os.path.exists(creds_path):
            creds = Credentials.from_authorized_user_file(creds_path)
            self.service = build("calendar", "v3", credentials=creds)
            print("✅ Google Calendar connected")
        else:
            print("⚠️  No Google Calendar credentials found. Using mock.")
            self.use_mock = True
    
    def schedule_meeting(
        self,
        customer_name: str,
        email: str,
        company: Optional[str] = None,
        topic: str = "Sales Demo",
        context: str = "",
        preferred_time: Optional[str] = None,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Schedule a meeting with a human sales agent.
        
        Args:
            customer_name: Customer's name
            email: Customer's email
            company: Customer's company (optional)
            topic: Meeting topic
            context: Call context/notes
            preferred_time: Preferred time (ISO format or natural language)
            duration_minutes: Meeting duration in minutes
            
        Returns:
            Meeting details including confirmation
        """
        # Parse preferred time or use default
        if preferred_time:
            try:
                start_time = datetime.fromisoformat(preferred_time.replace("Z", "+00:00"))
            except:
                # Default to tomorrow at 10 AM
                start_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            # Default to tomorrow at 10 AM
            start_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        meeting = {
            "customer_name": customer_name,
            "email": email,
            "company": company or "Not specified",
            "topic": topic,
            "context": context,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_minutes": duration_minutes,
            "status": "scheduled",
            "confirmation_id": f"ECO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        if self.use_mock:
            # Mock scheduling
            meeting["calendar_event_id"] = f"mock_event_{len(self.scheduled_meetings) + 1}"
            meeting["meeting_link"] = f"https://ecosphere.zoom.us/j/meeting-{meeting['confirmation_id']}"
        else:
            # Real Google Calendar
            event = self._create_calendar_event(meeting)
            meeting["calendar_event_id"] = event.get("id")
            meeting["meeting_link"] = event.get("hangoutLink", "")
        
        self.scheduled_meetings.append(meeting)
        
        return meeting
    
    def _create_calendar_event(self, meeting: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Google Calendar event."""
        event = {
            "summary": f"EcoSphere Sales: {meeting['customer_name']}",
            "description": f"""
Customer: {meeting['customer_name']}
Email: {meeting['email']}
Company: {meeting['company']}

Context:
{meeting['context']}
            """,
            "start": {
                "dateTime": meeting["start_time"],
                "timeZone": "America/New_York",
            },
            "end": {
                "dateTime": meeting["end_time"],
                "timeZone": "America/New_York",
            },
            "attendees": [
                {"email": meeting["email"]},
                {"email": "sales@ecosphere.ai"}  # Sales team
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }
        
        try:
            event_result = self.service.events().insert(
                calendarId="primary",
                body=event,
                sendUpdates="all"
            ).execute()
            return event_result
        except Exception as e:
            print(f"❌ Calendar error: {e}")
            return {"id": "error", "hangoutLink": ""}
    
    def get_meeting_confirmation(self, meeting: Dict[str, Any]) -> str:
        """Generate a human-readable confirmation message."""
        start = datetime.fromisoformat(meeting["start_time"])
        
        return f"""
📅 Meeting Scheduled!

• Customer: {meeting['customer_name']}
• Email: {meeting['email']}
• Company: {meeting['company']}
• Date: {start.strftime('%A, %B %d, %Y')}
• Time: {start.strftime('%I:%M %p')}
• Duration: {meeting['duration_minutes']} minutes
• Confirmation ID: {meeting['confirmation_id']}

A calendar invite has been sent to {meeting['email']}.
Our sales team will reach out shortly to confirm.
        """.strip()
    
    def get_scheduled_meetings(self) -> List[Dict[str, Any]]:
        """Get all scheduled meetings."""
        return self.scheduled_meetings
    
    def cancel_meeting(self, confirmation_id: str) -> bool:
        """Cancel a scheduled meeting."""
        for meeting in self.scheduled_meetings:
            if meeting["confirmation_id"] == confirmation_id:
                meeting["status"] = "cancelled"
                return True
        return False


# Singleton instance
_scheduler = None

def get_scheduler() -> MeetingScheduler:
    """Get or create the singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MeetingScheduler(use_mock=True)
    return _scheduler


# LangChain tool definition
def create_calendar_tool():
    """Create a LangChain-compatible tool for calendar scheduling."""
    try:
        from langchain_core.tools import tool
        
        @tool
        def schedule_meeting(
            customer_name: str,
            email: str,
            company: str = "",
            topic: str = "Sales Demo",
            context: str = ""
        ) -> str:
            """
            Schedule a meeting with a human sales agent.
            
            Args:
                customer_name: Customer's full name
                email: Customer's email address
                company: Customer's company name (optional)
                topic: Meeting topic (default: Sales Demo)
                context: Any relevant context from the call
            
            Returns:
                Confirmation message with meeting details
            """
            scheduler = get_scheduler()
            meeting = scheduler.schedule_meeting(
                customer_name=customer_name,
                email=email,
                company=company,
                topic=topic,
                context=context
            )
            return scheduler.get_meeting_confirmation(meeting)
        
        return schedule_meeting
    except ImportError:
        # Fallback if langchain not available
        return None


# For testing
if __name__ == "__main__":
    scheduler = get_scheduler()
    
    print("="*50)
    print("Calendar Tool Test")
    print("="*50)
    
    # Test scheduling
    meeting = scheduler.schedule_meeting(
        customer_name="John Smith",
        email="john@example.com",
        company="Acme Corp",
        topic="EcoSphere Enterprise Demo",
        context="Customer interested in unlimited calls and CRM integration"
    )
    
    print(scheduler.get_meeting_confirmation(meeting))
    
    print(f"\nTotal scheduled meetings: {len(scheduler.get_scheduled_meetings())}")
