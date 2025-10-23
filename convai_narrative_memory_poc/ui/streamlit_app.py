"""Streamlit UI for the memory-enhanced chatbot."""

from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional

import streamlit as st

from convai_narrative_memory_poc.tools.memory_service import (
    MemoryEvent,
    MemoryService,
    MemoryTurn,
)


def _init_state():
    if "service" not in st.session_state:
        st.session_state.service = MemoryService()
    if "turns" not in st.session_state:
        st.session_state.turns = []
    if "events" not in st.session_state:
        st.session_state.events = []
    if "persona" not in st.session_state:
        st.session_state.persona = (
            "You are Little Wan, an earnest padawan archivist who adores Master Lonn. "
            "Speak warmly, sprinkle in light dojo metaphors, and weave memories into the chat only when it helps move the conversation forward."
        )
    if "streaming" not in st.session_state:
        st.session_state.streaming = True


def _format_timestamp(ts: dt.datetime) -> str:
    return ts.astimezone(dt.timezone.utc).strftime("%H:%M:%S")


def _render_sidebar(events: List[MemoryEvent]):
    st.sidebar.header("Memory Activity")
    for event in reversed(events):
        with st.sidebar.expander(
            f"{event.type} · {_format_timestamp(event.timestamp)}", expanded=False
        ):
            st.json(event.payload)


def _handle_command(command: str):
    service: MemoryService = st.session_state.service
    events: List[MemoryEvent] = []

    if command == "/reset_session":
        events.append(service.reset_session(reason="manual reset from UI"))
    elif command == "/reset_time":
        events.append(service.reset_time())
    elif command.startswith("/advance_time"):
        parts = command.split()
        if len(parts) == 2:
            arg = parts[1]
            amount, unit = int(arg[:-1]), arg[-1]
            kwargs = {"days": 0, "months": 0, "years": 0}
            if unit == "d":
                kwargs["days"] = amount
            elif unit == "m":
                kwargs["months"] = amount
            elif unit == "y":
                kwargs["years"] = amount
            events.extend(service.advance_time(**kwargs))
        else:
            st.warning("Usage: /advance_time <number>[d|m|y]")
            return
    else:
        st.warning("Unknown command")
        return

    st.session_state.events.extend(events)
    st.success("Command executed")


def main():
    st.set_page_config(page_title="Memory Dojo Chatbot", layout="wide")
    _init_state()

    st.title("🧠 Memory Dojo Chatbot")
    st.caption("Watch anchors, recalls, and retells unfold while you chat")

    service: MemoryService = st.session_state.service
    service.set_persona(st.session_state.persona)

    with st.expander("Personality & streaming", expanded=True):
        persona_input = st.text_area(
            "Persona prompt",
            st.session_state.persona,
            help="Customize how the assistant speaks and uses memories.",
            height=150,
        )
        streaming_toggle = st.checkbox(
            "Stream replies in real time",
            value=st.session_state.streaming,
        )

        if persona_input.strip() and persona_input.strip() != st.session_state.persona:
            st.session_state.persona = persona_input.strip()
            service.set_persona(st.session_state.persona)

        st.session_state.streaming = streaming_toggle

    col_chat, col_info = st.columns([2, 1])

    with col_chat:
        st.subheader("Conversation")

        if turns := st.session_state.turns:
            for turn in turns:
                with st.chat_message("user"):
                    st.write(turn.user_text)
                    st.caption(f"Session {turn.session_id}")
                with st.chat_message("assistant"):
                    st.write(turn.bot_reply)
                    if turn.recall and turn.recall.get("retelling"):
                        st.caption(f"Retell: {turn.recall['retelling']}")
        else:
            st.info("Start chatting to populate memory events.")

        prompt = st.chat_input("Say something to Little Wan...")
        if prompt:
            if prompt.startswith("/"):
                _handle_command(prompt.strip())
            else:
                user_text = prompt.strip()
                with st.chat_message("user"):
                    st.write(user_text)

                if st.session_state.streaming:
                    assistant_placeholder = st.chat_message("assistant")
                    with assistant_placeholder:
                        text_spot = st.empty()
                        collected = ""
                        final_turn = None
                        for chunk, maybe_turn in service.stream_user_message(user_text):
                            if chunk:
                                collected += chunk
                                text_spot.write(collected)
                            if maybe_turn:
                                final_turn = maybe_turn
                        if final_turn:
                            st.session_state.turns.append(final_turn)
                            st.session_state.events.extend(final_turn.events)
                else:
                    turn = service.send_user_message(user_text)
                    st.session_state.turns.append(turn)
                    st.session_state.events.extend(turn.events)

                st.rerun()

    with col_info:
        st.subheader("Latest Memory Beats")
        if turns := st.session_state.turns:
            last_turn = turns[-1]
            recall = last_turn.recall or {}
            beats = recall.get("beats", [])
            if beats:
                for idx, beat in enumerate(beats, 1):
                    st.markdown(f"**Beat {idx}**")
                    st.write(beat.get("text", ""))
                    st.caption(
                        f"Activation {beat.get('activation', 0):.2f} · Age {beat.get('perceived_age', '?')}"
                    )
            else:
                st.info("No beats retrieved yet.")
        else:
            st.info("Chat to trigger recalls.")

    _render_sidebar(st.session_state.events)


if __name__ == "__main__":
    main()
