import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.agent_graph import reflexion_node, route_after_reflexion, AgentState

@pytest.mark.asyncio
async def test_reflexion_compliant():
    """Test that a compliant answer passes reflexion."""
    
    # Mock LLM response to be compliant (Score: 1.0)
    mock_response = MagicMock()
    mock_response.content = "Score: 1.0\nFeedback: Looks good."
    
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response
    
    # Patch create_llm to return a mock that produces our chain
    with patch("app.core.agent_graph.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        # The node does: chain = prompt | llm. So we need to mock the pipe behavior or the chain execution.
        # But wait, reflexion_node does `reflexion_prompt | llm`.
        # Easier to mock `chain.ainvoke` directly if we can patch the chain construction.
        # Actually, let's patch `ChatOllama` or `create_llm` to return a mock object that supports `ainvoke` when piped.
        # LangChain piping is complex to mock. 
        # Strategy: Mock `chain.ainvoke` by patching the `|` operator or just the final chain?
        # NO, simpler: The node code does:
        # chain = reflexion_prompt | llm
        # response = await chain.ainvoke(...)
        
        # If we make `llm` a MagicMock, `prompt | llm` returns a `RunnableSequence`.
        # We can mock the `ainvoke` of that sequence.
        
        # Alternative Strategy: Patch `ainvoke` on the resulting chain object.
        # But we don't have access to the chain object in the test scope easily.
        
        # Let's try mocking the `ainvoke` method of the object returned by `create_llm`.
        # In LangCHain, `prompt | llm` calls `llm` as a runnable.
        
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_create_llm.return_value = mock_llm
        
        # Ideally, `prompt | mock_llm` results in a Runnable that calls `mock_llm.ainvoke`.
        # Let's hope MagicMock handles the `|` operator gratefully or we might need a real Runnable.
        # Actually, `ChatPromptTemplate` | `MagicMock` might fail.
        # Let's use a side_effect to return the mock chain if needed.
        
        # Let's assume for this unit test we can mock `reflexion_prompt | llm` by mocking the `__or__` ? No.
        
        # Let's just mock the `chain` variable inside `reflexion_node`? 
        # No, can't easily reach inside function.
        
        # Better approach: We will patch `ChatPromptTemplate.__or__` if necessary, 
        # OR we can assume `create_llm` returns a custom object that implements `__or__` 
        # but that's getting complicated. 
        
        # Let's try to pass a `final_answer` and rely on the implementation details. 
        # If I look at the code:
        # chain = reflexion_prompt | llm
        # response = chain.ainvoke(...)
        
        # If I patch `app.core.agent_graph.ChatPromptTemplate` to return a mock prompt,
        # and set `mock_prompt | anything` to return `mock_chain`.
        with patch("app.core.agent_graph.ChatPromptTemplate") as MockPrompt:
             mock_prompt_instance = MagicMock()
             mock_chain_instance = AsyncMock()
             mock_chain_instance.ainvoke.return_value = mock_response
             
             # prompt | llm -> chain
             mock_prompt_instance.__or__.return_value = mock_chain_instance
             MockPrompt.from_messages.return_value = mock_prompt_instance
             
             state = {"final_answer": "Safe answer", "reflexion_attempts": 0}
             result = await reflexion_node(state)
             
             assert result["reflexion_score"] == 1.0
             assert result["reflexion_attempts"] == 1

@pytest.mark.asyncio
async def test_reflexion_violation():
    """Test that a violation triggers a low score."""
    
    mock_response = MagicMock()
    mock_response.content = "Score: 0.4\nFeedback: PII detected."
    
    with patch("app.core.agent_graph.create_llm"), \
         patch("app.core.agent_graph.ChatPromptTemplate") as MockPrompt:
             
             mock_prompt_instance = MagicMock()
             mock_chain_instance = AsyncMock()
             mock_chain_instance.ainvoke.return_value = mock_response
             mock_prompt_instance.__or__.return_value = mock_chain_instance
             MockPrompt.from_messages.return_value = mock_prompt_instance
             
             state = {"final_answer": "My SSN is 123", "reflexion_attempts": 0}
             result = await reflexion_node(state)
             
             assert result["reflexion_score"] == 0.4
             assert "PII detected" in result["reflexion_feedback"]
             assert result["reflexion_attempts"] == 1

def test_routing_logic():
    """Test routing based on score."""
    
    # Case 1: Score 1.0 -> END
    state = {"reflexion_score": 1.0, "reflexion_attempts": 1}
    assert route_after_reflexion(state) == "__end__"
    
    # Case 2: Score 0.4 -> GENERATOR (Retry)
    state = {"reflexion_score": 0.4, "reflexion_attempts": 1}
    assert route_after_reflexion(state) == "generator"
    
    # Case 3: Score 0.4, Max Attempts -> WARNING
    state = {"reflexion_score": 0.4, "reflexion_attempts": 3}
    assert route_after_reflexion(state) == "append_warning"
