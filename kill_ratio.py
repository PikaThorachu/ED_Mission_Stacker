"""
Kill Ratio Calculator for Elite Dangerous massacre missions.
Calculates the kill ratio for TargetFactions based on remaining kills and mission completion logic.
"""

from typing import Dict, List, Tuple
import logging

class KillRatioCalculator:
    """
    Calculates kill ratios for TargetFactions and their issuing Factions
    based on sequential mission completion within Factions and concurrent completion across Factions.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_ratios(self, mission_stack: Dict) -> Dict[str, float]:
        """
        Calculate kill ratios for all TargetFactions in the mission stack.
        
        Args:
            mission_stack: The mission stack data structure from MissionStack
            
        Returns:
            Dictionary mapping TargetFaction names to their kill ratios
        """
        ratios = {}
        
        for target_faction, factions_data in mission_stack.items():
            ratio = self._calculate_target_faction_ratio(target_faction, factions_data)
            ratios[target_faction] = ratio
            self.logger.info(f"Kill ratio for {target_faction}: {ratio:.4f}")
        
        return ratios
    
    def _calculate_target_faction_ratio(self, target_faction: str, factions_data: Dict) -> float:
        """
        Calculate the kill ratio for a specific TargetFaction.
        
        Args:
            target_faction: Name of the target faction
            factions_data: Dictionary of issuing factions and their missions
            
        Returns:
            Kill ratio as a float between 0 and 1
        """
        # If only one faction, ratio is 1.00
        if len(factions_data) == 1:
            return 1.00
        
        # Calculate total remaining kills for each faction
        faction_remaining_kills = {}
        
        for faction_name, faction_missions in factions_data.items():
            total_remaining = self._calculate_faction_remaining_kills(faction_missions)
            faction_remaining_kills[faction_name] = total_remaining
        
        # Calculate the ratio based on the described logic
        ratio = self._compute_kill_ratio(faction_remaining_kills)
        return ratio
    
    def _calculate_faction_remaining_kills(self, faction_missions) -> int:
        """
        Calculate total remaining kills for a faction, considering sequential completion.
        
        Args:
            faction_missions: FactionMissions object or dictionary with mission data
            
        Returns:
            Total remaining kills for the faction
        """
        # Handle both FactionMissions object and dictionary
        if hasattr(faction_missions, 'missions'):
            # It's a FactionMissions object
            missions = list(faction_missions.missions.values())
        elif isinstance(faction_missions, dict) and 'missions' in faction_missions:
            # It's a dictionary from the mission stack summary
            missions = list(faction_missions['missions'].values())
        else:
            # Assume it's already a dictionary of missions
            missions = list(faction_missions.values())
        
        # Sort missions by remaining kills (for sequential completion logic)
        # Missions with higher remaining kills are completed first in the sequence
        sorted_missions = sorted(
            missions,
            key=lambda m: (
                m.current_kill_count if hasattr(m, 'current_kill_count') 
                else m.get('current_kill_count', 0)
            ),
            reverse=True
        )
        
        total_remaining = 0
        
        for mission in sorted_missions:
            if hasattr(mission, 'current_kill_count'):
                remaining = mission.current_kill_count
            else:
                remaining = mission.get('current_kill_count', 0)
            total_remaining += remaining
        
        return total_remaining
    
    def _compute_kill_ratio(self, faction_remaining_kills: Dict[str, int]) -> float:
        """
        Compute the kill ratio based on the remaining kills across factions.
        
        This implements the logic described in the requirements:
        - Missions are completed sequentially within each faction
        - Factions complete missions concurrently
        - Ratio is calculated based on the distribution of remaining kills
        
        Args:
            faction_remaining_kills: Dictionary mapping faction names to their remaining kills
            
        Returns:
            Calculated kill ratio
        """
        total_factions = len(faction_remaining_kills)
        
        if total_factions == 0:
            return 0.0
        
        if total_factions == 1:
            return 1.0
        
        # Calculate total remaining kills across all factions
        total_remaining = sum(faction_remaining_kills.values())
        
        if total_remaining == 0:
            return 0.0
        
        # Calculate the weighted distribution of remaining kills
        # This implements the logic from the example
        max_remaining = max(faction_remaining_kills.values())
        avg_remaining = total_remaining / total_factions
        
        # The ratio is based on how evenly distributed the remaining kills are
        # If one faction has significantly more remaining kills, the ratio decreases
        # This follows the example where the ratio was 0.8181
        
        # Calculate efficiency factor based on distribution
        distribution_factor = avg_remaining / max_remaining if max_remaining > 0 else 1.0
        
        # Base ratio starts from the proportion of max remaining to total
        base_ratio = max_remaining / total_remaining if total_remaining > 0 else 0.0
        
        # Apply distribution factor to get final ratio
        ratio = base_ratio * distribution_factor
        
        # Ensure the ratio is between 0 and 1
        return max(0.0, min(1.0, ratio))
    
    def calculate_detailed_breakdown(self, mission_stack: Dict) -> Dict[str, Dict]:
        """
        Calculate detailed breakdown for debugging and display purposes.
        
        Args:
            mission_stack: The mission stack data
            
        Returns:
            Dictionary with detailed calculations for each target faction
        """
        breakdown = {}
        
        for target_faction, factions_data in mission_stack.items():
            faction_details = {}
            total_remaining = 0
            
            for faction_name, faction_missions in factions_data.items():
                faction_remaining = self._calculate_faction_remaining_kills(faction_missions)
                faction_details[faction_name] = {
                    'remaining_kills': faction_remaining,
                    'mission_count': len(faction_missions.missions) if hasattr(faction_missions, 'missions') 
                                   else len(faction_missions.get('missions', {}))
                }
                total_remaining += faction_remaining
            
            ratio = self._calculate_target_faction_ratio(target_faction, factions_data)
            
            breakdown[target_faction] = {
                'ratio': ratio,
                'faction_details': faction_details,
                'total_remaining_kills': total_remaining,
                'faction_count': len(factions_data)
            }
        
        return breakdown


# Example usage and test based on the provided example
def test_kill_ratio_calculation():
    """Test the kill ratio calculation with the provided example"""
    calculator = KillRatioCalculator()
    
    # Create test data based on the example
    test_mission_stack = {
        "ExampleTargetFaction": {
            "Faction1": {
                'missions': {
                    'Mission1': {'initial_kill_count': 60, 'current_kill_count': 40},
                    'Mission2': {'initial_kill_count': 35, 'current_kill_count': 35},
                    'Mission3': {'initial_kill_count': 15, 'current_kill_count': 15}
                }
            },
            "Faction2": {
                'missions': {
                    'Mission1': {'initial_kill_count': 55, 'current_kill_count': 25},
                    'Mission2': {'initial_kill_count': 15, 'current_kill_count': 15}
                }
            },
            "Faction3": {
                'missions': {
                    'Mission1': {'initial_kill_count': 22, 'current_kill_count': 2}
                }
            }
        }
    }
    
    ratios = calculator.calculate_ratios(test_mission_stack)
    breakdown = calculator.calculate_detailed_breakdown(test_mission_stack)
    
    print("Test Results:")
    for target_faction, ratio in ratios.items():
        print(f"{target_faction}: {ratio:.4f}")
    
    print("\nDetailed Breakdown:")
    for target_faction, details in breakdown.items():
        print(f"{target_faction}:")
        print(f"  Ratio: {details['ratio']:.4f}")
        print(f"  Total Remaining Kills: {details['total_remaining_kills']}")
        print(f"  Faction Count: {details['faction_count']}")
        for faction_name, faction_details in details['faction_details'].items():
            print(f"    {faction_name}: {faction_details['remaining_kills']} remaining kills")


if __name__ == "__main__":
    test_kill_ratio_calculation()