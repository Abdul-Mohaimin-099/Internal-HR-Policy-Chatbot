
from langchain.agents import create_agent
from hr_chatbot.llm.workflows.policy_chat.state import PolicyChatState


async def policyChatNode(state: PolicyChatState):
    # model = init_chat_model("gpt-5.5")

    agent = create_agent(
        model="google_genai:gemini-3.5-flash-lite",
        system_prompt="You are a helpful HR policy assistant",
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": state["user_input"]}]}
    )
    return {
        "messages": result["messages"]
    }
