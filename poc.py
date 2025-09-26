import datetime
import time
from typing import Dict, Tuple, Any
import litellm
import random

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

# --- 2. Sample Memories ---
# A list of tuples, each containing an "anchor" fact and its primary emotion.
MEMORIES_TO_CREATE = [
    ("On a morning train to Amsterdam, I was reading about AI when there was a 15-minute delay, which made me feel frustrated about an important meeting.", "frustration"),
    ("I was at a park when a friendly dog dropped its ball at my feet, wanting to play fetch. It was a moment of pure, unexpected joy.", "joy"),
    ("Walking home late one night, I saw what I thought was a weird shadow, but it turned out to be a peacock, fanning its tail in the moonlight. It was completely surreal and surprising.", "surprise")
]

def generate_story_variant(anchor: str, style: str, emotion: str) -> str:
    """Generates a story variant using an LLM."""
    
    prompt_map = {
        "immediate": f"You are retelling a memory where you felt intense {emotion}. Embody that feeling. Retell the story with vivid, immediate details, focusing on your feelings and sensory experiences. Use the present or very recent past tense. Keep it brief, just two or three sentences.",
        "recent": f"You are retelling a memory where you felt {emotion}. The intense emotion has faded, but it still colors the memory. Retell the story, focusing on what happened and its immediate consequences from that emotional perspective. Keep it brief, just two or three sentences.",
        "last_week": f"You are retelling a memory where the main feeling was {emotion}. The details are becoming fuzzier. Retell it as a general anecdote, colored by the memory of that {emotion}. Keep it brief, just two or three sentences.",
        "recently": f"You are retelling a memory where you felt {emotion}. The specific feelings are gone, and you've started to reflect on it. Retell the story in a more philosophical way, perhaps focusing on a lesson learned from feeling that way. Keep it brief, just two or three sentences.",
        "some_time_ago": f"You are retelling a distant memory where you once felt {emotion}. The feeling is now just a faint echo. Retell the story with a sense of nostalgia or detachment, colored by that distant emotion. Keep it brief, just two or three sentences."
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
        print(f"\n=== New Memory Created (Emotion: {emotion}) ===")
        memory = Memory(anchor, emotion)
        self.memories.append(memory)
        return memory
    
    def recall_random_memory(self) -> str:
        """Picks a random memory and retells it."""
        if not self.memories:
            return "I don't have any memories to share right now."
        
        chosen_memory = random.choice(self.memories)
        print(f"\n--- Recalling a memory (Anchor: '{chosen_memory.anchor[:40]}...') ---")
        return chosen_memory.retell()

# --- 4. Simulation ---

def run_simulation():
    """Runs a simulation of memory creation and retelling over time."""
    virtual_human_memory = MemorySystem()

    # --- Create a backlog of memories from the "past" ---
    print("--- Populating with past memories ---")
    
    # Frustrating memory from last week
    mem1 = virtual_human_memory.add_memory(MEMORIES_TO_CREATE[0][0], MEMORIES_TO_CREATE[0][1])
    mem1.timestamp -= 7 * 24 * 3600  # Age it by 1 week

    # Joyful memory from a month ago
    mem2 = virtual_human_memory.add_memory(MEMORIES_TO_CREATE[1][0], MEMORIES_TO_CREATE[1][1])
    mem2.timestamp -= 30 * 24 * 3600 # Age it by 30 days
    
    # Surprising memory from yesterday
    mem3 = virtual_human_memory.add_memory(MEMORIES_TO_CREATE[2][0], MEMORIES_TO_CREATE[2][1])
    mem3.timestamp -= 1 * 24 * 3600 # Age it by 1 day
    
    # --- Simulate a conversation by recalling memories randomly ---
    print("\n\n--- Starting conversation simulation ---")
    for i in range(3):
        print(f"\n--- Turn {i+1} ---")
        print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(virtual_human_memory.recall_random_memory())
        time.sleep(1) # a small pause between turns


if __name__ == "__main__":
    run_simulation()
