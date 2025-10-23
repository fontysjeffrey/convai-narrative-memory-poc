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
import re
import sys
import json
import uuid
import time
import datetime as dt
from typing import Optional, List, Dict, Any, Iterable

import requests
from confluent_kafka import Producer, Consumer

# Kafka configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

# LLM configuration
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PORTKEY_MODEL = os.getenv("PORTKEY_MODEL", "mistral-large")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


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

    def _call_portkey_stream(self, messages: List[Dict[str, str]]):
        headers = {
            "content-type": "application/json",
            "x-portkey-api-key": PORTKEY_API_KEY,
        }
        payload = {
            "model": PORTKEY_MODEL,
            "messages": messages,
            "temperature": 0.35,
            "max_tokens": 200,
            "stream": True,
        }

        with requests.post(
            f"{PORTKEY_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        ) as response:
            response.raise_for_status()
            buffer = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line or line.startswith(":"):
                    continue
                if line.strip() == "data: [DONE]":
                    break
                if line.startswith("data:"):
                    line = line[len("data:") :].strip()
                buffer += line
                try:
                    payload = json.loads(buffer)
                except json.JSONDecodeError:
                    continue
                buffer = ""
                for choice in payload.get("choices", []):
                    delta = choice.get("delta", {})
                    token = delta.get("content")
                    if token:
                        yield token


class MemoryChatbot:
    def __init__(self):
        self.producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
        self.time_offset = dt.timedelta(0)  # For time manipulation
        self.conversation_history: List[Dict[str, str]] = []
        self._last_user_anchor_id: Optional[str] = None
        self._last_bot_anchor_id: Optional[str] = None
        allow_session_env = os.getenv("CHATBOT_ALLOW_SESSION_RECALL", "1").lower()
        self.allow_session_recall = allow_session_env not in {"0", "false", "no"}
        self.session_id = str(uuid.uuid4())[:8]

    def reset_session(self, reason: Optional[str] = None):
        self.conversation_history.clear()
        self._last_user_anchor_id = None
        self._last_bot_anchor_id = None
        self.session_id = str(uuid.uuid4())[:8]
        message = "Session reset; new session_id " + self.session_id
        if reason:
            message += f" ({reason})"
        self.log_memory_op(
            "🔁",
            message,
            Colors.OKBLUE,
        )

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

        self.producer.produce("anchors-write", json.dumps(anchor).encode("utf-8"))
        self.producer.flush()

        self.log_memory_op(
            "📝",
            f"Stored anchor: {anchor_id[:8]}... | salience: {salience:.1f}",
            Colors.DIM,
        )

        # Give the indexer a moment to process (indexer needs to embed + store in Qdrant)
        time.sleep(1.0)

        return anchor_id

    def request_recall(
        self,
        query: str,
        top_k: int = 5,
        ignore_anchor_ids: Optional[List[str]] = None,
        allow_session_matches: bool = False,
    ) -> Optional[Dict]:
        """Request memory recall and wait for response."""
        request_id = str(uuid.uuid4())
        now = self.get_current_time()

        request = {
            "request_id": request_id,
            "query": query,
            "now": now.isoformat(),
            "top_k": top_k,
            "session_id": self.session_id,
        }

        if ignore_anchor_ids:
            request["ignore_anchor_ids"] = ignore_anchor_ids
        if allow_session_matches:
            request["allow_session_matches"] = True

        # Subscribe to response topics BEFORE sending request
        recall_consumer = self._create_consumer("recall-response")
        retell_consumer = self._create_consumer("retell-response")

        # Give consumers time to fully subscribe and get partition assignment
        # This is critical - Kafka consumers need time to join the group and get assigned partitions
        time.sleep(1.0)

        # Now send the request
        self.producer.produce("recall-request", json.dumps(request).encode("utf-8"))
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
        return self.chat_turn(user_input)["response"]

    def chat_turn(
        self, user_input: str, persona: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a full conversation turn capturing metadata for UI layers."""

        turn_data: Dict[str, Any] = {
            "user_input": user_input,
            "session_id": self.session_id,
            "anchors": {},
            "recall": None,
        }

        # Store the user's message
        user_anchor_id = self.store_anchor(f"User said: {user_input}", salience=0.9)
        turn_data["anchors"]["user"] = user_anchor_id
        self._last_user_anchor_id = user_anchor_id
        self._append_history("user", user_input)

        # Try to recall relevant memories (but not the message we just stored)
        try:
            ignore_ids: List[str] = []
            if self._last_bot_anchor_id:
                ignore_ids.append(self._last_bot_anchor_id)
            recall_data = self.request_recall(
                user_input,
                top_k=5,
                ignore_anchor_ids=ignore_ids or None,
                allow_session_matches=self.allow_session_recall,
            )
        except Exception as e:
            print(f"[ERROR] Exception in request_recall: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            recall_data = None

        if recall_data and recall_data.get("beats"):
            turn_data["recall"] = recall_data
            self.display_recall_info(recall_data)

        response = self._generate_persona_response_sync(
            user_input=user_input,
            recall_data=recall_data,
            persona=persona,
        )

        bot_anchor_id = self.store_anchor(f"Bot said: {response}", salience=0.7)
        turn_data["anchors"]["bot"] = bot_anchor_id
        turn_data["response"] = response
        self._last_bot_anchor_id = bot_anchor_id
        self._append_history("assistant", response)

        return turn_data

    def chat_turn_stream(
        self, user_input: str, persona: Optional[str] = None
    ) -> Iterable[Dict[str, Any]]:
        """Stream a full turn while recording anchors/recall metadata."""

        turn_data: Dict[str, Any] = {
            "user_input": user_input,
            "session_id": self.session_id,
            "anchors": {},
            "recall": None,
        }

        user_anchor_id = self.store_anchor(f"User said: {user_input}", salience=0.9)
        turn_data["anchors"]["user"] = user_anchor_id
        self._last_user_anchor_id = user_anchor_id
        self._append_history("user", user_input)
        yield {
            "kind": "event",
            "event": {
                "type": "anchor_stored",
                "payload": {"role": "user", "anchor_id": user_anchor_id},
            },
        }

        try:
            ignore_ids: List[str] = []
            if self._last_bot_anchor_id:
                ignore_ids.append(self._last_bot_anchor_id)
            recall_data = self.request_recall(
                user_input,
                top_k=5,
                ignore_anchor_ids=ignore_ids or None,
                allow_session_matches=self.allow_session_recall,
            )
        except Exception as e:
            print(f"[ERROR] Exception in request_recall: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            recall_data = None

        if recall_data:
            turn_data["recall"] = recall_data

            if recall_data.get("beats"):
                self.display_recall_info(recall_data)

            yield {
                "kind": "event",
                "event": {"type": "recall", "payload": recall_data},
            }

            beats = recall_data.get("beats") or []
            if beats:
                yield {
                    "kind": "event",
                    "event": {"type": "beats", "payload": {"beats": beats}},
                }

            if recall_data.get("retelling"):
                yield {
                    "kind": "event",
                    "event": {
                        "type": "retell",
                        "payload": {"retelling": recall_data["retelling"]},
                    },
                }
        else:
            self.log_memory_op("💭", "No memories recalled", Colors.DIM)

        collected: List[str] = []
        for chunk in self.stream_persona_response(
            user_input=user_input,
            recall_data=recall_data,
            persona=persona,
        ):
            if chunk:
                collected.append(chunk)
                yield {"kind": "token", "delta": chunk}

        response = "".join(collected).strip()
        bot_anchor_id = self.store_anchor(f"Bot said: {response}", salience=0.7)
        turn_data["anchors"]["bot"] = bot_anchor_id
        turn_data["response"] = response
        self._last_bot_anchor_id = bot_anchor_id
        self._append_history("assistant", response)
        yield {
            "kind": "event",
            "event": {
                "type": "anchor_stored",
                "payload": {"role": "bot", "anchor_id": bot_anchor_id},
            },
        }
        yield {"kind": "final", "turn": turn_data}

    def _append_history(self, role: str, content: str):
        trimmed = content.strip()
        if not trimmed:
            return
        self.conversation_history.append({"role": role, "content": trimmed})
        max_turns = max(0, int(os.getenv("CHATBOT_HISTORY_TURNS", "6")))
        if max_turns > 0:
            max_entries = max_turns * 2
            if len(self.conversation_history) > max_entries:
                self.conversation_history = self.conversation_history[-max_entries:]

    def _generate_persona_response_sync(
        self,
        user_input: str,
        recall_data: Optional[Dict[str, Any]],
        persona: Optional[str] = None,
    ) -> str:
        """Route conversation through an LLM with persona and memory context."""

        messages, memory_text, persona_text = self._prepare_persona_messages(
            user_input, recall_data, persona
        )

        llm_response = self._call_persona_llm(messages)
        if llm_response:
            return llm_response

        if memory_text:
            return self._generate_response_with_context(user_input, memory_text)

        if recall_data is None or not recall_data.get("beats"):
            self.log_memory_op("💭", "No memories recalled", Colors.DIM)
        return self._generate_simple_response(user_input)

    def stream_persona_response(
        self,
        user_input: str,
        recall_data: Optional[Dict[str, Any]],
        persona: Optional[str] = None,
    ) -> Any:
        """Yield persona-guided response chunks, falling back to sync output."""

        messages, memory_text, persona_text = self._prepare_persona_messages(
            user_input, recall_data, persona
        )

        if PORTKEY_API_KEY:
            try:
                for chunk in self._call_portkey_stream(messages):
                    if chunk:
                        yield chunk
                return
            except Exception as exc:
                print(f"[chatbot] Portkey streaming failed: {exc}", file=sys.stderr)

        fallback = self._generate_persona_response_sync(
            user_input, recall_data, persona_text
        )
        if fallback:
            yield fallback

    def _prepare_persona_messages(
        self,
        user_input: str,
        recall_data: Optional[Dict[str, Any]],
        persona: Optional[str],
    ) -> tuple[List[Dict[str, str]], Optional[str], str]:
        persona_text = persona or os.getenv(
            "CHATBOT_PERSONA",
            "You are Little Wan, an earnest padawan archivist who adores Master Lonn. Speak warmly, use light dojo metaphors, and decide when to weave in memories. Only mention memories if they help move the conversation forward.",
        )

        memory_text = None
        if recall_data and recall_data.get("retelling"):
            memory_text = recall_data["retelling"].strip()
        elif recall_data and recall_data.get("beats"):
            snippets = [beat.get("text", "") for beat in recall_data["beats"][:2]]
            snippets = [text for text in snippets if text]
            if snippets:
                memory_text = " ".join(snippets)

        history_messages: List[Dict[str, str]] = []
        if self.conversation_history:
            history_messages.extend(self.conversation_history)

        context_note = (
            f"You remember: {memory_text}"
            if memory_text
            else "You currently recall no relevant memories from the archive."
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": persona_text},
            {"role": "system", "content": context_note},
        ]

        if history_messages:
            messages.extend(history_messages)

        messages.append({"role": "user", "content": user_input})

        return messages, memory_text, persona_text

    def _call_persona_llm(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Call Portkey / OpenAI to generate persona-driven responses."""

        # Portkey inference takes precedence when configured
        if PORTKEY_API_KEY:
            try:
                headers = {
                    "content-type": "application/json",
                    "x-portkey-api-key": PORTKEY_API_KEY,
                }
                payload = {
                    "model": PORTKEY_MODEL,
                    "messages": messages,
                    "temperature": 0.35,
                    "max_tokens": 200,
                }
                response = requests.post(
                    f"{PORTKEY_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if choices:
                    return choices[0].get("message", {}).get("content")
            except Exception as exc:
                print(f"[chatbot] Portkey persona call failed: {exc}", file=sys.stderr)

        # Fall back to OpenAI if available
        if OPENAI_API_KEY:
            try:
                import openai

                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                result = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    temperature=0.35,
                    max_tokens=200,
                )
                return result.choices[0].message.content
            except Exception as exc:
                print(f"[chatbot] OpenAI persona call failed: {exc}", file=sys.stderr)

        return None

    def _generate_response_with_context(
        self, user_input: str, memory_context: Optional[str]
    ) -> str:
        """Generate a response using recalled memory context."""
        lower_input = user_input.lower()

        if memory_context and any(
            word in lower_input
            for word in ["remember", "recall", "happened", "tell me"]
        ):
            return memory_context

        base_response = self._generate_simple_response(user_input)

        if memory_context:
            summary = self._summarize_memory_context(memory_context)
            if summary:
                if not base_response.endswith((".", "!", "?")):
                    base_response = f"{base_response}."
                return f"{base_response} Based on what I remember: {summary}"

        return base_response

    def _summarize_memory_context(self, memory_context: str) -> str:
        """Return a compact summary suitable for inline conversation."""
        summary = memory_context.strip().splitlines()[0]
        return summary[:220].rstrip()

    def _generate_simple_response(self, user_input: str) -> str:
        """Generate a simple response without memory context."""
        lower_input = user_input.lower()

        identity_prompts = [
            "who are you",
            "what are you",
            "your name",
            "who is little wan",
        ]
        if any(prompt in lower_input for prompt in identity_prompts):
            return (
                "I'm Little Wan, Master Lonn's memory-obsessed apprentice. "
                "I weave past anchors into context so our virtual human stays consistent."
            )

        who_am_i_prompts = ["who am i", "do you know who i am", "remember me"]
        if any(prompt in lower_input for prompt in who_am_i_prompts):
            return (
                "I only know what you've shared in this session. The more memories you give me, "
                "the better I can describe you next time."
            )

        introduction_name = self._extract_name(lower_input)
        if introduction_name:
            return (
                f"Great to meet you, {introduction_name}! I'll hold on to that. "
                "What should we tackle next?"
            )

        greetings = ["hello", "hi", "hey", "greetings"]
        if any(g in lower_input for g in greetings):
            return "Hello! I'm a memory-enhanced chatbot. I'll remember our conversation and can recall it later with realistic time-based decay."

        questions = ["what", "how", "why", "when", "where", "who"]
        if any(q in lower_input for q in questions):
            return "That's an interesting question! I don't have much memory context yet, but I'm storing our conversation."

        return "I see. Tell me more, and I'll remember our discussion for future reference."

    def _extract_name(self, lower_input: str) -> Optional[str]:
        """Extract a name from user introductions."""
        patterns = [
            r"\bi am\s+([a-zA-Z][\w\-]*(?:\s+[a-zA-Z][\w\-]*)?)",
            r"\bi'm\s+([a-zA-Z][\w\-]*(?:\s+[a-zA-Z][\w\-]*)?)",
            r"\bmy name is\s+([a-zA-Z][\w\-]*(?:\s+[a-zA-Z][\w\-]*)?)",
            r"\bthis is\s+([a-zA-Z][\w\-]*(?:\s+[a-zA-Z][\w\-]*)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower_input)
            if match:
                name = match.group(1).strip()
                if name:
                    return name.title()
        return None

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
  /reset_session            - Start a fresh session (ignores current run for recall)

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

                elif command == "/reset_session":
                    chatbot.reset_session()

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
                            chatbot.reset_session(
                                reason="auto-reset after /advance_time"
                            )
                            print(
                                chatbot.colorize(
                                    "Session refreshed to stabilise memory timeline.",
                                    Colors.DIM,
                                )
                            )
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
