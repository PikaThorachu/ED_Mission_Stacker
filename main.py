import json
import os
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from pathlib import Path
import logging
import glob

# Import our custom modules
from events import parse_mission_event, is_mission_event
from mission_stack import MissionStack
from kill_ratio import KillRatioCalculator

class GameLogMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Elite Dangerous Mission Monitor")
        self.root.geometry("1200x800")
        
        # Configuration
        self.log_folder = ""  # Folder to monitor for log files
        self.current_log_file = ""  # Current log file being monitored
        self.monitoring = False
        self.last_file_size = 0
        self.update_interval = 1000  # milliseconds
        
        # Mission tracking
        self.mission_stack = MissionStack()
        self.kill_ratio_calculator = KillRatioCalculator()
        
        # Track event statistics - updated to include mission events
        self.event_stats = {
            # Mission events
            'mission_accepted': 0,
            'mission_completed': 0,
            'mission_failed': 0,
            'mission_abandoned': 0,
            'missions_event': 0,
            
            # Other events (you can add more as needed)
            'player_join': 0,
            'player_quit': 0,
            'player_death': 0,
            'player_kill': 0,
            'game_start': 0,
            'game_end': 0
        }
        
        # Player statistics
        self.player_stats = {}
        
        self.setup_ui()
        self.setup_logging()
        
    def setup_ui(self):
        """Create the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Folder selection
        ttk.Label(controls_frame, text="Log Folder:").grid(row=0, column=0, sticky=tk.W)
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(controls_frame, textvariable=self.folder_path_var, width=50)
        folder_entry.grid(row=0, column=1, padx=(5, 5), sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(controls_frame, text="Browse", command=self.browse_folder)
        browse_btn.grid(row=0, column=2, padx=(5, 5))
        
        # Monitor button
        self.monitor_btn = ttk.Button(controls_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.monitor_btn.grid(row=0, column=3, padx=(5, 0))
        
        # Clear missions button
        self.clear_btn = ttk.Button(controls_frame, text="Clear Missions", command=self.clear_missions)
        self.clear_btn.grid(row=0, column=4, padx=(5, 0))
        
        # Status label
        self.status_var = tk.StringVar(value="Status: Select a folder to begin")
        ttk.Label(controls_frame, textvariable=self.status_var).grid(row=0, column=5, padx=(10, 0))
        
        # Current file info
        file_info_frame = ttk.Frame(main_frame)
        file_info_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(file_info_frame, text="Current Log File:").grid(row=0, column=0, sticky=tk.W)
        self.current_file_var = tk.StringVar(value="No file selected")
        ttk.Label(file_info_frame, textvariable=self.current_file_var, foreground="blue").grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Mission Stack Tab
        self.setup_mission_stack_tab()
        
        # Kill Ratio Analysis Tab
        self.setup_kill_ratio_tab()
        
        # Event Statistics Tab
        self.setup_statistics_tab()
        
        # Player Statistics Tab  
        self.setup_player_stats_tab()
        
        # Log Display Tab
        self.setup_log_display_tab()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        
    def setup_mission_stack_tab(self):
        """Setup the mission stack display tab"""
        mission_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(mission_frame, text="Massacre Missions")
        
        # Mission summary frame
        summary_frame = ttk.LabelFrame(mission_frame, text="Mission Summary", padding="5")
        summary_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        
        # Summary labels
        ttk.Label(summary_frame, text="Total Missions:").grid(row=0, column=0, sticky=tk.W)
        self.total_missions_var = tk.StringVar(value="0")
        ttk.Label(summary_frame, textvariable=self.total_missions_var, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(summary_frame, text="Total Kills:").grid(row=0, column=2, sticky=tk.W)
        self.total_kills_var = tk.StringVar(value="0/0")
        ttk.Label(summary_frame, textvariable=self.total_kills_var, font=('Arial', 10, 'bold')).grid(row=0, column=3, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(summary_frame, text="Total Reward:").grid(row=0, column=4, sticky=tk.W)
        self.total_reward_var = tk.StringVar(value="0 CR")
        ttk.Label(summary_frame, textvariable=self.total_reward_var, font=('Arial', 10, 'bold')).grid(row=0, column=5, sticky=tk.W, padx=(5, 0))
        
        # Mission treeview
        tree_frame = ttk.LabelFrame(mission_frame, text="Mission Details", padding="5")
        tree_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        columns = ('target_faction', 'issuing_faction', 'mission_name', 'kills', 'reward', 'expiry', 'wing')
        self.mission_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.mission_tree.heading('target_faction', text='Target Faction')
        self.mission_tree.heading('issuing_faction', text='Issuing Faction')
        self.mission_tree.heading('mission_name', text='Mission Name')
        self.mission_tree.heading('kills', text='Kills')
        self.mission_tree.heading('reward', text='Reward')
        self.mission_tree.heading('expiry', text='Expiry')
        self.mission_tree.heading('wing', text='Wing')
        
        # Define columns
        self.mission_tree.column('target_faction', width=150)
        self.mission_tree.column('issuing_faction', width=150)
        self.mission_tree.column('mission_name', width=250)
        self.mission_tree.column('kills', width=80)
        self.mission_tree.column('reward', width=100)
        self.mission_tree.column('expiry', width=120)
        self.mission_tree.column('wing', width=50)
        
        self.mission_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for mission tree
        mission_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.mission_tree.yview)
        mission_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.mission_tree.configure(yscrollcommand=mission_scrollbar.set)
        
        # Configure grid weights for mission frame
        mission_frame.columnconfigure(0, weight=1)
        mission_frame.rowconfigure(1, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
    def setup_kill_ratio_tab(self):
        """Setup the kill ratio analysis tab"""
        ratio_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(ratio_frame, text="Kill Ratio Analysis")
        
        # Kill ratio explanation
        explanation_frame = ttk.LabelFrame(ratio_frame, text="Kill Ratio Explanation", padding="5")
        explanation_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        
        explanation_text = (
            "Kill Ratio represents the efficiency of completing missions across different factions.\n"
            "- Ratio of 1.00: Only one faction issuing missions for this target\n"
            "- Ratio < 1.00: Multiple factions, efficiency depends on kill distribution\n"
            "- Missions complete sequentially within each faction\n"
            "- Factions complete missions concurrently\n"
            "Higher ratio = more efficient mission completion"
        )
        
        explanation_label = ttk.Label(explanation_frame, text=explanation_text, justify=tk.LEFT)
        explanation_label.grid(row=0, column=0, sticky=tk.W)
        
        # Kill ratio treeview
        ratio_tree_frame = ttk.LabelFrame(ratio_frame, text="Kill Ratio by Target Faction", padding="5")
        ratio_tree_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        columns = ('target_faction', 'faction_count', 'total_remaining', 'kill_ratio')
        self.ratio_tree = ttk.Treeview(ratio_tree_frame, columns=columns, show='headings', height=10)
        
        # Define headings
        self.ratio_tree.heading('target_faction', text='Target Faction')
        self.ratio_tree.heading('faction_count', text='Issuing Factions')
        self.ratio_tree.heading('total_remaining', text='Total Remaining Kills')
        self.ratio_tree.heading('kill_ratio', text='Kill Ratio')
        
        # Define columns
        self.ratio_tree.column('target_faction', width=200)
        self.ratio_tree.column('faction_count', width=120)
        self.ratio_tree.column('total_remaining', width=140)
        self.ratio_tree.column('kill_ratio', width=100)
        
        self.ratio_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for ratio tree
        ratio_scrollbar = ttk.Scrollbar(ratio_tree_frame, orient=tk.VERTICAL, command=self.ratio_tree.yview)
        ratio_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.ratio_tree.configure(yscrollcommand=ratio_scrollbar.set)
        
        # Detailed breakdown frame
        breakdown_frame = ttk.LabelFrame(ratio_frame, text="Detailed Breakdown", padding="5")
        breakdown_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Breakdown treeview
        breakdown_columns = ('target_faction', 'issuing_faction', 'mission_count', 'remaining_kills')
        self.breakdown_tree = ttk.Treeview(breakdown_frame, columns=breakdown_columns, show='headings', height=8)
        
        # Define headings
        self.breakdown_tree.heading('target_faction', text='Target Faction')
        self.breakdown_tree.heading('issuing_faction', text='Issuing Faction')
        self.breakdown_tree.heading('mission_count', text='Mission Count')
        self.breakdown_tree.heading('remaining_kills', text='Remaining Kills')
        
        # Define columns
        self.breakdown_tree.column('target_faction', width=150)
        self.breakdown_tree.column('issuing_faction', width=150)
        self.breakdown_tree.column('mission_count', width=100)
        self.breakdown_tree.column('remaining_kills', width=120)
        
        self.breakdown_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for breakdown tree
        breakdown_scrollbar = ttk.Scrollbar(breakdown_frame, orient=tk.VERTICAL, command=self.breakdown_tree.yview)
        breakdown_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.breakdown_tree.configure(yscrollcommand=breakdown_scrollbar.set)
        
        # Configure grid weights for ratio frame
        ratio_frame.columnconfigure(0, weight=1)
        ratio_frame.rowconfigure(1, weight=1)
        ratio_frame.rowconfigure(2, weight=1)
        ratio_tree_frame.columnconfigure(0, weight=1)
        ratio_tree_frame.rowconfigure(0, weight=1)
        breakdown_frame.columnconfigure(0, weight=1)
        breakdown_frame.rowconfigure(0, weight=1)
        
    def setup_statistics_tab(self):
        """Setup the event statistics tab"""
        stats_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(stats_frame, text="Event Statistics")
        
        # Event statistics labels
        self.stats_labels = {}
        
        # Mission events frame
        mission_stats_frame = ttk.LabelFrame(stats_frame, text="Mission Events", padding="5")
        mission_stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10), padx=(0, 10))
        
        mission_events = ['mission_accepted', 'mission_completed', 'mission_failed', 'mission_abandoned', 'missions_event']
        for i, event in enumerate(mission_events):
            ttk.Label(mission_stats_frame, text=event.replace('_', ' ').title() + ":").grid(row=i, column=0, sticky=tk.W)
            self.stats_labels[event] = ttk.Label(mission_stats_frame, text="0")
            self.stats_labels[event].grid(row=i, column=1, sticky=tk.W, padx=(5, 15))
        
        # Other events frame
        other_stats_frame = ttk.LabelFrame(stats_frame, text="Other Events", padding="5")
        other_stats_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        
        other_events = ['player_join', 'player_quit', 'player_death', 'player_kill', 'game_start', 'game_end']
        for i, event in enumerate(other_events):
            ttk.Label(other_stats_frame, text=event.replace('_', ' ').title() + ":").grid(row=i, column=0, sticky=tk.W)
            self.stats_labels[event] = ttk.Label(other_stats_frame, text="0")
            self.stats_labels[event].grid(row=i, column=1, sticky=tk.W, padx=(5, 15))
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
    def setup_player_stats_tab(self):
        """Setup the player statistics tab"""
        player_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(player_frame, text="Player Statistics")
        
        # Player stats treeview
        columns = ('player', 'kills', 'deaths', 'join_time')
        self.player_tree = ttk.Treeview(player_frame, columns=columns, show='headings', height=20)
        
        # Define headings
        self.player_tree.heading('player', text='Player')
        self.player_tree.heading('kills', text='Kills')
        self.player_tree.heading('deaths', text='Deaths')
        self.player_tree.heading('join_time', text='Join Time')
        
        # Define columns
        self.player_tree.column('player', width=150)
        self.player_tree.column('kills', width=80)
        self.player_tree.column('deaths', width=80)
        self.player_tree.column('join_time', width=150)
        
        self.player_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for player tree
        player_scrollbar = ttk.Scrollbar(player_frame, orient=tk.VERTICAL, command=self.player_tree.yview)
        player_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.player_tree.configure(yscrollcommand=player_scrollbar.set)
        
        player_frame.columnconfigure(0, weight=1)
        player_frame.rowconfigure(0, weight=1)
        
    def setup_log_display_tab(self):
        """Setup the log display tab"""
        log_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(log_frame, text="Event Log")
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=30, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def setup_logging(self):
        """Setup application logging"""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    def browse_folder(self):
        """Open folder browser dialog with better drive access"""
        try:
            # Try to start from common Elite Dangerous journal locations first
            possible_paths = []
            
            # Windows common locations
            if os.name == 'nt':
                # Saved Games folder (default Elite Dangerous location)
                saved_games = os.path.join(os.path.expanduser("~"), "Saved Games")
                elite_path = os.path.join(saved_games, "Frontier Developments", "Elite Dangerous")
                if os.path.exists(elite_path):
                    possible_paths.append(elite_path)
                possible_paths.append(saved_games)
                possible_paths.append(os.path.expanduser("~"))  # Home directory
                possible_paths.append("C:\\")  # Root of C drive
            
            # Linux common locations
            elif os.name == 'posix':
                home = os.path.expanduser("~")
                elite_path = os.path.join(home, ".local", "share", "Frontier Developments", "Elite Dangerous")
                if os.path.exists(elite_path):
                    possible_paths.append(elite_path)
                possible_paths.append(home)
                possible_paths.append("/")  # Root directory
            
            # Mac common locations
            else:
                home = os.path.expanduser("~")
                elite_path = os.path.join(home, "Library", "Application Support", "Frontier Developments", "Elite Dangerous")
                if os.path.exists(elite_path):
                    possible_paths.append(elite_path)
                possible_paths.append(home)
                possible_paths.append("/")  # Root directory
            
            # Use the first existing path, or home directory as fallback
            initial_dir = possible_paths[0] if possible_paths else os.path.expanduser("~")
            
            folder = filedialog.askdirectory(
                title="Select Elite Dangerous Journal Folder",
                initialdir=initial_dir
            )
            
            if folder:
                self.log_folder = folder
                self.folder_path_var.set(folder)
                self.status_var.set("Status: Folder selected - ready to monitor")
                self.find_most_recent_log_file()
                self.log_message(f"Selected folder: {folder}")
                
        except Exception as e:
            # Fallback to simple directory selection if anything goes wrong
            self.log_message(f"Error with enhanced folder selection: {e}")
            folder = filedialog.askdirectory(title="Select Elite Dangerous Journal Folder")
            if folder:
                self.log_folder = folder
                self.folder_path_var.set(folder)
                self.status_var.set("Status: Folder selected - ready to monitor")
                self.find_most_recent_log_file()

    
    def find_most_recent_log_file(self):
        """Find the most recent .log file in the selected folder"""
        if not self.log_folder or not os.path.exists(self.log_folder):
            return None
        
        log_files = glob.glob(os.path.join(self.log_folder, "*.log"))
        if not log_files:
            self.current_file_var.set("No .log files found")
            return None
        
        # Find the most recently modified log file
        most_recent_file = max(log_files, key=os.path.getmtime)
        self.current_log_file = most_recent_file
        self.current_file_var.set(os.path.basename(most_recent_file))
        self.log_message(f"Found log file: {os.path.basename(most_recent_file)}")
        
        return most_recent_file
    
    def check_for_newer_log_file(self):
        """Check if a newer log file has been created in the folder"""
        if not self.log_folder:
            return False
        
        current_files = glob.glob(os.path.join(self.log_folder, "*.log"))
        if not current_files:
            return False
        
        newest_file = max(current_files, key=os.path.getmtime)
        
        # If we found a different file that's newer than our current one
        if newest_file != self.current_log_file:
            self.log_message(f"New log file detected: {os.path.basename(newest_file)}")
            self.current_log_file = newest_file
            self.current_file_var.set(os.path.basename(newest_file))
            self.last_file_size = 0  # Reset file size to read from beginning of new file
            return True
        
        return False
        
    def toggle_monitoring(self):
        """Start or stop monitoring"""
        if not self.monitoring:
            if not self.log_folder:
                self.log_message("Error: Please select a log folder first!")
                return
            
            # Find the most recent log file
            if not self.find_most_recent_log_file():
                self.log_message("Error: No .log files found in the selected folder!")
                return
            
            self.monitoring = True
            self.monitor_btn.config(text="Stop Monitoring")
            self.status_var.set("Status: Monitoring...")
            self.log_message("Started monitoring log folder")
            
            # Reset statistics when starting new monitoring session
            self.reset_statistics()
            
            # Start monitoring in a separate thread
            self.monitor_thread = threading.Thread(target=self.monitor_log_file, daemon=True)
            self.monitor_thread.start()
        else:
            self.monitoring = False
            self.monitor_btn.config(text="Start Monitoring")
            self.status_var.set("Status: Monitoring stopped")
            self.log_message("Stopped monitoring log folder")
    
    def clear_missions(self):
        """Clear all missions from the mission stack"""
        self.mission_stack.clear()
        self.update_mission_display()
        self.log_message("Mission stack cleared")
    
    def reset_statistics(self):
        """Reset all statistics when starting to monitor a new file"""
        for event_type in self.event_stats:
            self.event_stats[event_type] = 0
        self.player_stats.clear()
        self.mission_stack.clear()
        self.update_stats_display()
        self.update_player_display()
        self.update_mission_display()
    
    def monitor_log_file(self):
        """Monitor the log file for changes and process new entries"""
        self.last_file_size = 0
        
        while self.monitoring:
            try:
                # Check for newer log files every 5 seconds
                if int(time.time()) % 5 == 0:
                    self.check_for_newer_log_file()
                
                if not self.current_log_file or not os.path.exists(self.current_log_file):
                    time.sleep(1)
                    continue
                
                current_size = os.path.getsize(self.current_log_file)
                
                if current_size > self.last_file_size:
                    # File has grown, read new content
                    with open(self.current_log_file, 'r', encoding='utf-8') as file:
                        if self.last_file_size > 0:
                            file.seek(self.last_file_size)
                        new_content = file.read()
                        self.last_file_size = current_size
                        
                        if new_content.strip():
                            self.process_log_content(new_content)
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                self.log_message(f"Error reading log file: {str(e)}")
                time.sleep(1)
    
    def process_log_content(self, content):
        """Process the log content and extract events"""
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                event_data = json.loads(line)
                self.process_event(event_data)
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue
    
    def process_event(self, event_data):
        """Process a single game event"""
        # Check if it's a mission event first
        if is_mission_event(event_data):
            mission_event = parse_mission_event(event_data)
            if mission_event:
                self.handle_mission_event(mission_event)
                return
        
        # Handle non-mission events
        event_type = event_data.get('event', 'unknown')
        timestamp = event_data.get('timestamp', datetime.now().isoformat())
        
        # Update statistics based on event type
        if event_type in self.event_stats:
            self.event_stats[event_type] += 1
            self.update_stats_display()
        
        # Process specific event types
        if event_type == 'player_join':
            self.handle_player_join(event_data, timestamp)
        elif event_type == 'player_quit':
            self.handle_player_quit(event_data, timestamp)
        elif event_type == 'player_kill':
            self.handle_player_kill(event_data, timestamp)
        elif event_type == 'player_death':
            self.handle_player_death(event_data, timestamp)
        
        # Log the event
        self.log_message(f"[{timestamp}] {event_type}")
    
    def handle_mission_event(self, mission_event):
        """Handle mission events using the structured classes"""
        # Convert mission event to dictionary for the mission stack
        event_dict = mission_event.to_dict()
        
        # Process the event in the mission stack
        processed = self.mission_stack.process_event(event_dict)
        
        if processed:
            # Update mission event statistics
            event_type = mission_event.event
            if event_type in self.event_stats:
                self.event_stats[event_type] += 1
                self.update_stats_display()
            
            # Log the mission event
            self.log_message(f"[{mission_event.timestamp}] {str(mission_event)}")
            
            # Update UI with mission stack summary
            self.update_mission_display()
    
    def handle_player_join(self, event, timestamp):
        """Handle player join event"""
        player = event.get('player')
        if player and player not in self.player_stats:
            self.player_stats[player] = {
                'kills': 0,
                'deaths': 0,
                'join_time': timestamp
            }
            self.update_player_display()
    
    def handle_player_quit(self, event, timestamp):
        """Handle player quit event"""
        # You could add logic here to track session duration, etc.
        pass
    
    def handle_player_kill(self, event, timestamp):
        """Handle player kill event"""
        killer = event.get('killer')
        if killer and killer in self.player_stats:
            self.player_stats[killer]['kills'] += 1
            self.update_player_display()
    
    def handle_player_death(self, event, timestamp):
        """Handle player death event"""
        player = event.get('player')
        if player and player in self.player_stats:
            self.player_stats[player]['deaths'] += 1
            self.update_player_display()
    
    def update_stats_display(self):
        """Update the statistics display in the GUI"""
        def update():
            for event_type, count in self.event_stats.items():
                if event_type in self.stats_labels:
                    self.stats_labels[event_type].config(text=str(count))
        
        # Schedule update in main thread
        self.root.after(0, update)
    
    def update_player_display(self):
        """Update the player statistics display"""
        def update():
            # Clear existing items
            for item in self.player_tree.get_children():
                self.player_tree.delete(item)
            
            # Add sorted player data (by kills descending)
            sorted_players = sorted(
                self.player_stats.items(),
                key=lambda x: x[1]['kills'],
                reverse=True
            )
            
            for player, stats in sorted_players:
                self.player_tree.insert('', tk.END, values=(
                    player,
                    stats['kills'],
                    stats['deaths'],
                    stats['join_time'][:19]  # Truncate to seconds
                ))
        
        # Schedule update in main thread
        self.root.after(0, update)
    
    def update_mission_display(self):
        """Update the mission stack display"""
        def update():
            # Get mission stack summary
            summary = self.mission_stack.get_summary()
            
            # Update summary labels
            self.total_missions_var.set(str(summary['total_missions']))
            self.total_kills_var.set(f"{summary['total_current_kills']}/{summary['total_initial_kills']}")
            self.total_reward_var.set(f"{summary['total_reward']:,} CR")
            
            # Clear existing mission tree items
            for item in self.mission_tree.get_children():
                self.mission_tree.delete(item)
            
            # Add missions to treeview
            for target_faction, target_data in summary['target_factions'].items():
                for issuing_faction, faction_data in target_data['factions'].items():
                    for mission_name, mission in faction_data['missions'].items():
                        # Format expiry time
                        expiry = mission['expiry']
                        if expiry:
                            expiry = expiry[:16].replace('T', ' ')  # Format as YYYY-MM-DD HH:MM
                        
                        # Format wing status
                        wing = "Yes" if mission['wing'] else "No"
                        
                        self.mission_tree.insert('', tk.END, values=(
                            target_faction,
                            issuing_faction,
                            mission_name,
                            f"{mission['current_kill_count']}/{mission['initial_kill_count']}",
                            f"{mission['reward']:,}",
                            expiry,
                            wing
                        ))
        
        # Schedule update in main thread
        self.root.after(0, update)
    
    def log_message(self, message):
        """Add a message to the log display"""
        def update():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        # Schedule update in main thread
        self.root.after(0, update)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

    def update_mission_display(self):
        """Update the mission stack display"""
        def update():
            # Get mission stack summary
            summary = self.mission_stack.get_summary()
            
            # Get kill ratios and detailed breakdown
            kill_ratios = self.kill_ratio_calculator.calculate_ratios(self.mission_stack.missions)
            detailed_breakdown = self.kill_ratio_calculator.calculate_detailed_breakdown(self.mission_stack.missions)
            
            # Update summary labels
            self.total_missions_var.set(str(summary['total_missions']))
            self.total_kills_var.set(f"{summary['total_current_kills']}/{summary['total_initial_kills']}")
            self.total_reward_var.set(f"{summary['total_reward']:,} CR")
            
            # Clear existing mission tree items
            for item in self.mission_tree.get_children():
                self.mission_tree.delete(item)
            
            # Add missions to treeview
            for target_faction, target_data in summary['target_factions'].items():
                for issuing_faction, faction_data in target_data['factions'].items():
                    for mission_name, mission in faction_data['missions'].items():
                        # Format expiry time
                        expiry = mission['expiry']
                        if expiry:
                            expiry = expiry[:16].replace('T', ' ')  # Format as YYYY-MM-DD HH:MM
                        
                        # Format wing status
                        wing = "Yes" if mission['wing'] else "No"
                        
                        self.mission_tree.insert('', tk.END, values=(
                            target_faction,
                            issuing_faction,
                            mission_name,
                            f"{mission['current_kill_count']}/{mission['initial_kill_count']}",
                            f"{mission['reward']:,}",
                            expiry,
                            wing
                        ))
            
            # Update kill ratio display
            self.update_kill_ratio_display(kill_ratios, detailed_breakdown)
        
        # Schedule update in main thread
        self.root.after(0, update)
    
    def update_kill_ratio_display(self, kill_ratios, detailed_breakdown):
        """Update the kill ratio analysis tab"""
        # Clear existing ratio tree items
        for item in self.ratio_tree.get_children():
            self.ratio_tree.delete(item)
        
        # Clear existing breakdown tree items
        for item in self.breakdown_tree.get_children():
            self.breakdown_tree.delete(item)
        
        # Add kill ratios to ratio tree
        for target_faction, ratio in kill_ratios.items():
            breakdown = detailed_breakdown.get(target_faction, {})
            faction_count = breakdown.get('faction_count', 0)
            total_remaining = breakdown.get('total_remaining_kills', 0)
            
            # Color code the ratio
            ratio_display = f"{ratio:.4f}"
            if ratio >= 0.8:
                ratio_display = f"🟢 {ratio:.4f}"  # Green for high efficiency
            elif ratio >= 0.5:
                ratio_display = f"🟡 {ratio:.4f}"  # Yellow for medium efficiency
            else:
                ratio_display = f"🔴 {ratio:.4f}"  # Red for low efficiency
            
            self.ratio_tree.insert('', tk.END, values=(
                target_faction,
                faction_count,
                total_remaining,
                ratio_display
            ))
        
        # Add detailed breakdown
        for target_faction, breakdown in detailed_breakdown.items():
            faction_details = breakdown.get('faction_details', {})
            for issuing_faction, details in faction_details.items():
                self.breakdown_tree.insert('', tk.END, values=(
                    target_faction,
                    issuing_faction,
                    details.get('mission_count', 0),
                    details.get('remaining_kills', 0)
                ))

def create_sample_log_folder():
    """Create a sample log folder with log files for testing"""
    sample_folder = "sample_logs"
    os.makedirs(sample_folder, exist_ok=True)
    
    # Create sample massacre mission events
    sample_events = [
        {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "MissionAccepted",
            "Faction": "Military Gamers",
            "Name": "Mission_Massacre",
            "LocalisedName": "Kill Mizete Jet Society faction Pirates",
            "TargetType": "$MissionUtil_FactionTag_Pirate;",
            "TargetType_Localised": "Pirates",
            "TargetFaction": "Mizete Jet Society",
            "KillCount": 30,
            "DestinationSystem": "Mizete",
            "DestinationStation": "Porges Orbital",
            "Expiry": (datetime.now().replace(hour=23, minute=59, second=59)).isoformat() + "Z",
            "Wing": False,
            "Influence": "++",
            "Reputation": "++",
            "Reward": 40561668,
            "MissionID": 1037083037
        },
        {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "MissionAccepted",
            "Faction": "Gatorma Labour",
            "Name": "Mission_MassacreWing",
            "LocalisedName": "Kill Mizete Jet Society faction Pirates",
            "TargetType": "$MissionUtil_FactionTag_Pirate;",
            "TargetType_Localised": "Pirates",
            "TargetFaction": "Mizete Jet Society",
            "KillCount": 45,
            "DestinationSystem": "Mizete",
            "DestinationStation": "Sakers Station",
            "Expiry": (datetime.now().replace(hour=23, minute=59, second=59)).isoformat() + "Z",
            "Wing": True,
            "Influence": "++",
            "Reputation": "++",
            "Reward": 16295619,
            "MissionID": 1037083079
        },
        {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "MissionAccepted",
            "Faction": "Military Gamers",
            "Name": "Mission_Massacre",
            "LocalisedName": "Kill Brothers of Nijoten faction Pirates",
            "TargetType": "$MissionUtil_FactionTag_Pirate;",
            "TargetType_Localised": "Pirates",
            "TargetFaction": "Brothers of Nijoten",
            "KillCount": 25,
            "DestinationSystem": "Nijoten",
            "DestinationStation": "Maury Beacon",
            "Expiry": (datetime.now().replace(hour=23, minute=59, second=59)).isoformat() + "Z",
            "Wing": False,
            "Influence": "++",
            "Reputation": "++",
            "Reward": 30106172,
            "MissionID": 1037083115
        }
    ]
    
    log_filename = f"Journal.24{datetime.now().strftime('%m%d.%H%M%S')}.01.log"
    log_path = os.path.join(sample_folder, log_filename)
    
    with open(log_path, "w") as f:
        for event in sample_events:
            f.write(json.dumps(event) + "\n")
    
    print(f"Sample log folder created: {sample_folder}")
    print(f"Sample log file: {log_filename}")
    return sample_folder

if __name__ == "__main__":
    # Create a sample log folder for testing (remove this in production)
    sample_folder = create_sample_log_folder()
    
    # Start the application
    app = GameLogMonitor()
    # Pre-populate the sample folder path for testing
    app.folder_path_var.set(sample_folder)
    app.log_folder = sample_folder
    app.run()