from typing import Dict, List, Literal, TypedDict, Union


class UserMessageTextContentPart(TypedDict):
    type: Literal["text"]
    text: str


class UserMessageImageContentPart(TypedDict):
    type: Literal["image_url"]
    # Ignoring the other "detail param for now"
    image_url: Dict[Literal["url"], str]

from typing import List, Literal, Optional, Protocol

class Function(TypedDict):
    arguments: str
    name: str

class ToolCall(TypedDict):
    id: str
    function: Function
    type: Literal["function"]


class AssistantMessage(TypedDict, total=False):
    content: Optional[str]
    role: Literal["assistant"]
    name: Optional[str]
    tool_calls: Optional[List[str]]

    # Deprecated
    function_call: Optional[Function] = None

class FunctionCall(TypedDict):
    arguments: str
    name: str
