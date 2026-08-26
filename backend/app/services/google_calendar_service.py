"""Google Calendar API integration for the authenticated user's primary calendar."""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.models.calendar import CalendarEvent
from app.models.user import User


CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarConfigurationError(RuntimeError):
    """Raised when Calendar OAuth has not been configured on the server."""


class GoogleCalendarService:
    def _credentials(self, user: User) -> Credentials:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret or not user.google_refresh_token:
            raise GoogleCalendarConfigurationError(
                "Google Calendar is not connected. Configure OAuth and connect Google Calendar first."
            )

        credentials = Credentials(
            token=None,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[CALENDAR_SCOPE],
        )
        credentials.refresh(Request())
        return credentials

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict:
        return await asyncio.to_thread(self._request_sync, method, url, **kwargs)

    def _request_sync(self, method: str, url: str, **kwargs: Any) -> dict:
        response = requests.request(method, url, timeout=30, **kwargs)
        if not response.ok:
            raise RuntimeError(f"Google Calendar API returned {response.status_code}: {response.text[:500]}")
        return response.json() if response.content else {}

    @staticmethod
    def _headers(credentials: Credentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}

    @staticmethod
    def _google_datetime(value: datetime | None) -> str | None:
        if not value:
            return None
        aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _event_body(event_data: dict) -> dict:
        body = {
            "summary": event_data.get("title") or "EduAI event",
            "description": event_data.get("description") or "",
            "location": event_data.get("location") or "",
        }
        start = event_data.get("start_time") or event_data.get("start")
        end = event_data.get("end_time") or event_data.get("end")
        if event_data.get("is_all_day"):
            body["start"] = {"date": str(start)[:10]}
            body["end"] = {"date": str(end)[:10]}
        else:
            body["start"] = {"dateTime": GoogleCalendarService._google_datetime(start), "timeZone": "UTC"}
            body["end"] = {"dateTime": GoogleCalendarService._google_datetime(end), "timeZone": "UTC"}
        return body

    async def create_google_event(self, user: User, event_data: dict) -> dict:
        credentials = self._credentials(user)
        return await self._request(
            "POST",
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers=self._headers(credentials),
            json=self._event_body(event_data),
        )

    async def sync_events_from_google(self, user: User) -> int:
        credentials = self._credentials(user)
        data = await self._request(
            "GET",
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            headers=self._headers(credentials),
            params={"singleEvents": "true", "showDeleted": "false", "maxResults": 2500},
        )
        imported = 0
        for item in data.get("items", []):
            start_data, end_data = item.get("start", {}), item.get("end", {})
            start = start_data.get("dateTime") or start_data.get("date")
            end = end_data.get("dateTime") or end_data.get("date")
            if not start or not end or not item.get("id"):
                continue
            existing = await CalendarEvent.find_one(CalendarEvent.google_event_id == item["id"])
            if existing:
                continue
            def parse(value: str) -> datetime:
                if len(value) == 10:
                    return datetime.fromisoformat(value)
                return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
            event = CalendarEvent(
                title=item.get("summary") or "Google Calendar event",
                description=item.get("description"),
                location=item.get("location"),
                start_time=parse(start), end_time=parse(end),
                event_type="meeting", teacher_name=user.name,
                google_event_id=item["id"], google_calendar_id="primary",
            )
            await event.assign_id()
            await event.insert()
            imported += 1
        return imported

    async def sync_events_to_google(self, user: User, events: list[CalendarEvent]) -> int:
        credentials = self._credentials(user)
        pushed = 0
        for event in events:
            if event.google_event_id:
                continue
            item = await self.create_google_event(user, event.model_dump())
            event.google_event_id = item.get("id")
            event.google_calendar_id = "primary"
            await event.save()
            pushed += 1
        return pushed

    async def sync_bidirectional(self, user: User) -> dict[str, int]:
        imported = await self.sync_events_from_google(user)
        events = await CalendarEvent.find(CalendarEvent.teacher_name == user.name).to_list()
        pushed = await self.sync_events_to_google(user, events)
        user.google_calendar_synced = True
        await user.save()
        return {"imported": imported, "exported": pushed}
