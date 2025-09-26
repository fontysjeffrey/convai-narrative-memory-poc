import datetime
import time
from typing import Dict, Tuple, Any
import litellm

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
# This is the core "anchor" fact and its primary emotion.
STORY_ANCHOR = "On a morning train to Amsterdam, I was reading about AI when there was a 15-minute delay, which made me feel frustrated about an important meeting."
STORY_EMOTION = "frustration"

def generate_story_variant(anchor: str, style: str, emotion: str) -> str:
    """Generates a story variant using an LLM."""
    
    prompt_map = {
        "immediate": f"The primary emotion you felt during this event was {emotion}. You are still feeling this emotion intensely. Retell the story with vivid, immediate details, focusing on your feelings and sensory experiences. Use the present or very recent past tense. Keep it brief, just two or three sentences.",
        "recent": f"The primary emotion you felt during this event was {emotion}. The memory is still clear, but the intense emotion has faded. Retell the story, focusing on what happened and its immediate consequences. Keep it brief, just two or three sentences.",
        "last_week": f"The primary emotion you felt during this event was {emotion}. The details are becoming fuzzier. Retell the story as a general anecdote, perhaps touching on the feeling of {emotion}. Keep it brief, just two or three sentences.",
        "recently": f"The primary emotion you felt during this event was {emotion}. The specific feelings are gone, and you've started to reflect on it. Retell the story in a more philosophical way, perhaps focusing on a lesson learned from feeling {emotion}. Keep it brief, just two or three sentences.",
        "some_time_ago": f"The primary emotion you felt during this event was {emotion}. It's now a distant memory. Retell the story with a sense of nostalgia or detachment, perhaps mentioning the faint echo of {emotion} that has stuck with you. Keep it brief, just two or three sentences."
    }

    system_prompt = prompt_map.get(style, prompt_map["some_time_ago"])
    
    try:
        response = litellm.completion(
            model="ollama/gpt-oss:latest", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the core memory: {anchor}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating story with LLM: {e}")
        # Fallback to a simple string if LLM fails
        return f"I remember a train delay... It was frustrating. ({style})"

# --- 3. Simple Memory System ---

class Memory:
    """A simple class to represent a single memory event."""
    def __init__(self, anchor: str, emotion: str):
        self.timestamp: float = time.time()
        self.anchor: str = anchor
        self.emotion: str = emotion
        self.access_count: int = 0

    def retell(self) -> str:
        """Retells the memory using the appropriate temporal style."""
        self.access_count += 1
        elapsed_seconds = time.time() - self.timestamp
        style = get_temporal_style(elapsed_seconds)
        
        print(f"--- Retelling (style: {style}, {self.access_count} access(es)) ---")
        return generate_story_variant(self.anchor, style, self.emotion)

class MemorySystem:
    """A simple system to hold and manage memories."""
    def __init__(self):
        self.memories: list[Memory] = []

    def add_memory(self, anchor: str, emotion: str):
        print("\n=== New Memory Created ===")
        memory = Memory(anchor, emotion)
        self.memories.append(memory)
        return memory

# --- 4. Simulation ---

def run_simulation():
    """Runs a simulation of memory creation and retelling over time."""
    virtual_human_memory = MemorySystem()

    # Create the initial memory of the train event
    train_memory = virtual_human_memory.add_memory(STORY_ANCHOR, STORY_EMOTION)
    
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
