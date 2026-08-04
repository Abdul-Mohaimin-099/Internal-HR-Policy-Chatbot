from fastapi import APIRouter

from hr_chatbot.api.v1.schemas import PolicyChatInput, PolicyChatOutput
from hr_chatbot.llm.workflows.policy_chat.graph import policy_chat_graph

router = APIRouter()

@router.post("/policy-chat/chatbot", response_model=PolicyChatOutput)
async def policy_chatbot(
    chat_input: PolicyChatInput
): 
    graph = policy_chat_graph.compile()
    state = {
        "user_input": chat_input.user_input
    }
    result = await graph.ainvoke(state)
    return {
        "response": result['messages'][-1].text
    }
