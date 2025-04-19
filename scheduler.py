#!/usr/bin/env python3
"""
Main script for the Dynamic Scheduler Agent.
Orchestrates the scheduling process by integrating all components.
"""

import argparse
import logging
from datetime import datetime, timedelta
import pytz

from google_api import GoogleAPIClient
from prioritization import PrioritizationEngine
from schedule_optimizer import ScheduleOptimizer
from morning_brief import MorningBriefGenerator
from config import USER_PREFERENCES


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class DynamicScheduler:
    """
    Main scheduler class that orchestrates the entire scheduling process.
    """
    
    def __init__(self, user_preferences=None):
        """
        Initialize the Dynamic Scheduler.
        
        Args:
            user_preferences (dict, optional): User preferences
        """
        self.user_preferences = user_preferences or USER_PREFERENCES
        
        # Initialize components
        logger.info("Initializing Google API client...")
        self.api_client = GoogleAPIClient()
        
        logger.info("Initializing prioritization engine...")
        self.prioritizer = PrioritizationEngine(self.user_preferences)
        
        logger.info("Initializing schedule optimizer...")
        self.optimizer = ScheduleOptimizer(self.user_preferences)
        
        logger.info("Initializing morning brief generator...")
        self.brief_generator = MorningBriefGenerator(self.user_preferences)
    
    def run(self, target_date=None, days_ahead=1, send_brief=True):
        """
        Run the scheduling process for the target date.
        
        Args:
            target_date (datetime.date, optional): Target date, defaults to tomorrow
            days_ahead (int): Number of days ahead to schedule
            send_brief (bool): Whether to send the morning brief
            
        Returns:
            dict: Generated schedule and brief
        """
        # Set target date to tomorrow if not specified
        if target_date is None:
            target_date = (datetime.now(pytz.UTC) + timedelta(days=days_ahead)).date()
        
        logger.info(f"Running scheduler for {target_date}...")
        
        # Step 1: Retrieve data from Google APIs
        logger.info("Retrieving data from Google APIs...")
        data = self._retrieve_data()
        
        # Step 2: Prioritize items
        logger.info("Prioritizing items...")
        prioritized_items = self.prioritizer.prioritize_items(
            data['events'],
            data['tasks'],
            data['emails']
        )
        
        # Step 3: Generate optimized schedule
        logger.info("Generating optimized schedule...")
        optimized_schedule = self.optimizer.generate_optimized_schedule(
            prioritized_items,
            target_date
        )
        
        # Step 4: Generate morning brief
        logger.info("Generating morning brief...")
        morning_brief = self.brief_generator.generate_morning_brief(
            optimized_schedule,
            prioritized_items
        )
        
        # Step 5: Update calendar (if enabled)
        # This would update the user's calendar with the optimized schedule
        # Disabled for now to avoid making changes without user approval
        
        # Step 6: Send morning brief (if enabled)
        if send_brief:
            logger.info("Sending morning brief...")
            self._send_morning_brief(morning_brief)
        
        return {
            'schedule': optimized_schedule,
            'brief': morning_brief
        }
    
    def _retrieve_data(self):
        """
        Retrieve data from Google APIs.
        
        Returns:
            dict: Retrieved data
        """
        # Get upcoming events (7 days)
        events = self.api_client.get_upcoming_events(days=7)
        logger.info(f"Retrieved {len(events)} calendar events")
        
        # Get tasks
        tasks = self.api_client.get_tasks()
        logger.info(f"Retrieved {len(tasks)} tasks")
        
        # Get important emails
        emails = self.api_client.get_important_emails(max_results=10)
        logger.info(f"Retrieved {len(emails)} important emails")
        
        return {
            'events': events,
            'tasks': tasks,
            'emails': emails
        }
    
    def _send_morning_brief(self, brief):
        """
        Send the morning brief via email.
        
        Args:
            brief (dict): Morning brief content
            
        Returns:
            dict: API response
        """
        # Get user's email (in a real implementation, this would be configured)
        user_email = "user@example.com"
        
        # Send the email
        response = self.api_client.send_email(
            to=user_email,
            subject=brief['subject'],
            message_text=brief['text_content'],
            html_content=brief['html_content']
        )
        
        logger.info(f"Morning brief sent to {user_email}")
        
        return response


def main():
    """
    Main function to run the Dynamic Scheduler Agent.
    """
    parser = argparse.ArgumentParser(description='Dynamic Scheduler Agent')
    parser.add_argument('--days', type=int, default=1, help='Number of days ahead to schedule')
    parser.add_argument('--no-brief', action='store_true', help='Do not send morning brief')
    args = parser.parse_args()
    
    try:
        # Initialize and run the scheduler
        scheduler = DynamicScheduler()
        result = scheduler.run(days_ahead=args.days, send_brief=not args.no_brief)
        
        logger.info("Scheduler completed successfully")
        
        # Print summary
        print("\nSchedule Summary:")
        print(f"Date: {result['schedule']['date']}")
        print(f"Work Location: {result['schedule']['work_location']}")
        print(f"Total Blocks: {len(result['schedule']['blocks'])}")
        print(f"Deep Work Minutes: {result['schedule']['metrics'].get('deep_work_minutes', 0)}")
        print(f"North Star Alignment: {result['schedule']['metrics'].get('north_star_alignment', 0):.0f}%")
        print(f"Balance Score: {result['schedule']['metrics'].get('balance_score', 0):.0f}%")
        
        if result['schedule']['reschedule_candidates']:
            print(f"\nReschedule Candidates: {len(result['schedule']['reschedule_candidates'])}")
            for candidate in result['schedule']['reschedule_candidates']:
                print(f"- {candidate['title']} at {candidate['start'].strftime('%I:%M %p')}")
        
    except Exception as e:
        logger.error(f"Error running scheduler: {e}", exc_info=True)
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
