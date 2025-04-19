"""
Configuration settings for the Dynamic Scheduler Agent.
"""

import os
from datetime import time

# Google API Configuration
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.pickle')

# API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

# User Preferences
USER_PREFERENCES = {
    # Energy patterns throughout the day
    'energy_patterns': {
        'research': {'start_time': time(6, 0), 'end_time': time(8, 0), 'energy_level': 'high'},
        'calls': {'start_time': time(8, 0), 'end_time': time(9, 0), 'energy_level': 'high'},
        'exercise': {'start_time': time(9, 30), 'end_time': time(10, 30), 'energy_level': 'high'},
        'meetings': {'start_time': time(11, 0), 'end_time': time(16, 0), 'energy_level': 'medium'},
        'admin': {'start_time': time(16, 0), 'end_time': time(19, 0), 'energy_level': 'medium'},
        'family': {'start_time': time(19, 0), 'end_time': time(22, 0), 'energy_level': 'low'},
        'learning': {'start_time': time(22, 0), 'end_time': time(0, 0), 'energy_level': 'medium'}
    },
    
    # Work location preferences
    'work_location': {
        0: 'home',  # Monday
        1: 'office',  # Tuesday
        2: 'office',  # Wednesday
        3: 'office',  # Thursday
        4: 'home'  # Friday
    },
    
    # In-person meeting hours (for office days)
    'in_person_meeting_hours': {
        'start_time': time(12, 0),
        'end_time': time(16, 0)
    },
    
    # Protected time blocks
    'protected_blocks': {
        'deep_work': {
            'duration': 60,  # minutes
            'preferred_time': time(7, 0),
            'alternative_time': time(11, 0),
            'protection_level': 'high'
        },
        'physical_wellbeing': {
            'start_time': time(9, 30),
            'end_time': time(10, 30),
            'protection_level': 'highest'
        },
        'family_time': {
            'start_time': time(19, 0),
            'end_time': time(22, 0),
            'protection_level': 'highest'
        },
        'learning_time': {
            'start_time': time(22, 0),
            'end_time': time(0, 0),
            'protection_level': 'medium'
        },
        'research_time': {
            'start_time': time(6, 0),
            'end_time': time(8, 0),
            'protection_level': 'medium'
        }
    },
    
    # Strategic goals
    'goals': {
        'north_star': 'Generate 10 RAIN ventures AI impact sessions and 5 Launch Labs projects generating $250K',
        'secondary': [
            'Establish RAIN ventures as a leading AI-first technology venture studio',
            'Secure speaking engagements',
            'Refine core proposition',
            'Align team around growth'
        ]
    },
    
    # Meeting preferences
    'meeting_preferences': {
        'max_meetings_per_day': 5,
        'team_meetings_per_day': 2,
        'client_partner_meetings_per_day': 3,
        'preferred_meeting_duration': 30,  # minutes
        'buffer_between_meetings': 15  # minutes
    },
    
    # Email settings
    'email': {
        'morning_brief_time': time(6, 0),
        'morning_brief_subject': 'Your Daily Schedule: {date}'
    }
}

# Protection level override conditions
PROTECTION_OVERRIDE_CONDITIONS = {
    'highest': {'quadrant': ['urgent_important'], 'min_score': 95},
    'high': {'quadrant': ['urgent_important'], 'min_score': 90},
    'medium': {'quadrant': ['urgent_important', 'important'], 'min_score': 80},
    'low': {'quadrant': ['urgent_important', 'important', 'urgent'], 'min_score': 60}
}

# Email templates
EMAIL_TEMPLATES = {
    'clarification_request': """
Subject: Agenda Clarification for {meeting_title}

Hi {organizer},

I noticed our upcoming meeting on {date} doesn't have a clear agenda/expected outcomes. 
Could you share what we'll be covering and what decisions need to be made?

This will help me prepare appropriately and ensure we make the most of our time together.

Thanks,
{user_name}
""",
    'delegation_suggestion': """
Subject: Regarding {meeting_title}

Hi {organizer},

I believe {delegate_name} would be better positioned to represent our interests in the 
upcoming {meeting_title} on {date} given their expertise in this area.

I've briefed them on the context, and they're prepared to attend. Please let me know if 
you have any concerns with this arrangement.

Best regards,
{user_name}
""",
    'reschedule_request': """
Subject: Rescheduling Request for {meeting_title}

Hi {organizer},

I have a conflict with our scheduled meeting on {date}. Would it be possible to 
reschedule to one of these alternative times?

- {option_1}
- {option_2}
- {option_3}

These times would allow me to give this meeting my full attention.

Thanks for your understanding,
{user_name}
"""
}

# Calendar color coding for protected blocks
CALENDAR_COLORS = {
    'deep_work': '10',  # Purple
    'physical_wellbeing': '2',  # Green
    'family_time': '9',  # Blue
    'learning_time': '6',  # Orange
    'research_time': '5'  # Yellow
}
