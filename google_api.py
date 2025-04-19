"""
Google API integration module for the Dynamic Scheduler Agent.
Handles authentication and interactions with Google Calendar, Tasks, and Gmail.
"""

import os
import pickle
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pytz
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE


class GoogleAPIClient:
    """
    Client for interacting with Google APIs (Calendar, Tasks, Gmail).
    Handles authentication and provides methods for common operations.
    """
    
    def __init__(self):
        """Initialize the Google API client with authentication."""
        self.credentials = self._get_credentials()
        self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
        self.tasks_service = build('tasks', 'v1', credentials=self.credentials)
        self.gmail_service = build('gmail', 'v1', credentials=self.credentials)
    
    def _get_credentials(self):
        """
        Get and refresh user credentials from OAuth 2.0 flow.
        Returns authenticated credentials for API access.
        """
        creds = None
        
        # Load credentials from token file if it exists
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # If credentials don't exist or are invalid, refresh or create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for future runs
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def get_upcoming_events(self, days=7, max_results=100):
        """
        Retrieve upcoming calendar events.
        
        Args:
            days (int): Number of days to look ahead
            max_results (int): Maximum number of events to return
            
        Returns:
            list: Calendar events
        """
        # Calculate time boundaries
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()
        
        # Call the Calendar API
        events_result = self.calendar_service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    
    def create_calendar_event(self, summary, start_time, end_time, location=None, 
                             description=None, attendees=None, color_id=None):
        """
        Create a new calendar event.
        
        Args:
            summary (str): Title of the event
            start_time (str): Start time in RFC3339 format
            end_time (str): End time in RFC3339 format
            location (str, optional): Location of the event
            description (str, optional): Description of the event
            attendees (list, optional): List of attendee email addresses
            color_id (str, optional): Color ID for the event
            
        Returns:
            dict: Created event
        """
        # Create event body
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        # Add optional fields if provided
        if location:
            event['location'] = location
        
        if description:
            event['description'] = description
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        if color_id:
            event['colorId'] = color_id
        
        # Call the Calendar API
        event = self.calendar_service.events().insert(calendarId='primary', body=event).execute()
        return event
    
    def update_calendar_event(self, event_id, **kwargs):
        """
        Update an existing calendar event.
        
        Args:
            event_id (str): ID of the event to update
            **kwargs: Fields to update (summary, start, end, etc.)
            
        Returns:
            dict: Updated event
        """
        # Get the existing event
        event = self.calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update fields
        for key, value in kwargs.items():
            if key in event:
                event[key] = value
        
        # Call the Calendar API
        updated_event = self.calendar_service.events().update(
            calendarId='primary', 
            eventId=event_id, 
            body=event
        ).execute()
        
        return updated_event
    
    def delete_calendar_event(self, event_id):
        """
        Delete a calendar event.
        
        Args:
            event_id (str): ID of the event to delete
            
        Returns:
            dict: API response
        """
        return self.calendar_service.events().delete(calendarId='primary', eventId=event_id).execute()
    
    def get_tasks(self, tasklist_id='@default', max_results=100):
        """
        Retrieve tasks from a specified task list.
        
        Args:
            tasklist_id (str): ID of the task list
            max_results (int): Maximum number of tasks to return
            
        Returns:
            list: Tasks
        """
        # Call the Tasks API
        results = self.tasks_service.tasks().list(
            tasklist=tasklist_id,
            maxResults=max_results,
            showCompleted=True
        ).execute()
        
        tasks = results.get('items', [])
        return tasks
    
    def create_task(self, title, notes=None, due=None, tasklist_id='@default'):
        """
        Create a new task in the specified task list.
        
        Args:
            title (str): Title of the task
            notes (str, optional): Notes for the task
            due (str, optional): Due date in RFC3339 format
            tasklist_id (str): ID of the task list
            
        Returns:
            dict: Created task
        """
        # Create task body
        task = {
            'title': title
        }
        
        if notes:
            task['notes'] = notes
        
        if due:
            task['due'] = due
        
        # Call the Tasks API
        result = self.tasks_service.tasks().insert(tasklist=tasklist_id, body=task).execute()
        return result
    
    def get_important_emails(self, max_results=10):
        """
        Retrieve important emails that might require action.
        
        Args:
            max_results (int): Maximum number of emails to return
            
        Returns:
            list: Important emails
        """
        # Query for important unread emails
        query = "is:important is:unread"
        
        # Call the Gmail API
        results = self.gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        # Get full message details for each message
        emails = []
        for message in messages:
            msg = self.gmail_service.users().messages().get(
                userId='me', 
                id=message['id']
            ).execute()
            emails.append(msg)
        
        return emails
    
    def send_email(self, to, subject, message_text, from_email=None, html_content=None):
        """
        Send an email using the Gmail API.
        
        Args:
            to (str): Recipient email address
            subject (str): Email subject
            message_text (str): Plain text content
            from_email (str, optional): Sender email address
            html_content (str, optional): HTML content
            
        Returns:
            dict: Sent message
        """
        # Create a MIME message
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['subject'] = subject
        
        if from_email:
            message['from'] = from_email
        
        # Add text part
        text_part = MIMEText(message_text, 'plain')
        message.attach(text_part)
        
        # Add HTML part if provided
        if html_content:
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Create the message object
        message_object = {
            'raw': raw_message
        }
        
        # Send the message
        sent_message = self.gmail_service.users().messages().send(
            userId='me', 
            body=message_object
        ).execute()
        
        return sent_message
