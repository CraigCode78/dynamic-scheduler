"""
Prioritization module for the Dynamic Scheduler Agent.
Implements the prioritization algorithm to score tasks and meetings.
"""

from datetime import datetime, time
import pytz


class PrioritizationEngine:
    """
    Engine for prioritizing tasks and meetings based on importance, urgency,
    energy alignment, and goal alignment.
    """
    
    def __init__(self, user_preferences):
        """
        Initialize the prioritization engine with user preferences.
        
        Args:
            user_preferences (dict): User preferences from config
        """
        self.user_preferences = user_preferences
        self.energy_patterns = user_preferences['energy_patterns']
        self.goals = user_preferences['goals']
    
    def prioritize_items(self, calendar_events, tasks, emails):
        """
        Prioritize all items (calendar events, tasks, emails) based on the prioritization algorithm.
        
        Args:
            calendar_events (list): Calendar events from Google Calendar
            tasks (list): Tasks from Google Tasks
            emails (list): Important emails from Gmail
            
        Returns:
            dict: Prioritized items with scores
        """
        prioritized_items = {
            'events': self._prioritize_events(calendar_events),
            'tasks': self._prioritize_tasks(tasks),
            'emails': self._prioritize_emails(emails)
        }
        
        return prioritized_items
    
    def _prioritize_events(self, events):
        """
        Prioritize calendar events.
        
        Args:
            events (list): Calendar events from Google Calendar
            
        Returns:
            list: Prioritized events with scores
        """
        prioritized_events = []
        
        for event in events:
            # Skip events without start time (all-day events)
            if 'dateTime' not in event.get('start', {}):
                continue
            
            # Extract event details
            start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            
            # Determine if the event is a meeting
            is_meeting = bool(event.get('attendees', []))
            
            # Evaluate meeting if it has attendees
            if is_meeting:
                meeting_score = self._evaluate_meeting(event)
                
                # Add meeting evaluation to the event
                event['priority'] = {
                    'score': meeting_score['final_score'],
                    'quadrant': meeting_score['quadrant'],
                    'energy_alignment': meeting_score['energy_alignment'],
                    'goal_alignment': meeting_score['goal_alignment'],
                    'reschedule_candidate': meeting_score['reschedule_candidate']
                }
            else:
                # For non-meeting events, calculate priority based on event properties
                is_important = 'important' in event.get('description', '').lower() or '[important]' in event.get('summary', '').lower()
                is_urgent = 'urgent' in event.get('description', '').lower() or '[urgent]' in event.get('summary', '').lower()
                
                priority = self._calculate_priority(
                    is_important=is_important,
                    is_urgent=is_urgent,
                    start_time=start_time.time(),
                    description=event.get('description', '')
                )
                
                event['priority'] = priority
            
            prioritized_events.append(event)
        
        # Sort events by priority score (descending)
        prioritized_events.sort(key=lambda x: x['priority']['score'], reverse=True)
        
        return prioritized_events
    
    def _prioritize_tasks(self, tasks):
        """
        Prioritize tasks.
        
        Args:
            tasks (list): Tasks from Google Tasks
            
        Returns:
            list: Prioritized tasks with scores
        """
        prioritized_tasks = []
        
        for task in tasks:
            # Skip completed tasks
            if task.get('status') == 'completed':
                continue
            
            # Extract task details
            title = task.get('title', '')
            notes = task.get('notes', '')
            due = task.get('due')
            
            # Determine importance and urgency
            is_important = 'important' in notes.lower() or '[important]' in title.lower()
            is_urgent = 'urgent' in notes.lower() or '[urgent]' in title.lower()
            
            # If due date is today or earlier, consider it urgent
            if due:
                due_date = datetime.fromisoformat(due.replace('Z', '+00:00')).date()
                today = datetime.now(pytz.UTC).date()
                if due_date <= today:
                    is_urgent = True
            
            # Calculate priority
            priority = self._calculate_priority(
                is_important=is_important,
                is_urgent=is_urgent,
                start_time=None,  # Tasks don't have a specific time
                description=notes
            )
            
            task['priority'] = priority
            prioritized_tasks.append(task)
        
        # Sort tasks by priority score (descending)
        prioritized_tasks.sort(key=lambda x: x['priority']['score'], reverse=True)
        
        return prioritized_tasks
    
    def _prioritize_emails(self, emails):
        """
        Prioritize emails.
        
        Args:
            emails (list): Important emails from Gmail
            
        Returns:
            list: Prioritized emails with scores
        """
        prioritized_emails = []
        
        for email in emails:
            # Extract email details
            headers = {header['name']: header['value'] for header in email.get('payload', {}).get('headers', [])}
            subject = headers.get('Subject', '')
            
            # Determine importance and urgency
            is_important = 'important' in subject.lower() or email.get('labelIds', []).count('IMPORTANT') > 0
            is_urgent = 'urgent' in subject.lower() or 'asap' in subject.lower()
            
            # Calculate priority
            priority = self._calculate_priority(
                is_important=is_important,
                is_urgent=is_urgent,
                start_time=None,  # Emails don't have a specific time
                description=subject
            )
            
            email['priority'] = priority
            prioritized_emails.append(email)
        
        # Sort emails by priority score (descending)
        prioritized_emails.sort(key=lambda x: x['priority']['score'], reverse=True)
        
        return prioritized_emails
    
    def _calculate_priority(self, is_important, is_urgent, start_time=None, description=''):
        """
        Calculate priority score for an item based on quadrant, energy alignment, and goal alignment.
        
        Args:
            is_important (bool): Whether the item is important
            is_urgent (bool): Whether the item is urgent
            start_time (time, optional): Start time of the item
            description (str): Description or content of the item
            
        Returns:
            dict: Priority information including score and quadrant
        """
        # Determine quadrant
        if is_urgent and is_important:
            quadrant = 'urgent_important'
            quadrant_score = 95  # Urgent + Important
        elif is_important and not is_urgent:
            quadrant = 'important'
            quadrant_score = 80  # Important, Not Urgent
        elif is_urgent and not is_important:
            quadrant = 'urgent'
            quadrant_score = 60  # Urgent, Not Important
        else:
            quadrant = 'neither'
            quadrant_score = 30  # Neither Urgent nor Important
        
        # Calculate energy alignment
        energy_alignment = self._calculate_energy_alignment(start_time) if start_time else 50
        
        # Calculate goal alignment
        goal_alignment = self._calculate_goal_alignment(description)
        
        # Calculate final priority score
        final_score = (0.5 * quadrant_score) + (0.3 * energy_alignment) + (0.2 * goal_alignment)
        
        return {
            'score': final_score,
            'quadrant': quadrant,
            'energy_alignment': energy_alignment,
            'goal_alignment': goal_alignment
        }
    
    def _calculate_energy_alignment(self, item_time):
        """
        Calculate how well an item aligns with the user's energy patterns.
        
        Args:
            item_time (time): Time of the item
            
        Returns:
            float: Energy alignment score (0-100)
        """
        if not item_time:
            return 50  # Default score for items without a specific time
        
        # Find which energy pattern the item falls into
        for pattern_name, pattern in self.energy_patterns.items():
            start = pattern['start_time']
            end = pattern['end_time']
            
            # Handle patterns that cross midnight
            if end < start:
                if (item_time >= start) or (item_time < end):
                    energy_level = pattern['energy_level']
                    break
            else:
                if start <= item_time < end:
                    energy_level = pattern['energy_level']
                    break
        else:
            # Default if no pattern matches
            energy_level = 'medium'
        
        # Convert energy level to score
        energy_scores = {
            'high': 100,
            'medium': 75,
            'low': 50
        }
        
        return energy_scores.get(energy_level, 50)
    
    def _calculate_goal_alignment(self, description):
        """
        Calculate how well an item aligns with the user's strategic goals.
        
        Args:
            description (str): Description or content of the item
            
        Returns:
            float: Goal alignment score (0-100)
        """
        description = description.lower()
        
        # Check alignment with North Star goal
        north_star = self.goals['north_star'].lower()
        if any(keyword in description for keyword in ['rain ventures', 'ai impact', 'launch labs']):
            return 90  # Direct contribution to North Star goal
        
        # Check alignment with secondary goals
        for secondary_goal in self.goals['secondary']:
            if any(keyword in description for keyword in secondary_goal.lower().split()):
                return 70  # Contribution to secondary focus areas
        
        # Default score for items with minimal goal alignment
        return 30
    
    def _evaluate_meeting(self, event):
        """
        Evaluate a meeting based on agenda, outcomes, necessity, and strategic alignment.
        
        Args:
            event (dict): Calendar event representing a meeting
            
        Returns:
            dict: Meeting evaluation including reschedule recommendation
        """
        # Extract meeting details
        summary = event.get('summary', '')
        description = event.get('description', '')
        attendees = event.get('attendees', [])
        start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        
        # Evaluate meeting criteria
        has_agenda = 'agenda' in description.lower() or 'agenda:' in description.lower()
        has_outcomes = 'outcome' in description.lower() or 'objective' in description.lower()
        
        # Determine if user's presence is critical (simplified logic)
        # In a real implementation, this would be more sophisticated
        user_is_organizer = event.get('organizer', {}).get('self', False)
        attendee_count = len(attendees)
        user_necessity = 5 if user_is_organizer else (4 if attendee_count <= 3 else 3)
        
        # Determine strategic alignment
        strategic_alignment = self._calculate_goal_alignment(description + ' ' + summary) / 20  # Convert to 1-5 scale
        
        # Determine if decisions will be made
        decision_authority = 'decision' in description.lower() or 'approve' in description.lower()
        
        # Calculate meeting score
        meeting_score = (
            (has_agenda * 20) +
            (has_outcomes * 20) +
            (user_necessity * 10) +
            (strategic_alignment * 10) +
            (decision_authority * 20)
        )
        
        # Determine if meeting is a reschedule candidate
        reschedule_candidate = meeting_score < 60
        
        # Calculate priority components
        is_important = strategic_alignment >= 3 or decision_authority
        is_urgent = user_is_organizer or 'urgent' in description.lower()
        
        # Get priority details
        priority = self._calculate_priority(
            is_important=is_important,
            is_urgent=is_urgent,
            start_time=start_time.time(),
            description=description
        )
        
        # Add meeting evaluation details
        priority.update({
            'meeting_score': meeting_score,
            'has_agenda': has_agenda,
            'has_outcomes': has_outcomes,
            'user_necessity': user_necessity,
            'strategic_alignment': strategic_alignment,
            'decision_authority': decision_authority,
            'reschedule_candidate': reschedule_candidate
        })
        
        return priority
