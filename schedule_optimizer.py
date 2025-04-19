"""
Schedule optimization module for the Dynamic Scheduler Agent.
Transforms prioritized tasks and meetings into an optimal daily schedule.
"""

from datetime import datetime, timedelta, time
import pytz

from config import USER_PREFERENCES, PROTECTION_OVERRIDE_CONDITIONS, CALENDAR_COLORS


class ScheduleOptimizer:
    """
    Optimizes the user's schedule based on prioritized items and user preferences.
    """
    
    def __init__(self, user_preferences=None):
        """
        Initialize the schedule optimizer with user preferences.
        
        Args:
            user_preferences (dict, optional): User preferences, defaults to config.USER_PREFERENCES
        """
        self.user_preferences = user_preferences or USER_PREFERENCES
        self.protected_blocks = self.user_preferences['protected_blocks']
        self.energy_patterns = self.user_preferences['energy_patterns']
        self.override_conditions = PROTECTION_OVERRIDE_CONDITIONS
        self.calendar_colors = CALENDAR_COLORS
    
    def generate_optimized_schedule(self, prioritized_items, target_date=None):
        """
        Generate an optimized schedule for the target date.
        
        Args:
            prioritized_items (dict): Prioritized events, tasks, and emails
            target_date (datetime.date, optional): Target date, defaults to tomorrow
            
        Returns:
            dict: Optimized schedule with time blocks
        """
        # Set target date to tomorrow if not specified
        if target_date is None:
            target_date = (datetime.now(pytz.UTC) + timedelta(days=1)).date()
        
        # Initialize schedule with empty time blocks
        schedule = self._initialize_schedule(target_date)
        
        # Identify fixed time blocks (existing meetings with multiple attendees)
        fixed_blocks = self._identify_fixed_blocks(prioritized_items['events'], target_date)
        
        # Add fixed blocks to schedule
        for block in fixed_blocks:
            schedule['blocks'].append(block)
        
        # Reserve protected time blocks
        protected_blocks = self._generate_protected_blocks(target_date)
        
        # Identify potential conflicts between protected blocks and fixed blocks
        protected_blocks = self._resolve_protected_conflicts(protected_blocks, fixed_blocks)
        
        # Add protected blocks to schedule
        for block in protected_blocks:
            schedule['blocks'].append(block)
        
        # Allocate high priority tasks to energy-aligned slots
        high_priority_tasks = self._get_high_priority_tasks(prioritized_items)
        
        # Find available time slots
        available_slots = self._find_available_slots(schedule, target_date)
        
        # Allocate tasks to available slots
        allocated_tasks = self._allocate_tasks_to_slots(high_priority_tasks, available_slots, target_date)
        
        # Add allocated tasks to schedule
        for block in allocated_tasks:
            schedule['blocks'].append(block)
        
        # Identify meetings for potential rescheduling
        reschedule_candidates = self._identify_reschedule_candidates(prioritized_items['events'], target_date)
        schedule['reschedule_candidates'] = reschedule_candidates
        
        # Sort blocks by start time
        schedule['blocks'].sort(key=lambda x: x['start'])
        
        # Calculate schedule metrics
        schedule['metrics'] = self._calculate_schedule_metrics(schedule)
        
        return schedule
    
    def _initialize_schedule(self, target_date):
        """
        Initialize an empty schedule for the target date.
        
        Args:
            target_date (datetime.date): Target date
            
        Returns:
            dict: Empty schedule structure
        """
        # Convert date to datetime objects for start and end of day
        day_start = datetime.combine(target_date, time(0, 0)).replace(tzinfo=pytz.UTC)
        day_end = datetime.combine(target_date, time(23, 59, 59)).replace(tzinfo=pytz.UTC)
        
        # Get day of week (0 = Monday, 6 = Sunday)
        day_of_week = target_date.weekday()
        
        # Determine work location
        work_location = self.user_preferences['work_location'].get(day_of_week, 'home')
        
        return {
            'date': target_date,
            'day_start': day_start,
            'day_end': day_end,
            'work_location': work_location,
            'blocks': [],
            'unscheduled_tasks': [],
            'reschedule_candidates': [],
            'metrics': {}
        }
    
    def _identify_fixed_blocks(self, events, target_date):
        """
        Identify fixed time blocks (existing meetings with multiple attendees).
        
        Args:
            events (list): Prioritized calendar events
            target_date (datetime.date): Target date
            
        Returns:
            list: Fixed time blocks
        """
        fixed_blocks = []
        
        for event in events:
            # Skip events that are not on the target date
            start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            if start_time.date() != target_date:
                continue
            
            # Check if this is a fixed event (meeting with multiple attendees)
            attendees = event.get('attendees', [])
            is_meeting = len(attendees) > 1
            
            if is_meeting:
                # Create a fixed block for this meeting
                fixed_blocks.append({
                    'id': event['id'],
                    'title': event['summary'],
                    'start': start_time,
                    'end': datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00')),
                    'type': 'meeting',
                    'priority': event.get('priority', {}),
                    'is_fixed': True,
                    'attendees': len(attendees),
                    'location': event.get('location', '')
                })
        
        return fixed_blocks
    
    def _generate_protected_blocks(self, target_date):
        """
        Generate protected time blocks based on user preferences.
        
        Args:
            target_date (datetime.date): Target date
            
        Returns:
            list: Protected time blocks
        """
        protected_blocks = []
        
        # Generate blocks for each protected time category
        for block_type, block_config in self.protected_blocks.items():
            # For deep work, use preferred or alternative time
            if block_type == 'deep_work':
                preferred_time = block_config['preferred_time']
                start_time = datetime.combine(target_date, preferred_time).replace(tzinfo=pytz.UTC)
                end_time = start_time + timedelta(minutes=block_config['duration'])
                
                protected_blocks.append({
                    'id': f"protected_{block_type}_{target_date}",
                    'title': f"[PROTECTED] Deep Work",
                    'start': start_time,
                    'end': end_time,
                    'type': 'protected',
                    'protection_level': block_config['protection_level'],
                    'is_fixed': False,
                    'color_id': self.calendar_colors.get(block_type)
                })
            else:
                # For other protected blocks with fixed start/end times
                if 'start_time' in block_config and 'end_time' in block_config:
                    start_time = datetime.combine(target_date, block_config['start_time']).replace(tzinfo=pytz.UTC)
                    
                    # Handle blocks that cross midnight
                    if block_config['end_time'] < block_config['start_time']:
                        end_time = datetime.combine(target_date + timedelta(days=1), block_config['end_time']).replace(tzinfo=pytz.UTC)
                    else:
                        end_time = datetime.combine(target_date, block_config['end_time']).replace(tzinfo=pytz.UTC)
                    
                    # Format the title based on block type
                    if block_type == 'physical_wellbeing':
                        title = "[PROTECTED] CrossFit"
                    elif block_type == 'family_time':
                        title = "[PROTECTED] Family Time"
                    elif block_type == 'learning_time':
                        title = "[PROTECTED] Learning: AI Developments"
                    elif block_type == 'research_time':
                        title = "[PROTECTED] Research: AI Tools"
                    else:
                        title = f"[PROTECTED] {block_type.replace('_', ' ').title()}"
                    
                    protected_blocks.append({
                        'id': f"protected_{block_type}_{target_date}",
                        'title': title,
                        'start': start_time,
                        'end': end_time,
                        'type': 'protected',
                        'protection_level': block_config['protection_level'],
                        'is_fixed': False,
                        'color_id': self.calendar_colors.get(block_type)
                    })
        
        return protected_blocks
    
    def _resolve_protected_conflicts(self, protected_blocks, fixed_blocks):
        """
        Resolve conflicts between protected blocks and fixed blocks.
        
        Args:
            protected_blocks (list): Protected time blocks
            fixed_blocks (list): Fixed time blocks
            
        Returns:
            list: Adjusted protected blocks
        """
        adjusted_blocks = []
        
        for protected_block in protected_blocks:
            # Check for conflicts with fixed blocks
            conflicts = []
            for fixed_block in fixed_blocks:
                if self._blocks_overlap(protected_block, fixed_block):
                    conflicts.append(fixed_block)
            
            if not conflicts:
                # No conflicts, keep the protected block as is
                adjusted_blocks.append(protected_block)
                continue
            
            # For each conflict, check if the protected block can be overridden
            can_override = True
            for conflict in conflicts:
                priority = conflict.get('priority', {})
                quadrant = priority.get('quadrant', 'neither')
                score = priority.get('score', 0)
                
                protection_level = protected_block['protection_level']
                override_condition = self.override_conditions.get(protection_level, {})
                
                # Check if the conflict meets the override conditions
                if quadrant not in override_condition.get('quadrant', []) or score < override_condition.get('min_score', 100):
                    can_override = False
                    break
            
            if can_override:
                # Protected block can be overridden, don't add it
                continue
            else:
                # Protected block cannot be overridden, try to adjust it
                if protected_block['type'] == 'deep_work':
                    # For deep work, try the alternative time
                    alt_time = self.protected_blocks['deep_work']['alternative_time']
                    alt_start = datetime.combine(protected_block['start'].date(), alt_time).replace(tzinfo=pytz.UTC)
                    alt_end = alt_start + (protected_block['end'] - protected_block['start'])
                    
                    # Check if alternative time has conflicts
                    alt_conflicts = False
                    for fixed_block in fixed_blocks:
                        if (alt_start < fixed_block['end'] and alt_end > fixed_block['start']):
                            alt_conflicts = True
                            break
                    
                    if not alt_conflicts:
                        # Use alternative time
                        protected_block['start'] = alt_start
                        protected_block['end'] = alt_end
                        adjusted_blocks.append(protected_block)
                else:
                    # For other protected blocks, keep them but mark as conflicted
                    protected_block['has_conflict'] = True
                    adjusted_blocks.append(protected_block)
        
        return adjusted_blocks
    
    def _get_high_priority_tasks(self, prioritized_items):
        """
        Get high priority tasks from prioritized items.
        
        Args:
            prioritized_items (dict): Prioritized events, tasks, and emails
            
        Returns:
            list: High priority tasks
        """
        high_priority_tasks = []
        
        # Add high priority tasks
        for task in prioritized_items['tasks']:
            priority = task.get('priority', {})
            score = priority.get('score', 0)
            
            if score >= 70:  # Consider tasks with score >= 70 as high priority
                # Estimate task duration (simplified)
                # In a real implementation, this would be more sophisticated
                title = task.get('title', '')
                notes = task.get('notes', '')
                estimated_duration = 30  # Default 30 minutes
                
                if 'quick' in title.lower() or 'quick' in notes.lower():
                    estimated_duration = 15
                elif 'long' in title.lower() or 'long' in notes.lower():
                    estimated_duration = 60
                
                high_priority_tasks.append({
                    'id': task['id'],
                    'title': task['title'],
                    'type': 'task',
                    'priority': priority,
                    'estimated_duration': estimated_duration,
                    'notes': task.get('notes', '')
                })
        
        # Add email tasks for high priority emails
        for email in prioritized_items['emails']:
            priority = email.get('priority', {})
            score = priority.get('score', 0)
            
            if score >= 70:  # Consider emails with score >= 70 as high priority
                # Extract email details
                headers = {header['name']: header['value'] for header in email.get('payload', {}).get('headers', [])}
                subject = headers.get('Subject', '')
                sender = headers.get('From', '')
                
                high_priority_tasks.append({
                    'id': email['id'],
                    'title': f"Respond to email: {subject}",
                    'type': 'email',
                    'priority': priority,
                    'estimated_duration': 15,  # Default 15 minutes for email responses
                    'notes': f"From: {sender}"
                })
        
        # Sort by priority score
        high_priority_tasks.sort(key=lambda x: x['priority']['score'], reverse=True)
        
        return high_priority_tasks
    
    def _find_available_slots(self, schedule, target_date):
        """
        Find available time slots in the schedule.
        
        Args:
            schedule (dict): Current schedule
            target_date (datetime.date): Target date
            
        Returns:
            list: Available time slots
        """
        # Get all blocks in the schedule
        blocks = schedule['blocks']
        
        # Sort blocks by start time
        blocks.sort(key=lambda x: x['start'])
        
        # Define day boundaries
        day_start = datetime.combine(target_date, time(6, 0)).replace(tzinfo=pytz.UTC)  # Start at 6 AM
        day_end = datetime.combine(target_date, time(22, 0)).replace(tzinfo=pytz.UTC)  # End at 10 PM
        
        # Initialize available slots
        available_slots = []
        
        # If no blocks, the entire day is available
        if not blocks:
            available_slots.append({
                'start': day_start,
                'end': day_end,
                'duration': int((day_end - day_start).total_seconds() / 60)
            })
            return available_slots
        
        # Find gaps between blocks
        current_time = day_start
        
        for block in blocks:
            # Skip blocks outside the day boundaries
            if block['end'] <= day_start or block['start'] >= day_end:
                continue
            
            # Adjust block boundaries to day boundaries
            block_start = max(block['start'], day_start)
            block_end = min(block['end'], day_end)
            
            # If there's a gap before this block, add it as an available slot
            if current_time < block_start:
                duration = int((block_start - current_time).total_seconds() / 60)
                if duration >= 15:  # Only consider slots of at least 15 minutes
                    available_slots.append({
                        'start': current_time,
                        'end': block_start,
                        'duration': duration
                    })
            
            # Move current time to the end of this block
            current_time = block_end
        
        # Add final slot if there's time left in the day
        if current_time < day_end:
            duration = int((day_end - current_time).total_seconds() / 60)
            if duration >= 15:  # Only consider slots of at least 15 minutes
                available_slots.append({
                    'start': current_time,
                    'end': day_end,
                    'duration': duration
                })
        
        return available_slots
    
    def _allocate_tasks_to_slots(self, tasks, available_slots, target_date):
        """
        Allocate tasks to available time slots.
        
        Args:
            tasks (list): Tasks to allocate
            available_slots (list): Available time slots
            target_date (datetime.date): Target date
            
        Returns:
            list: Allocated task blocks
        """
        allocated_blocks = []
        
        # Sort tasks by priority (highest first)
        tasks.sort(key=lambda x: x['priority']['score'], reverse=True)
        
        # Sort slots by energy alignment for the time of day
        for slot in available_slots:
            slot_time = slot['start'].time()
            slot['energy_alignment'] = self._get_energy_alignment_for_time(slot_time)
        
        # For each task, find the best slot
        for task in tasks:
            best_slot = None
            best_score = -1
            
            for i, slot in enumerate(available_slots):
                # Skip slots that are too short
                if slot['duration'] < task['estimated_duration']:
                    continue
                
                # Calculate alignment score
                energy_alignment = slot['energy_alignment']
                quadrant = task['priority']['quadrant']
                
                # Adjust score based on quadrant
                if quadrant == 'urgent_important':
                    # For urgent+important tasks, prioritize earlier slots
                    time_factor = 1 - (slot['start'].hour / 24)
                    score = (energy_alignment * 0.5) + (time_factor * 100 * 0.5)
                elif quadrant == 'important':
                    # For important tasks, prioritize high energy slots
                    score = energy_alignment
                elif quadrant == 'urgent':
                    # For urgent tasks, prioritize earlier slots
                    time_factor = 1 - (slot['start'].hour / 24)
                    score = time_factor * 100
                else:
                    # For other tasks, use energy alignment
                    score = energy_alignment
                
                if score > best_score:
                    best_score = score
                    best_slot = (i, slot)
            
            if best_slot:
                i, slot = best_slot
                
                # Create a block for this task
                task_block = {
                    'id': task['id'],
                    'title': task['title'],
                    'start': slot['start'],
                    'end': slot['start'] + timedelta(minutes=task['estimated_duration']),
                    'type': task['type'],
                    'priority': task['priority'],
                    'is_fixed': False
                }
                
                allocated_blocks.append(task_block)
                
                # Update the slot
                new_start = slot['start'] + timedelta(minutes=task['estimated_duration'])
                new_duration = int((slot['end'] - new_start).total_seconds() / 60)
                
                if new_duration >= 15:
                    # Slot still has usable time, update it
                    available_slots[i] = {
                        'start': new_start,
                        'end': slot['end'],
                        'duration': new_duration,
                        'energy_alignment': slot['energy_alignment']
                    }
                else:
                    # Slot is too small now, remove it
                    available_slots.pop(i)
        
        return allocated_blocks
    
    def _identify_reschedule_candidates(self, events, target_date):
        """
        Identify meetings that are candidates for rescheduling.
        
        Args:
            events (list): Prioritized calendar events
            target_date (datetime.date): Target date
            
        Returns:
            list: Reschedule candidates
        """
        reschedule_candidates = []
        
        for event in events:
            # Skip events that are not on the target date
            start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            if start_time.date() != target_date:
                continue
            
            # Check if this event is a meeting
            attendees = event.get('attendees', [])
            is_meeting = len(attendees) > 0
            
            if is_meeting:
                # Check if this meeting is a reschedule candidate
                priority = event.get('priority', {})
                if priority.get('reschedule_candidate', False):
                    reschedule_candidates.append({
                        'id': event['id'],
                        'title': event['summary'],
                        'start': start_time,
                        'end': datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00')),
                        'organizer': event.get('organizer', {}).get('email', ''),
                        'attendees': [attendee.get('email') for attendee in attendees],
                        'reasons': self._get_reschedule_reasons(priority)
                    })
        
        return reschedule_candidates
    
    def _get_reschedule_reasons(self, priority):
        """
        Get reasons why a meeting is a reschedule candidate.
        
        Args:
            priority (dict): Meeting priority information
            
        Returns:
            list: Reasons for rescheduling
        """
        reasons = []
        
        if not priority.get('has_agenda', False):
            reasons.append("No clear agenda")
        
        if not priority.get('has_outcomes', False):
            reasons.append("No clear expected outcomes")
        
        if priority.get('user_necessity', 5) <= 3:
            reasons.append("Your presence may not be critical")
        
        if priority.get('strategic_alignment', 0) <= 2:
            reasons.append("Low alignment with strategic goals")
        
        if not priority.get('decision_authority', False):
            reasons.append("No decisions expected to be made")
        
        return reasons
    
    def _calculate_schedule_metrics(self, schedule):
        """
        Calculate metrics for the schedule.
        
        Args:
            schedule (dict): Optimized schedule
            
        Returns:
            dict: Schedule metrics
        """
        blocks = schedule['blocks']
        
        # Initialize metrics
        metrics = {
            'deep_work_minutes': 0,
            'meeting_minutes': 0,
            'task_minutes': 0,
            'protected_minutes': 0,
            'total_scheduled_minutes': 0,
            'north_star_alignment': 0,
            'balance_score': 0
        }
        
        # Calculate time allocations
        for block in blocks:
            duration = int((block['end'] - block['start']).total_seconds() / 60)
            
            if block['type'] == 'protected':
                if 'Deep Work' in block['title']:
                    metrics['deep_work_minutes'] += duration
                metrics['protected_minutes'] += duration
            elif block['type'] == 'meeting':
                metrics['meeting_minutes'] += duration
            elif block['type'] in ['task', 'email']:
                metrics['task_minutes'] += duration
            
            metrics['total_scheduled_minutes'] += duration
            
            # Calculate North Star alignment
            if block['type'] in ['meeting', 'task', 'email']:
                priority = block.get('priority', {})
                goal_alignment = priority.get('goal_alignment', 0)
                
                # Weight by duration
                metrics['north_star_alignment'] += goal_alignment * duration
        
        # Normalize North Star alignment
        if metrics['total_scheduled_minutes'] > 0:
            metrics['north_star_alignment'] /= metrics['total_scheduled_minutes']
        
        # Calculate balance score (work vs. personal time)
        work_minutes = metrics['meeting_minutes'] + metrics['task_minutes']
        personal_minutes = metrics['protected_minutes']
        total_minutes = work_minutes + personal_minutes
        
        if total_minutes > 0:
            # Ideal balance: 2/3 work, 1/3 personal
            ideal_work_ratio = 2/3
            actual_work_ratio = work_minutes / total_minutes
            
            # Score based on how close to ideal ratio (100 = perfect)
            metrics['balance_score'] = 100 - (abs(ideal_work_ratio - actual_work_ratio) * 100)
        
        return metrics
    
    def _blocks_overlap(self, block1, block2):
        """
        Check if two blocks overlap in time.
        
        Args:
            block1 (dict): First block
            block2 (dict): Second block
            
        Returns:
            bool: True if blocks overlap, False otherwise
        """
        return block1['start'] < block2['end'] and block1['end'] > block2['start']
    
    def _get_energy_alignment_for_time(self, time_obj):
        """
        Get energy alignment score for a specific time.
        
        Args:
            time_obj (time): Time to check
            
        Returns:
            float: Energy alignment score (0-100)
        """
        # Find which energy pattern this time falls into
        for pattern_name, pattern in self.energy_patterns.items():
            start = pattern['start_time']
            end = pattern['end_time']
            
            # Handle patterns that cross midnight
            if end < start:
                if (time_obj >= start) or (time_obj < end):
                    energy_level = pattern['energy_level']
                    break
            else:
                if start <= time_obj < end:
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
