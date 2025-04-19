"""
Morning brief generation module for the Dynamic Scheduler Agent.
Creates a daily morning brief with schedule overview and key information.
"""

from datetime import datetime
import pytz


class MorningBriefGenerator:
    """
    Generates the morning brief with schedule overview and key information.
    """
    
    def __init__(self, user_preferences=None):
        """
        Initialize the morning brief generator.
        
        Args:
            user_preferences (dict, optional): User preferences
        """
        self.user_preferences = user_preferences
    
    def generate_morning_brief(self, optimized_schedule, prioritized_items):
        """
        Generate the morning brief with schedule overview and key information.
        
        Args:
            optimized_schedule (dict): Optimized schedule
            prioritized_items (dict): Prioritized events, tasks, and emails
            
        Returns:
            dict: Morning brief with text and HTML content
        """
        date = optimized_schedule['date']
        blocks = optimized_schedule['blocks']
        metrics = optimized_schedule['metrics']
        reschedule_candidates = optimized_schedule['reschedule_candidates']
        
        # Generate schedule visualization
        schedule_visualization = self._generate_schedule_visualization(blocks)
        
        # Identify top tasks
        critical_tasks = self._identify_top_tasks(prioritized_items['tasks'], limit=3)
        
        # Generate meeting intelligence
        meeting_intelligence = self._generate_meeting_insights(blocks, reschedule_candidates)
        
        # Gather recent context
        recent_context = self._gather_recent_context(prioritized_items['emails'])
        
        # Create brief content
        brief = {
            'date': date.strftime("%A, %B %d, %Y"),
            'schedule_overview': schedule_visualization,
            'key_metrics': metrics,
            'critical_tasks': critical_tasks,
            'meeting_intelligence': meeting_intelligence,
            'recent_context': recent_context
        }
        
        # Format the brief
        formatted_brief = self._format_morning_brief(brief)
        
        return formatted_brief
    
    def _generate_schedule_visualization(self, blocks):
        """
        Generate a visualization of the day's schedule.
        
        Args:
            blocks (list): Schedule blocks
            
        Returns:
            str: Schedule visualization
        """
        # Sort blocks by start time
        blocks = sorted(blocks, key=lambda x: x['start'])
        
        # Group blocks by hour
        hours = {}
        for block in blocks:
            hour = block['start'].hour
            if hour not in hours:
                hours[hour] = []
            hours[hour].append(block)
        
        # Generate visualization
        visualization = []
        
        for hour in range(6, 24):  # 6 AM to 11 PM
            hour_blocks = hours.get(hour, [])
            
            if hour_blocks:
                # Format hour header
                hour_str = f"{hour:02d}:00" if hour < 12 else f"{hour-12 if hour > 12 else hour}:00 PM"
                visualization.append(f"**{hour_str}**")
                
                # Add blocks for this hour
                for block in hour_blocks:
                    start_time = block['start'].strftime("%I:%M %p")
                    end_time = block['end'].strftime("%I:%M %p")
                    title = block['title']
                    block_type = block['type']
                    
                    # Format based on block type
                    if block_type == 'protected':
                        visualization.append(f"- {start_time} - {end_time}: 🛡️ {title}")
                    elif block_type == 'meeting':
                        # Add indicator for important meetings
                        priority = block.get('priority', {})
                        if priority.get('quadrant') == 'urgent_important':
                            visualization.append(f"- {start_time} - {end_time}: 🔴 {title}")
                        elif priority.get('quadrant') == 'important':
                            visualization.append(f"- {start_time} - {end_time}: 🟠 {title}")
                        else:
                            visualization.append(f"- {start_time} - {end_time}: 📅 {title}")
                    elif block_type == 'task':
                        visualization.append(f"- {start_time} - {end_time}: ✅ {title}")
                    elif block_type == 'email':
                        visualization.append(f"- {start_time} - {end_time}: 📧 {title}")
                    else:
                        visualization.append(f"- {start_time} - {end_time}: {title}")
            else:
                # Empty hour
                hour_str = f"{hour:02d}:00" if hour < 12 else f"{hour-12 if hour > 12 else hour}:00 PM"
                visualization.append(f"**{hour_str}** - *Open*")
        
        return "\n".join(visualization)
    
    def _identify_top_tasks(self, tasks, limit=3):
        """
        Identify the top priority tasks.
        
        Args:
            tasks (list): Prioritized tasks
            limit (int): Maximum number of tasks to return
            
        Returns:
            list: Top priority tasks
        """
        # Sort tasks by priority score
        sorted_tasks = sorted(tasks, key=lambda x: x.get('priority', {}).get('score', 0), reverse=True)
        
        # Get top tasks
        top_tasks = []
        for task in sorted_tasks[:limit]:
            # Estimate time required
            notes = task.get('notes', '')
            title = task.get('title', '')
            
            estimated_time = "30 min"  # Default
            if 'quick' in title.lower() or 'quick' in notes.lower():
                estimated_time = "15 min"
            elif 'long' in title.lower() or 'long' in notes.lower():
                estimated_time = "60 min"
            
            top_tasks.append({
                'title': task.get('title', ''),
                'estimated_time': estimated_time,
                'notes': notes
            })
        
        return top_tasks
    
    def _generate_meeting_insights(self, blocks, reschedule_candidates):
        """
        Generate insights for meetings.
        
        Args:
            blocks (list): Schedule blocks
            reschedule_candidates (list): Meetings that are candidates for rescheduling
            
        Returns:
            dict: Meeting insights
        """
        # Filter for meeting blocks
        meeting_blocks = [block for block in blocks if block['type'] == 'meeting']
        
        # Generate preparation notes
        preparation_notes = []
        for meeting in meeting_blocks:
            priority = meeting.get('priority', {})
            quadrant = priority.get('quadrant', 'neither')
            
            # Only include important meetings
            if quadrant in ['urgent_important', 'important']:
                preparation_notes.append({
                    'title': meeting['title'],
                    'time': meeting['start'].strftime("%I:%M %p"),
                    'notes': self._generate_meeting_prep_notes(meeting)
                })
        
        # Format reschedule candidates
        reschedule_suggestions = []
        for candidate in reschedule_candidates:
            reschedule_suggestions.append({
                'title': candidate['title'],
                'time': candidate['start'].strftime("%I:%M %p"),
                'reasons': candidate['reasons']
            })
        
        # Identify meetings with expected decisions
        decision_meetings = []
        for meeting in meeting_blocks:
            priority = meeting.get('priority', {})
            if priority.get('decision_authority', False):
                decision_meetings.append({
                    'title': meeting['title'],
                    'time': meeting['start'].strftime("%I:%M %p")
                })
        
        return {
            'preparation_notes': preparation_notes,
            'reschedule_suggestions': reschedule_suggestions,
            'decision_meetings': decision_meetings
        }
    
    def _generate_meeting_prep_notes(self, meeting):
        """
        Generate preparation notes for a meeting.
        
        Args:
            meeting (dict): Meeting block
            
        Returns:
            str: Preparation notes
        """
        # In a real implementation, this would analyze the meeting details
        # and generate specific preparation notes
        
        # For now, use a simple template
        notes = []
        
        # Add note about strategic alignment
        priority = meeting.get('priority', {})
        strategic_alignment = priority.get('strategic_alignment', 0)
        
        if strategic_alignment >= 4:
            notes.append("This meeting is highly aligned with your strategic goals.")
        
        # Add note about decision authority
        if priority.get('decision_authority', False):
            notes.append("Decisions are expected to be made in this meeting.")
        
        # Add note about attendees
        attendees_count = meeting.get('attendees', 0)
        if attendees_count > 5:
            notes.append(f"Large meeting with {attendees_count} attendees.")
        
        # Default note if none generated
        if not notes:
            notes.append("Review the agenda and prepare key talking points.")
        
        return "\n".join(notes)
    
    def _gather_recent_context(self, emails):
        """
        Gather recent context from emails.
        
        Args:
            emails (list): Important emails
            
        Returns:
            dict: Recent context
        """
        # Extract important emails requiring response
        important_emails = []
        for email in emails[:5]:  # Limit to top 5
            headers = {header['name']: header['value'] for header in email.get('payload', {}).get('headers', [])}
            subject = headers.get('Subject', '')
            sender = headers.get('From', '')
            
            important_emails.append({
                'subject': subject,
                'sender': sender
            })
        
        # In a real implementation, this would also include:
        # - Follow-ups from yesterday's meetings
        # - Upcoming deadlines
        
        return {
            'important_emails': important_emails,
            'follow_ups': [],  # Placeholder for follow-ups
            'upcoming_deadlines': []  # Placeholder for deadlines
        }
    
    def _format_morning_brief(self, brief):
        """
        Format the morning brief for email delivery.
        
        Args:
            brief (dict): Morning brief content
            
        Returns:
            dict: Formatted brief with text and HTML content
        """
        # Generate text version
        text_content = self._generate_text_brief(brief)
        
        # Generate HTML version
        html_content = self._generate_html_brief(brief)
        
        return {
            'subject': f"Your Daily Schedule: {brief['date']}",
            'text_content': text_content,
            'html_content': html_content
        }
    
    def _generate_text_brief(self, brief):
        """
        Generate the text version of the morning brief.
        
        Args:
            brief (dict): Morning brief content
            
        Returns:
            str: Text content
        """
        sections = []
        
        # Header
        sections.append(f"DAILY SCHEDULE: {brief['date']}")
        sections.append("=" * 50)
        
        # Key Metrics
        metrics = brief['key_metrics']
        sections.append("KEY METRICS")
        sections.append(f"Deep Work Time: {metrics.get('deep_work_minutes', 0)} minutes")
        sections.append(f"North Star Goal Progress: {metrics.get('north_star_alignment', 0):.0f}%")
        sections.append(f"Work-Life Balance: {metrics.get('balance_score', 0):.0f}%")
        sections.append("")
        
        # Critical Tasks
        sections.append("CRITICAL TASKS")
        for i, task in enumerate(brief['critical_tasks'], 1):
            sections.append(f"{i}. {task['title']} ({task['estimated_time']})")
            if task['notes']:
                sections.append(f"   Notes: {task['notes']}")
        sections.append("")
        
        # Meeting Intelligence
        sections.append("MEETING INTELLIGENCE")
        
        # Decision Meetings
        decision_meetings = brief['meeting_intelligence']['decision_meetings']
        if decision_meetings:
            sections.append("Decisions Expected Today:")
            for meeting in decision_meetings:
                sections.append(f"- {meeting['time']}: {meeting['title']}")
            sections.append("")
        
        # Preparation Notes
        prep_notes = brief['meeting_intelligence']['preparation_notes']
        if prep_notes:
            sections.append("Meeting Preparation:")
            for meeting in prep_notes:
                sections.append(f"- {meeting['time']}: {meeting['title']}")
                for note in meeting['notes'].split('\n'):
                    sections.append(f"  * {note}")
            sections.append("")
        
        # Reschedule Suggestions
        reschedule = brief['meeting_intelligence']['reschedule_suggestions']
        if reschedule:
            sections.append("Reschedule Candidates:")
            for meeting in reschedule:
                sections.append(f"- {meeting['time']}: {meeting['title']}")
                for reason in meeting['reasons']:
                    sections.append(f"  * {reason}")
            sections.append("")
        
        # Recent Context
        sections.append("RECENT CONTEXT")
        
        # Important Emails
        important_emails = brief['recent_context']['important_emails']
        if important_emails:
            sections.append("Important Emails:")
            for email in important_emails:
                sections.append(f"- {email['subject']} (From: {email['sender']})")
            sections.append("")
        
        # Schedule Overview
        sections.append("TODAY'S SCHEDULE")
        sections.append(brief['schedule_overview'])
        
        return "\n".join(sections)
    
    def _generate_html_brief(self, brief):
        """
        Generate the HTML version of the morning brief.
        
        Args:
            brief (dict): Morning brief content
            
        Returns:
            str: HTML content
        """
        # This is a simplified HTML template
        # In a real implementation, this would be more sophisticated with better styling
        
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }",
            "h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }",
            "h2 { color: #2980b9; margin-top: 30px; }",
            "h3 { color: #3498db; }",
            ".metrics { display: flex; justify-content: space-between; margin: 20px 0; }",
            ".metric { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; flex: 1; margin: 0 10px; }",
            ".metric h3 { margin: 0; }",
            ".metric p { font-size: 24px; font-weight: bold; margin: 10px 0; }",
            ".task, .meeting, .email { margin-bottom: 15px; padding: 10px; border-radius: 5px; }",
            ".task { background: #e8f4f8; }",
            ".meeting { background: #fff4e6; }",
            ".meeting.decision { background: #ffe8e8; }",
            ".email { background: #f0f4c3; }",
            ".schedule { margin-top: 30px; }",
            ".hour { margin-bottom: 10px; }",
            ".hour-label { font-weight: bold; }",
            ".block { margin-left: 20px; padding: 5px; }",
            ".protected { color: #8e44ad; }",
            ".important { color: #e74c3c; }",
            ".normal { color: #2c3e50; }",
            ".reschedule { background: #ffecb3; padding: 10px; border-radius: 5px; margin-top: 5px; }",
            ".reason { margin-left: 20px; color: #e67e22; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Daily Schedule: {brief['date']}</h1>"
        ]
        
        # Key Metrics
        metrics = brief['key_metrics']
        html.append("<div class='metrics'>")
        html.append("<div class='metric'>")
        html.append("<h3>Deep Work</h3>")
        html.append(f"<p>{metrics.get('deep_work_minutes', 0)} min</p>")
        html.append("</div>")
        html.append("<div class='metric'>")
        html.append("<h3>Goal Progress</h3>")
        html.append(f"<p>{metrics.get('north_star_alignment', 0):.0f}%</p>")
        html.append("</div>")
        html.append("<div class='metric'>")
        html.append("<h3>Balance</h3>")
        html.append(f"<p>{metrics.get('balance_score', 0):.0f}%</p>")
        html.append("</div>")
        html.append("</div>")
        
        # Critical Tasks
        html.append("<h2>Critical Tasks</h2>")
        for task in brief['critical_tasks']:
            html.append("<div class='task'>")
            html.append(f"<h3>{task['title']} ({task['estimated_time']})</h3>")
            if task['notes']:
                html.append(f"<p>{task['notes']}</p>")
            html.append("</div>")
        
        # Meeting Intelligence
        html.append("<h2>Meeting Intelligence</h2>")
        
        # Decision Meetings
        decision_meetings = brief['meeting_intelligence']['decision_meetings']
        if decision_meetings:
            html.append("<h3>Decisions Expected Today</h3>")
            for meeting in decision_meetings:
                html.append("<div class='meeting decision'>")
                html.append(f"<p><strong>{meeting['time']}:</strong> {meeting['title']}</p>")
                html.append("</div>")
        
        # Preparation Notes
        prep_notes = brief['meeting_intelligence']['preparation_notes']
        if prep_notes:
            html.append("<h3>Meeting Preparation</h3>")
            for meeting in prep_notes:
                html.append("<div class='meeting'>")
                html.append(f"<p><strong>{meeting['time']}:</strong> {meeting['title']}</p>")
                html.append("<ul>")
                for note in meeting['notes'].split('\n'):
                    html.append(f"<li>{note}</li>")
                html.append("</ul>")
                html.append("</div>")
        
        # Reschedule Suggestions
        reschedule = brief['meeting_intelligence']['reschedule_suggestions']
        if reschedule:
            html.append("<h3>Reschedule Candidates</h3>")
            for meeting in reschedule:
                html.append("<div class='reschedule'>")
                html.append(f"<p><strong>{meeting['time']}:</strong> {meeting['title']}</p>")
                html.append("<ul>")
                for reason in meeting['reasons']:
                    html.append(f"<li class='reason'>{reason}</li>")
                html.append("</ul>")
                html.append("</div>")
        
        # Recent Context
        html.append("<h2>Recent Context</h2>")
        
        # Important Emails
        important_emails = brief['recent_context']['important_emails']
        if important_emails:
            html.append("<h3>Important Emails</h3>")
            for email in important_emails:
                html.append("<div class='email'>")
                html.append(f"<p><strong>{email['subject']}</strong><br>From: {email['sender']}</p>")
                html.append("</div>")
        
        # Schedule Overview
        html.append("<h2>Today's Schedule</h2>")
        html.append("<div class='schedule'>")
        
        # Convert markdown schedule to HTML
        schedule_lines = brief['schedule_overview'].split('\n')
        current_hour = None
        
        for line in schedule_lines:
            if line.startswith('**'):
                # Hour header
                if current_hour is not None:
                    html.append("</div>")  # Close previous hour
                
                hour_label = line.strip('*')
                html.append(f"<div class='hour'>")
                html.append(f"<div class='hour-label'>{hour_label}</div>")
                current_hour = hour_label
            elif line.startswith('-'):
                # Block
                block_text = line[1:].strip()
                
                # Determine block class
                block_class = 'normal'
                if '🛡️' in block_text:
                    block_class = 'protected'
                elif '🔴' in block_text or '🟠' in block_text:
                    block_class = 'important'
                
                html.append(f"<div class='block {block_class}'>{block_text}</div>")
        
        # Close last hour
        if current_hour is not None:
            html.append("</div>")
        
        html.append("</div>")  # Close schedule
        
        # Footer
        html.append("<hr>")
        html.append("<p><em>Generated by Dynamic Scheduler Agent</em></p>")
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
