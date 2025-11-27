"""
Mission Stack Manager for Elite Dangerous massacre mission tracking.
Tracks and manages massacre missions by target faction and issuing faction.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from kill_ratio import KillRatioCalculator

class MissionData:
    """Represents a single massacre mission and its kill tracking"""
    
    def __init__(self, mission_data: Dict[str, Any]):
        self.mission_id = mission_data.get('MissionID', 0)
        self.name = mission_data.get('Name', '')
        self.localised_name = mission_data.get('LocalisedName', '')
        self.faction = mission_data.get('Faction', '')
        self.target_faction = mission_data.get('TargetFaction', '')
        self.initial_kill_count = mission_data.get('KillCount', 0)
        self.current_kill_count = mission_data.get('KillCount', 0)
        self.reward = mission_data.get('Reward', 0)
        self.expiry = mission_data.get('Expiry', '')
        self.wing = mission_data.get('Wing', False)
        self.destination_system = mission_data.get('DestinationSystem', '')
        self.destination_station = mission_data.get('DestinationStation', '')
        self.timestamp = mission_data.get('timestamp', '')
        
        # Parse expiry to datetime if available
        self.expiry_datetime = None
        if self.expiry:
            try:
                if self.expiry.endswith('Z'):
                    self.expiry = self.expiry[:-1]
                self.expiry_datetime = datetime.fromisoformat(self.expiry)
            except (ValueError, TypeError):
                pass
    
    def update_kill_count(self, new_kill_count: int):
        """Update the current kill count for this mission"""
        self.current_kill_count = new_kill_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mission data to dictionary"""
        return {
            'mission_id': self.mission_id,
            'name': self.name,
            'localised_name': self.localised_name,
            'faction': self.faction,
            'target_faction': self.target_faction,
            'initial_kill_count': self.initial_kill_count,
            'current_kill_count': self.current_kill_count,
            'reward': self.reward,
            'expiry': self.expiry,
            'wing': self.wing,
            'destination_system': self.destination_system,
            'destination_station': self.destination_station,
            'timestamp': self.timestamp
        }
    
    def __str__(self) -> str:
        return (f"Mission {self.mission_id}: {self.localised_name} | "
                f"Kills: {self.current_kill_count}/{self.initial_kill_count} | "
                f"Reward: {self.reward:,}")

