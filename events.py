"""
Event classes for Elite Dangerous journal events.
Handles parsing and structuring of Mission-related events.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

class MissionEvent:
    """Base class for all mission-related events"""
    
    def __init__(self, timestamp: str, event: str):
        self.timestamp = timestamp
        self.event = event
        self.datetime = self._parse_timestamp(timestamp)
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO format timestamp string to datetime object"""
        try:
            # Remove the 'Z' and parse as ISO format
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1]
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return datetime.now()
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> Optional['MissionEvent']:
        """Factory method to create appropriate mission event from JSON data"""
        event_type = json_data.get('event', '')
        
        if event_type == 'Missions':
            return MissionsEvent.from_json(json_data)
        elif event_type == 'MissionAccepted':
            return MissionAcceptedEvent.from_json(json_data)
        elif event_type == 'MissionCompleted':
            return MissionCompletedEvent.from_json(json_data)
        elif event_type == 'MissionFailed':
            return MissionFailedEvent.from_json(json_data)
        elif event_type == 'MissionAbandoned':
            return MissionAbandonedEvent.from_json(json_data)
        else:
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation"""
        return {
            'timestamp': self.timestamp,
            'event': self.event,
            'datetime': self.datetime.isoformat()
        }
    
    def __str__(self) -> str:
        return f"{self.event} at {self.timestamp}"


class MissionsEvent(MissionEvent):
    """
    Represents the current state of all missions
    This event shows active, failed, and completed missions
    """
    
    def __init__(self, timestamp: str, active: List[Dict], failed: List[Dict], complete: List[Dict]):
        super().__init__(timestamp, "Missions")
        self.active = active or []
        self.failed = failed or []
        self.complete = complete or []
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'MissionsEvent':
        """Create MissionsEvent from JSON data"""
        return cls(
            timestamp=json_data.get('timestamp', ''),
            active=json_data.get('Active', []),
            failed=json_data.get('Failed', []),
            complete=json_data.get('Complete', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with mission arrays"""
        data = super().to_dict()
        data.update({
            'Active': self.active,
            'Failed': self.failed,
            'Complete': self.complete
        })
        return data
    
    def __str__(self) -> str:
        return f"Missions: {len(self.active)} active, {len(self.failed)} failed, {len(self.complete)} complete"


