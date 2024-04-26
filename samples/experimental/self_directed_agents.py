import asyncio
import os
from typing import List, Optional, Required, Sequence, Tuple, cast

from aioconsole import aprint

from autogen.experimental.agent import Agent
from autogen.experimental.agents.assistant_agent import AssistantAgent
from autogen.experimental.chat_history import ChatHistoryReadOnly
from autogen.experimental.chats.group_chat import GroupChat
from autogen.experimental.model_clients.openai_client import OpenAI
from autogen.experimental.speaker_selection import SpeakerSelection
from autogen.experimental.termination import (
    NotTerminated,
    Terminated,
    Termination,
    TerminationReason,
    TerminationResult,
)
from autogen.experimental.types import GenerateReplyResult, MessageContext
import random


class SelfDirectedTermination(Termination):
    def record_turn_taken(self, agent: Agent) -> None:
        pass

    async def check_termination(self, chat_history: ChatHistoryReadOnly) -> TerminationResult:
        if len(chat_history) > 0:
            last_context = cast(MessageContextWithSpeakerSelection, chat_history.contexts[-1])
            if last_context["recipient"] is None:
                return Terminated(reason=TerminationReason.GOAL_REACHED, explanation="No recipient")
        return NotTerminated()

    def reset(self) -> None:
        pass

class SelfDirectedSpeakerSelection(SpeakerSelection):
    def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Tuple[Agent, Optional[str]]:
        if len(chat_history) > 0:
            last_context = cast(MessageContextWithSpeakerSelection, chat_history.contexts[-1])
            recipient = last_context["recipient"]
            if recipient is None:
                assert False, "Should have terminated already"
            else:
                return recipient, None
        else:
            # Start with the first agent
            return agents[0], None

class MessageContextWithSpeakerSelection(MessageContext, total=False):
    candidates: Sequence[Agent]
    recipient: Required[Optional[Agent]]

class SelfDirectedAgent(Agent):
    def __init__(self, generic_agent: Agent, neighbors: Optional[Sequence[Agent]] = None) -> None:
        super().__init__()
        self._generic_agent = generic_agent
        self.neighbors = neighbors

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._generic_agent.name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._generic_agent.description

    async def select_recipient(self, chat_history: ChatHistoryReadOnly, candidates: Sequence[Agent]) -> Optional[Agent]:
        if len(candidates) == 1:
            return candidates[0]

        # random choice
        new_candidates = list(candidates) + [None]
        return random.choice(new_candidates)

    async def suggest_candidates(self, chat_history: ChatHistoryReadOnly, recipient: Optional[Agent]) -> Sequence[Agent]:
        if recipient is None:
            return []

        return recipient.neighbors

    async def generate_reply(
        self,
        chat_history: ChatHistoryReadOnly,
    ) -> GenerateReplyResult:

        assert self.neighbors is not None
        if len(chat_history) > 0:
            last_context = cast(MessageContextWithSpeakerSelection, chat_history.contexts[-1])
            candidates = last_context["candidates"] if "candidates" in last_context else self.neighbors
        else:
            candidates = self.neighbors

        response = await self._generic_agent.generate_reply(chat_history)

        recipient = await self.select_recipient(chat_history, candidates)
        match response:
            case (_, _):
                reply, context_new = response
                context = cast(MessageContextWithSpeakerSelection, context_new)
                context["recipient"] = recipient
            case _:
                reply = response
                context = MessageContextWithSpeakerSelection(recipient=recipient)

        context["recipient"] = recipient
        context["candidates"] = await self.suggest_candidates(chat_history, recipient)
        return reply, context

async def main() -> None:

    model_client = OpenAI(model="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"])

    central_agent = SelfDirectedAgent(AssistantAgent(name="central", system_message="Assess the last joke then ask for a new one. If there was no joke you can just ask for one.", model_client=model_client))
    spoke1_agent = SelfDirectedAgent(AssistantAgent(name="bad_comedian", system_message="Tell a bad joke", model_client=model_client))
    spoke2_agent = SelfDirectedAgent(AssistantAgent(name="good_comedian", system_message="Tell a good joke", model_client=model_client))

    central_agent.neighbors = [spoke1_agent, spoke2_agent]
    spoke1_agent.neighbors = [central_agent]
    spoke2_agent.neighbors = [central_agent]

    chat = GroupChat(
        agents=[spoke1_agent, central_agent, spoke2_agent],
        send_introduction=False,
        speaker_selection=SelfDirectedSpeakerSelection(),
        termination_manager=SelfDirectedTermination(),
    )

    while not chat.done:
        next_message = await chat.step()
        next_context = chat.chat_history.contexts[-1]

        if next_context["recipient"] is not None:
            recipient = next_context["recipient"].name
        else:
            recipient = "None"

        candidates = next_context["candidates"] if "candidates" in next_context else []
        candidates = [c.name for c in candidates]

        await aprint("[{}->{}] (Suggested candidates: {}) \"{}\"\n----".format(next_message.source, recipient,candidates, next_message.content))

if __name__ == "__main__":
    asyncio.run(main())
