#!/usr/bin/env python3
"""
Interactive Memory-Enhanced Chatbot Demo

Demonstrates the Kafka-based narrative memory system with:
- Real-time conversation storage as anchors
- Memory retrieval with time-based decay
- Transparent logging of memory operations
- Time manipulation for demonstrating forgetting curves
"""

import os
import sys
import json
import uuid
import time
import datetime as dt
from typing import Optional, List, Dict, Any
from confluent_kafka import Producer, Consumer

# Kafka configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")


# Colors for pretty terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"


class MemoryChatbot:
    def __init__(self):
        self.producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
        self.time_offset = dt.timedelta(0)  # For time manipulation
        self.conversation_history = []
        self.session_id = str(uuid.uuid4())[:8]

    def get_current_time(self) -> dt.datetime:
        """Get current time with any artificial offset applied."""
        return dt.datetime.now(dt.timezone.utc) + self.time_offset

    def colorize(self, text: str, color: str) -> str:
        """Add color to terminal output."""
        return f"{color}{text}{Colors.ENDC}"

    def log_memory_op(self, symbol: str, message: str, color: str = Colors.DIM):
        """Log a memory operation with visual flair."""
        print(f"{color}{symbol} {message}{Colors.ENDC}")

    def store_anchor(self, text: str, salience: float = 0.8) -> str:
        """Store a conversation turn as a memory anchor."""
        anchor_id = str(uuid.uuid4())
        now = self.get_current_time()

        anchor = {
            "anchor_id": anchor_id,
            "text": text,
            "stored_at": now.isoformat(),
            "meta": {"session": self.session_id, "type": "conversation"},
            "salience": salience,
        }

        self.producer.produce("anchors.write", json.dumps(anchor).encode("utf-8"))
        self.producer.flush()

        self.log_memory_op(
            "📝",
            f"Stored anchor: {anchor_id[:8]}... | salience: {salience:.1f}",
            Colors.DIM,
        )

        # Give the indexer a moment to process (indexer needs to embed + store in Qdrant)
        time.sleep(1.0)

        return anchor_id

    def request_recall(self, query: str, top_k: int = 5) -> Optional[Dict]:
        """Request memory recall and wait for response."""
        request_id = str(uuid.uuid4())
        now = self.get_current_time()

        request = {
            "request_id": request_id,
            "query": query,
            "now": now.isoformat(),
            "top_k": top_k,
        }

        # Subscribe to response topics BEFORE sending request
        recall_consumer = self._create_consumer("recall.response")
        retell_consumer = self._create_consumer("retell.response")

        # Give consumers time to fully subscribe and get partition assignment
        # This is critical - Kafka consumers need time to join the group and get assigned partitions
        time.sleep(1.0)

        # Now send the request
        self.producer.produce("recall.request", json.dumps(request).encode("utf-8"))
        self.producer.flush()

        self.log_memory_op("⏳", f"Querying memory (req: {request_id[:8]})", Colors.DIM)

        # Wait for recall.response
        recall_result = self._wait_for_response_with_consumer(
            recall_consumer, request_id, timeout=15.0
        )

        if not recall_result:
            self.log_memory_op(
                "⚠️", "No response from memory system (timeout)", Colors.WARNING
            )
            recall_consumer.close()
            retell_consumer.close()
            return None

        if not recall_result.get("beats"):
            self.log_memory_op("💭", "No relevant memories found", Colors.DIM)
            recall_consumer.close()
            retell_consumer.close()
            return None

        # Wait for retell.response
        retell_result = self._wait_for_response_with_consumer(
            retell_consumer, request_id, timeout=15.0
        )

        recall_consumer.close()
        retell_consumer.close()

        if not retell_result:
            self.log_memory_op(
                "⚠️", "Retelling timed out (using beats only)", Colors.DIM
            )

        return {
            "beats": recall_result.get("beats", []),
            "retelling": retell_result.get("retelling") if retell_result else None,
        }

    def _create_consumer(self, topic: str) -> Consumer:
        """Create and subscribe a consumer to a topic."""
        consumer = Consumer(
            {
                "bootstrap.servers": KAFKA_BOOTSTRAP,
                "group.id": f"chatbot-{self.session_id}-{uuid.uuid4()}",
                "auto.offset.reset": "earliest",  # Read from beginning to catch all messages
                "enable.auto.commit": False,
                "session.timeout.ms": 6000,
                "max.poll.interval.ms": 300000,
            }
        )
        consumer.subscribe([topic])
        # Force partition assignment
        consumer.poll(0.0)
        return consumer

    def _wait_for_response_with_consumer(
        self, consumer: Consumer, request_id: str, timeout: float = 15.0
    ) -> Optional[Dict]:
        """Wait for a specific message using an already-subscribed consumer."""
        deadline = time.time() + timeout
        messages_seen = 0

        try:
            while time.time() < deadline:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    print(
                        f"[chatbot] Kafka error: {msg.error()}",
                        file=sys.stderr,
                    )
                    continue

                messages_seen += 1
                payload = json.loads(msg.value().decode("utf-8"))
                msg_req_id = payload.get("request_id", "")

                if msg_req_id == request_id:
                    self.log_memory_op("✓", "Response received", Colors.OKGREEN)
                    return payload
        except Exception as e:
            print(f"[ERROR] Exception in wait_for_response: {e}", file=sys.stderr)

        return None

    def display_recall_info(self, recall_data: Dict):
        """Display transparent information about recalled memories."""
        beats = recall_data.get("beats", [])

        if not beats:
            self.log_memory_op("💭", "No relevant memories found", Colors.DIM)
            return

        avg_activation = sum(b.get("activation", 0) for b in beats) / len(beats)
        self.log_memory_op(
            "🔍",
            f"Recalled {len(beats)} memories | avg activation: {avg_activation:.2f}",
            Colors.OKCYAN,
        )

        for i, beat in enumerate(beats, 1):
            activation = beat.get("activation", 0)
            age = beat.get("perceived_age", "unknown")
            text_preview = beat.get("text", "")[:60]

            self.log_memory_op(
                f"💭",
                f'Beat {i}: "{text_preview}..." ({age}) | act: {activation:.2f}',
                Colors.DIM,
            )

    def chat_response(self, user_input: str) -> str:
        """Generate a response with memory-enhanced context."""
        # Store the user's message
        self.store_anchor(f"User said: {user_input}", salience=0.9)

        # Try to recall relevant memories (but not the message we just stored)
        try:
            recall_data = self.request_recall(user_input, top_k=5)
        except Exception as e:
            print(f"[ERROR] Exception in request_recall: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            recall_data = None

        if recall_data and recall_data.get("beats"):
            self.display_recall_info(recall_data)

            # If we have a retelling, use it as context for response
            retelling = recall_data.get("retelling")
            if retelling:
                # Simple response that acknowledges the memory
                response = self._generate_response_with_context(user_input, retelling)
            else:
                # Fall back to simple response with beat info
                beats = recall_data.get("beats", [])
                if beats:
                    response = (
                        f"I recall we discussed: {beats[0].get('text', '')[:80]}..."
                    )
                else:
                    response = self._generate_simple_response(user_input)
        else:
            self.log_memory_op("💭", "No memories recalled", Colors.DIM)
            response = self._generate_simple_response(user_input)

        # Store bot's response
        self.store_anchor(f"Bot said: {response}", salience=0.7)

        return response

    def _generate_response_with_context(
        self, user_input: str, memory_context: str
    ) -> str:
        """Generate a response using recalled memory context."""
        # Simple rule-based responses that incorporate memory
        lower_input = user_input.lower()

        if any(
            word in lower_input
            for word in ["remember", "recall", "happened", "tell me"]
        ):
            return memory_context

        # For other inputs, acknowledge and respond naturally
        return f"I remember our conversation. {memory_context}"

    def _generate_simple_response(self, user_input: str) -> str:
        """Generate a simple response without memory context."""
        lower_input = user_input.lower()

        greetings = ["hello", "hi", "hey", "greetings"]
        if any(g in lower_input for g in greetings):
            return "Hello! I'm a memory-enhanced chatbot. I'll remember our conversation and can recall it later with realistic time-based decay."

        questions = ["what", "how", "why", "when", "where", "who"]
        if any(q in lower_input for q in questions):
            return "That's an interesting question! I don't have much memory context yet, but I'm storing our conversation."

        return "I see. Tell me more, and I'll remember our discussion for future reference."

    def advance_time(self, days: int = 0, months: int = 0, years: int = 0):
        """Advance the simulated time forward."""
        delta = dt.timedelta(days=days + months * 30 + years * 365)
        self.time_offset += delta

        total_days = delta.days
        self.log_memory_op(
            "⏰",
            f"Time advanced by {total_days} days ({self._format_time_delta(delta)})",
            Colors.WARNING,
        )

    def reset_time(self):
        """Reset time to present."""
        self.time_offset = dt.timedelta(0)
        self.log_memory_op("⏰", "Time reset to present", Colors.OKGREEN)

    def _format_time_delta(self, delta: dt.timedelta) -> str:
        """Format a timedelta nicely."""
        days = delta.days
        if days < 7:
            return f"{days} days"
        elif days < 30:
            return f"{days // 7} weeks"
        elif days < 365:
            return f"{days // 30} months"
        else:
            return f"{days // 365} years"

    def show_help(self):
        """Display help information."""
        help_text = f"""
{self.colorize("Memory-Enhanced Chatbot Commands", Colors.BOLD + Colors.HEADER)}

{self.colorize("Chat Commands:", Colors.BOLD)}
  Just type normally to chat - your messages will be stored as memories!

{self.colorize("Time Manipulation:", Colors.BOLD)}
  /advance_time <days>d     - Advance time by days (e.g., /advance_time 30d)
  /advance_time <months>m   - Advance time by months (e.g., /advance_time 6m)
  /advance_time <years>y    - Advance time by years (e.g., /advance_time 1y)
  /reset_time               - Reset time to present

{self.colorize("Utility Commands:", Colors.BOLD)}
  /help                     - Show this help
  /clear                    - Clear screen
  /exit or /quit            - Exit chatbot

{self.colorize("Memory System Info:", Colors.BOLD)}
  📝 = Memory stored as anchor
  🔍 = Memories recalled from Qdrant
  💭 = Memory beat (individual recalled memory)
  ⏰ = Time manipulation

{self.colorize("Example Flow:", Colors.BOLD)}
  You: I'm working on narrative memory research at Fontys
  Bot: [stores memory] <response>
  You: /advance_time 90d
  Bot: [time advanced by 90 days]
  You: What was I working on?
  Bot: [recalls with decay] About 3 months ago, you mentioned...
"""
        print(help_text)

    def print_banner(self):
        """Print a welcome banner."""
        banner = f"""
{self.colorize("╔════════════════════════════════════════════════════════════╗", Colors.HEADER)}
{self.colorize("║     🧠 Memory-Enhanced Chatbot - Kafka Stack Demo 🧠      ║", Colors.HEADER)}
{self.colorize("╚════════════════════════════════════════════════════════════╝", Colors.HEADER)}

{self.colorize("Connected to:", Colors.BOLD)} Kafka @ {KAFKA_BOOTSTRAP}
{self.colorize("Session ID:", Colors.BOLD)} {self.session_id}

Type {self.colorize("/help", Colors.OKCYAN)} for commands or just chat naturally!
Type {self.colorize("/exit", Colors.OKCYAN)} to quit.
"""
        print(banner)


def parse_time_command(arg: str) -> tuple[int, int, int]:
    """Parse time advancement argument like '30d', '6m', '1y'."""
    arg = arg.strip().lower()

    if arg.endswith("d"):
        return (int(arg[:-1]), 0, 0)
    elif arg.endswith("m"):
        return (0, int(arg[:-1]), 0)
    elif arg.endswith("y"):
        return (0, 0, int(arg[:-1]))
    else:
        # Default to days
        return (int(arg), 0, 0)


def main():
    """Main chatbot loop."""
    chatbot = MemoryChatbot()
    chatbot.print_banner()

    while True:
        try:
            # Get user input
            user_input = input(f"\n{Colors.OKGREEN}You:{Colors.ENDC} ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else None

                if command in ["/exit", "/quit"]:
                    print(
                        f"\n{Colors.OKCYAN}Goodbye! Memories preserved in Qdrant.{Colors.ENDC}\n"
                    )
                    break

                elif command == "/help":
                    chatbot.show_help()

                elif command == "/clear":
                    os.system("clear" if os.name != "nt" else "cls")
                    chatbot.print_banner()

                elif command == "/reset_time":
                    chatbot.reset_time()

                elif command == "/advance_time":
                    if not arg:
                        print(
                            f"{Colors.FAIL}Usage: /advance_time <amount>[d|m|y]{Colors.ENDC}"
                        )
                        print(
                            f"Examples: /advance_time 30d, /advance_time 6m, /advance_time 1y"
                        )
                    else:
                        try:
                            days, months, years = parse_time_command(arg)
                            chatbot.advance_time(days=days, months=months, years=years)
                        except ValueError:
                            print(
                                f"{Colors.FAIL}Invalid time format. Use: 30d, 6m, or 1y{Colors.ENDC}"
                            )

                else:
                    print(
                        f"{Colors.FAIL}Unknown command. Type /help for available commands.{Colors.ENDC}"
                    )

                continue

            # Normal chat interaction
            print()  # Blank line before memory operations
            response = chatbot.chat_response(user_input)
            print(f"\n{Colors.OKBLUE}Bot:{Colors.ENDC} {response}")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.OKCYAN}Interrupted. Goodbye!{Colors.ENDC}\n")
            break
        except Exception as e:
            print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}\n")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