class MissionAcceptedEvent(MissionEvent):
    """
    Represents when a mission is accepted
    Contains all mission details and requirements
    """
    
    def __init__(self, timestamp: str, faction: str, name: str, localised_name: str, 
                 target_type: str, target_type_localised: str, target_faction: str,
                 kill_count: int, destination_system: str, destination_station: str,
                 expiry: str, wing: bool, influence: str, reputation: str,
                 reward: int, mission_id: int, **kwargs):
        super().__init__(timestamp, "MissionAccepted")
        self.faction = faction
        self.name = name
        self.localised_name = localised_name
        self.target_type = target_type
        self.target_type_localised = target_type_localised
        self.target_faction = target_faction
        self.kill_count = kill_count
        self.destination_system = destination_system
        self.destination_station = destination_station
        self.expiry = expiry
        self.expiry_datetime = self._parse_timestamp(expiry) if expiry else None
        self.wing = wing
        self.influence = influence
        self.reputation = reputation
        self.reward = reward
        self.mission_id = mission_id
        
        # Store any additional fields that might be present
        self.extra_data = kwargs
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'MissionAcceptedEvent':
        """Create MissionAcceptedEvent from JSON data"""
        return cls(
            timestamp=json_data.get('timestamp', ''),
            faction=json_data.get('Faction', ''),
            name=json_data.get('Name', ''),
            localised_name=json_data.get('LocalisedName', ''),
            target_type=json_data.get('TargetType', ''),
            target_type_localised=json_data.get('TargetType_Localised', ''),
            target_faction=json_data.get('TargetFaction', ''),
            kill_count=json_data.get('KillCount', 0),
            destination_system=json_data.get('DestinationSystem', ''),
            destination_station=json_data.get('DestinationStation', ''),
            expiry=json_data.get('Expiry', ''),
            wing=json_data.get('Wing', False),
            influence=json_data.get('Influence', ''),
            reputation=json_data.get('Reputation', ''),
            reward=json_data.get('Reward', 0),
            mission_id=json_data.get('MissionID', 0),
            **{k: v for k, v in json_data.items() 
               if k not in ['timestamp', 'event', 'Faction', 'Name', 'LocalisedName', 
                           'TargetType', 'TargetType_Localised', 'TargetFaction', 
                           'KillCount', 'DestinationSystem', 'DestinationStation', 
                           'Expiry', 'Wing', 'Influence', 'Reputation', 'Reward', 'MissionID']}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = super().to_dict()
        data.update({
            'Faction': self.faction,
            'Name': self.name,
            'LocalisedName': self.localised_name,
            'TargetType': self.target_type,
            'TargetType_Localised': self.target_type_localised,
            'TargetFaction': self.target_faction,
            'KillCount': self.kill_count,
            'DestinationSystem': self.destination_system,
            'DestinationStation': self.destination_station,
            'Expiry': self.expiry,
            'Wing': self.wing,
            'Influence': self.influence,
            'Reputation': self.reputation,
            'Reward': self.reward,
            'MissionID': self.mission_id
        })
        data.update(self.extra_data)
        return data
    
    def __str__(self) -> str:
        mission_type = "Wing" if self.wing else "Solo"
        return (f"Mission Accepted: {self.localised_name} | "
                f"Target: {self.target_faction} | "
                f"Kills: {self.kill_count} | "
                f"Reward: {self.reward:,} CR | "
                f"Type: {mission_type}")


class MissionCompletedEvent(MissionEvent):
    """Represents when a mission is completed"""
    
    def __init__(self, timestamp: str, faction: str, name: str, mission_id: int, 
                 reward: int, **kwargs):
        super().__init__(timestamp, "MissionCompleted")
        self.faction = faction
        self.name = name
        self.mission_id = mission_id
        self.reward = reward
        self.extra_data = kwargs
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'MissionCompletedEvent':
        """Create MissionCompletedEvent from JSON data"""
        return cls(
            timestamp=json_data.get('timestamp', ''),
            faction=json_data.get('Faction', ''),
            name=json_data.get('Name', ''),
            mission_id=json_data.get('MissionID', 0),
            reward=json_data.get('Reward', 0),
            **{k: v for k, v in json_data.items() 
               if k not in ['timestamp', 'event', 'Faction', 'Name', 'MissionID', 'Reward']}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = super().to_dict()
        data.update({
            'Faction': self.faction,
            'Name': self.name,
            'MissionID': self.mission_id,
            'Reward': self.reward
        })
        data.update(self.extra_data)
        return data
    
    def __str__(self) -> str:
        return f"Mission Completed: {self.name} | Reward: {self.reward:,} CR"


class MissionFailedEvent(MissionEvent):
    """Represents when a mission fails"""
    
    def __init__(self, timestamp: str, name: str, mission_id: int, **kwargs):
        super().__init__(timestamp, "MissionFailed")
        self.name = name
        self.mission_id = mission_id
        self.extra_data = kwargs
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'MissionFailedEvent':
        """Create MissionFailedEvent from JSON data"""
        return cls(
            timestamp=json_data.get('timestamp', ''),
            name=json_data.get('Name', ''),
            mission_id=json_data.get('MissionID', 0),
            **{k: v for k, v in json_data.items() 
               if k not in ['timestamp', 'event', 'Name', 'MissionID']}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = super().to_dict()
        data.update({
            'Name': self.name,
            'MissionID': self.mission_id
        })
        data.update(self.extra_data)
        return data
    
    def __str__(self) -> str:
        return f"Mission Failed: {self.name}"


class MissionAbandonedEvent(MissionEvent):
    """Represents when a mission is abandoned"""
    
    def __init__(self, timestamp: str, name: str, mission_id: int, **kwargs):
        super().__init__(timestamp, "MissionAbandoned")
        self.name = name
        self.mission_id = mission_id
        self.extra_data = kwargs
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'MissionAbandonedEvent':
        """Create MissionAbandonedEvent from JSON data"""
        return cls(
            timestamp=json_data.get('timestamp', ''),
            name=json_data.get('Name', ''),
            mission_id=json_data.get('MissionID', 0),
            **{k: v for k, v in json_data.items() 
               if k not in ['timestamp', 'event', 'Name', 'MissionID']}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = super().to_dict()
        data.update({
            'Name': self.name,
            'MissionID': self.mission_id
        })
        data.update(self.extra_data)
        return data
    
    def __str__(self) -> str:
        return f"Mission Abandoned: {self.name}"


# Utility functions for working with mission events
def parse_mission_event(json_data: Dict[str, Any]) -> Optional[MissionEvent]:
    """Parse JSON data and return appropriate MissionEvent object"""
    return MissionEvent.from_json(json_data)

def is_mission_event(json_data: Dict[str, Any]) -> bool:
    """Check if JSON data represents a mission event"""
    event_type = json_data.get('event', '')
    return event_type.startswith('Mission') or event_type == 'Missions'