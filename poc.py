import datetime
import time
from typing import Dict, Tuple, Any

# --- 1. Core Temporal Model ---
# Based on our discussion of natural human temporal landmarks.
# This dictionary maps a retelling style to a time window in seconds.
TEMPORAL_INTERVALS: Dict[str, Tuple[float, float]] = {
    "immediate": (0, 2 * 3600),  # 0-2 hours
    "recent": (2 * 3600, 2 * 24 * 3600),  # 2 hours - 2 days
    "last_week": (2 * 24 * 3600, 10 * 24 * 3600),  # 2-10 days
    "recently": (10 * 24 * 3600, 8 * 7 * 24 * 3600),  # 10 days - 8 weeks
    "some_time_ago": (8 * 7 * 24 * 3600, float('inf'))  # 8+ weeks
}

def get_temporal_style(elapsed_seconds: float) -> str:
    """Determines the appropriate retelling style based on elapsed time."""
    for style, (min_time, max_time) in TEMPORAL_INTERVALS.items():
        if min_time <= elapsed_seconds < max_time:
            return style
    return "some_time_ago"

# --- 2. The Train-Pause Story (Our PoC Scenario) ---
# Here we define the core "anchor" fact and the different "flux" versions
# of the story for each temporal style.
TRAIN_STORY_DATA: Dict[str, str] = {
    "anchor": "On a morning train to Amsterdam, I was reading about AI when there was a 15-minute delay, which made me feel frustrated about an important meeting.",
    "immediate": "God, I'm still annoyed about this morning's train. The 8:47 to Amsterdam - you know, the one I always take? We're sitting there, I'm trying to read this fascinating article about AI bias in hiring systems, when suddenly the conductor comes on: 'Ladies and gentlemen, due to a signal failure ahead, we'll have a 15-minute delay.' Fifteen minutes! I kept checking my phone, thinking about my 10 AM meeting with the board. My coffee was getting cold, and I could feel that familiar knot in my stomach...",
    "recent": "Yesterday's commute was such a mess. I was on my usual morning train, reading something interesting - I think it was about AI ethics? Anyway, we got delayed for like fifteen minutes because of some signal problem. Really threw off my whole morning schedule. I hate how these little disruptions can completely derail your day, you know?",
    "last_week": "Last week I had one of those typical commuter nightmares - train delays right when you need to be somewhere important. I was trying to read, but couldn't focus because we were just sitting there waiting. It's funny how these small frustrations can stick with you longer than they should.",
    "recently": "I was thinking about how unpredictable public transport can be. Recently I had this experience where a simple delay reminded me how little control we actually have over our daily routines. I was reading something thought-provoking at the time, which made the contrast even more stark - here I am contemplating big ideas while being held hostage by a signal failure.",
    "some_time_ago": "I remember once being on a train that got delayed, and it struck me how these moments of forced stillness can actually be gifts. There I was, irritated about being late, but also deeply absorbed in what I was reading. It made me realize how rarely we just... sit with our thoughts anymore."
}

# --- 3. Simple Memory System ---

class Memory:
    """A simple class to represent a single memory event."""
    def __init__(self, data: Dict[str, str]):
        self.timestamp: float = time.time()
        self.data: Dict[str, str] = data
        self.access_count: int = 0

    def retell(self) -> str:
        """Retells the memory using the appropriate temporal style."""
        self.access_count += 1
        elapsed_seconds = time.time() - self.timestamp
        style = get_temporal_style(elapsed_seconds)
        
        print(f"--- Retelling (style: {style}, {self.access_count} access(es)) ---")
        return self.data.get(style, self.data["some_time_ago"])

class MemorySystem:
    """A simple system to hold and manage memories."""
    def __init__(self):
        self.memories: list[Memory] = []

    def add_memory(self, data: Dict[str, str]):
        print("\n=== New Memory Created ===")
        memory = Memory(data)
        self.memories.append(memory)
        return memory

# --- 4. Simulation ---

def run_simulation():
    """Runs a simulation of memory creation and retelling over time."""
    virtual_human_memory = MemorySystem()

    # Create the initial memory of the train event
    train_memory = virtual_human_memory.add_memory(TRAIN_STORY_DATA)
    
    # --- Simulate retelling at different time intervals ---
    
    # 1. Immediate retelling (a few seconds later)
    print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(train_memory.retell())

    # 2. Recent retelling (simulating 1 day later)
    print("\n...simulating 1 day passing...")
    train_memory.timestamp -= 24 * 3600  # Manually age the memory
    print(f"Time: {(datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')}")
    print(train_memory.retell())

    # 3. Last Week retelling (simulating 7 days later)
    print("\n...simulating 6 more days passing...")
    train_memory.timestamp -= 6 * 24 * 3600 # Manually age it further
    print(f"Time: {(datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')}")
    print(train_memory.retell())

    # 4. Some Time Ago retelling (simulating 3 months later)
    print("\n...simulating ~3 months passing...")
    train_memory.timestamp -= 90 * 24 * 3600 # Manually age it further
    print(f"Time: {(datetime.datetime.now() - datetime.timedelta(days=97)).strftime('%Y-%m-%d %H:%M:%S')}")
    print(train_memory.retell())


if __name__ == "__main__":
    run_simulation()