class FactionMissions:
    """Manages missions for a specific issuing faction"""
    
    def __init__(self, faction_name: str):
        self.faction_name = faction_name
        self.missions: Dict[str, MissionData] = {}  # key: localised_name, value: MissionData
        self.total_initial_kills = 0
        self.total_current_kills = 0
        self.total_reward = 0
    
    def add_mission(self, mission_data: MissionData):
        """Add a mission to this faction's tracking"""
        key = mission_data.localised_name
        
        if key in self.missions:
            # Update existing mission
            existing = self.missions[key]
            existing.update_kill_count(mission_data.current_kill_count)
        else:
            # Add new mission
            self.missions[key] = mission_data
            self.total_initial_kills += mission_data.initial_kill_count
            self.total_current_kills += mission_data.current_kill_count
            self.total_reward += mission_data.reward
    
    def update_mission_kills(self, mission_id: int, new_kill_count: int) -> bool:
        """Update kill count for a specific mission by mission ID"""
        for mission in self.missions.values():
            if mission.mission_id == mission_id:
                old_kill_count = mission.current_kill_count
                mission.update_kill_count(new_kill_count)
                self.total_current_kills += (new_kill_count - old_kill_count)
                return True
        return False
    
    def remove_mission(self, mission_id: int) -> bool:
        """Remove a mission by mission ID"""
        for key, mission in list(self.missions.items()):
            if mission.mission_id == mission_id:
                self.total_initial_kills -= mission.initial_kill_count
                self.total_current_kills -= mission.current_kill_count
                self.total_reward -= mission.reward
                del self.missions[key]
                return True
        return False
    
    def get_progress_percentage(self) -> float:
        """Get overall progress percentage for this faction's missions"""
        if self.total_initial_kills == 0:
            return 0.0
        return (self.total_current_kills / self.total_initial_kills) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert faction missions to dictionary"""
        return {
            'faction_name': self.faction_name,
            'missions': {name: mission.to_dict() for name, mission in self.missions.items()},
            'total_initial_kills': self.total_initial_kills,
            'total_current_kills': self.total_current_kills,
            'total_reward': self.total_reward,
            'progress_percentage': self.get_progress_percentage()
        }

class MissionStack:
    """
    Main mission stack manager that organizes missions by target faction and issuing faction
    """
    
    def __init__(self):
        # Structure: target_faction -> issuing_faction -> FactionMissions
        self.missions: Dict[str, Dict[str, FactionMissions]] = {}
        self.logger = logging.getLogger(__name__)
    
    def process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process a mission event and update the mission stack
        Returns True if the event was processed, False otherwise
        """
        try:
            event_type = event_data.get('event', '')
            
            if event_type == 'MissionAccepted':
                return self._handle_mission_accepted(event_data)
            elif event_type == 'MissionCompleted':
                return self._handle_mission_completed(event_data)
            elif event_type == 'MissionFailed':
                return self._handle_mission_failed(event_data)
            elif event_type == 'MissionAbandoned':
                return self._handle_mission_abandoned(event_data)
            # Add other mission-related events as needed
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing mission event: {e}")
            return False
    
    def _handle_mission_accepted(self, event_data: Dict[str, Any]) -> bool:
        """Handle MissionAccepted event"""
        # Only process massacre missions
        name = event_data.get('Name', '')
        if 'Mission_Massacre' not in name:
            return False
        
        mission_data = MissionData(event_data)
        
        target_faction = mission_data.target_faction
        issuing_faction = mission_data.faction
        
        # Initialize target faction if needed
        if target_faction not in self.missions:
            self.missions[target_faction] = {}
        
        # Initialize issuing faction if needed
        if issuing_faction not in self.missions[target_faction]:
            self.missions[target_faction][issuing_faction] = FactionMissions(issuing_faction)
        
        # Add the mission
        self.missions[target_faction][issuing_faction].add_mission(mission_data)
        
        self.logger.info(f"Added massacre mission: {mission_data.localised_name} "
                        f"for {target_faction} from {issuing_faction}")
        return True
    
    def _handle_mission_completed(self, event_data: Dict[str, Any]) -> bool:
        """Handle MissionCompleted event - remove completed mission"""
        mission_id = event_data.get('MissionID', 0)
        return self._remove_mission_by_id(mission_id, "completed")
    
    def _handle_mission_failed(self, event_data: Dict[str, Any]) -> bool:
        """Handle MissionFailed event - remove failed mission"""
        mission_id = event_data.get('MissionID', 0)
        return self._remove_mission_by_id(mission_id, "failed")
    
    def _handle_mission_abandoned(self, event_data: Dict[str, Any]) -> bool:
        """Handle MissionAbandoned event - remove abandoned mission"""
        mission_id = event_data.get('MissionID', 0)
        return self._remove_mission_by_id(mission_id, "abandoned")
    
    def _remove_mission_by_id(self, mission_id: int, reason: str) -> bool:
        """Remove a mission by its ID from the stack"""
        for target_faction, factions in list(self.missions.items()):
            for faction_name, faction_missions in list(factions.items()):
                if faction_missions.remove_mission(mission_id):
                    self.logger.info(f"Removed mission {mission_id} ({reason}) "
                                  f"from {faction_name} for {target_faction}")
                    
                    # Clean up empty factions
                    if not faction_missions.missions:
                        del self.missions[target_faction][faction_name]
                    
                    # Clean up empty target factions
                    if not self.missions[target_faction]:
                        del self.missions[target_faction]
                    
                    return True
        return False
    
    def update_mission_kills(self, mission_id: int, new_kill_count: int) -> bool:
        """Update kill count for a specific mission"""
        for target_faction, factions in self.missions.items():
            for faction_name, faction_missions in factions.items():
                if faction_missions.update_mission_kills(mission_id, new_kill_count):
                    self.logger.info(f"Updated mission {mission_id} kills to {new_kill_count}")
                    return True
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all missions in the stack"""
        summary = {
            'target_factions': {},
            'total_initial_kills': 0,
            'total_current_kills': 0,
            'total_reward': 0,
            'total_missions': 0
        }
        
        for target_faction, factions in self.missions.items():
            target_summary = {
                'factions': {},
                'total_initial_kills': 0,
                'total_current_kills': 0,
                'total_reward': 0,
                'total_missions': 0
            }
            
            for faction_name, faction_missions in factions.items():
                faction_data = faction_missions.to_dict()
                target_summary['factions'][faction_name] = faction_data
                target_summary['total_initial_kills'] += faction_data['total_initial_kills']
                target_summary['total_current_kills'] += faction_data['total_current_kills']
                target_summary['total_reward'] += faction_data['total_reward']
                target_summary['total_missions'] += len(faction_data['missions'])
            
            summary['target_factions'][target_faction] = target_summary
            summary['total_initial_kills'] += target_summary['total_initial_kills']
            summary['total_current_kills'] += target_summary['total_current_kills']
            summary['total_reward'] += target_summary['total_reward']
            summary['total_missions'] += target_summary['total_missions']
        
        return summary
    
    def get_target_factions(self) -> List[str]:
        """Get list of all target factions being tracked"""
        return list(self.missions.keys())
    
    def get_issuing_factions(self, target_faction: str) -> List[str]:
        """Get list of issuing factions for a target faction"""
        if target_faction in self.missions:
            return list(self.missions[target_faction].keys())
        return []
    
    def clear(self):
        """Clear all missions from the stack"""
        self.missions.clear()
        self.logger.info("Mission stack cleared")
    
    def __str__(self) -> str:
        summary = self.get_summary()
        return (f"MissionStack: {summary['total_missions']} missions, "
                f"{summary['total_current_kills']}/{summary['total_initial_kills']} kills, "
                f"{summary['total_reward']:,} CR total reward")
    
    def get_kill_ratios(self) -> Dict[str, float]:
        """Calculate kill ratios for all target factions in the stack"""
        calculator = KillRatioCalculator()
        return calculator.calculate_ratios(self.missions)
    
    def get_detailed_kill_breakdown(self) -> Dict[str, Dict]:
        """Get detailed kill ratio breakdown for all target factions"""
        calculator = KillRatioCalculator()
        return calculator.calculate_detailed_breakdown(self.missions)