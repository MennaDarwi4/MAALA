from langchain_groq import ChatGroq
from langchain_community.utilities import ArxivAPIWrapper, WikipediaAPIWrapper
from langchain_community.tools import ArxivQueryRun, WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import re

class SearchAgent:
    def __init__(self, groq_api_key):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key, 
            model_name="llama-3.3-70b-versatile",
            temperature=0
        )
        
        # Initialize Tools
        api_wrapper_wiki = WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=1500)
        self.wiki = WikipediaQueryRun(api_wrapper=api_wrapper_wiki)
        
        api_wrapper_arxiv = ArxivAPIWrapper(top_k_results=2, doc_content_chars_max=1500)
        self.arxiv = ArxivQueryRun(api_wrapper=api_wrapper_arxiv)
        
        self.search = DuckDuckGoSearchRun()
        
        self.tools = {
            "Wikipedia": {
                "tool": self.wiki,
                "description": "Search Wikipedia for encyclopedic information about people, places, events, concepts, and general knowledge."
            },
            "Arxiv": {
                "tool": self.arxiv,
                "description": "Search scientific papers and academic research. Use for technical, scientific, or research-related questions."
            },
            "Search": {
                "tool": self.search,
                "description": "Search the internet for current events, news, recent information, and real-time data."
            }
        }

    def _get_system_prompt(self):
        tools_desc = "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])
        
        return f"""You are a research assistant. You MUST use tools to find information. DO NOT answer from your own knowledge.

Available tools:
{tools_desc}

MANDATORY PROCESS:
1. ALWAYS use at least ONE tool before answering
2. For factual questions → use Wikipedia or Search
3. For scientific/technical questions → use Arxiv or Wikipedia
4. For current events/news → use Search

Response format (YOU MUST FOLLOW THIS):

Thought: [explain which tool you'll use and why]
Action: [exactly one of: Wikipedia, Arxiv, Search]
Action Input: [your search query]

After receiving the Observation, you can either:
- Use another tool (repeat Thought/Action/Action Input)
- OR provide Final Answer

To finish:
Thought: [explain your conclusion based on tool results]
Final Answer: [comprehensive answer using information from the tools]

CRITICAL RULES:
- NEVER answer without using tools first
- ALWAYS cite which tool provided the information
- Action must be EXACTLY: Wikipedia, Arxiv, or Search
- Be thorough and detailed in your Final Answer

Begin!"""

    def run(self, query, callbacks=None):
        """Run the search agent"""
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=f"User Question: {query}\n\nRemember: You MUST use at least one tool before answering!")
            ]
            
            sources = []
            history = []
            max_iterations = 6
            tools_used = 0
            
            for iteration in range(max_iterations):
                # Get LLM response
                response = self.llm.invoke(messages)
                response_text = response.content
                
                # Parse response
                thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)", response_text, re.DOTALL | re.IGNORECASE)
                action_match = re.search(r"Action:\s*(\w+)", response_text, re.IGNORECASE)
                action_input_match = re.search(r"Action Input:\s*(.+?)(?=\n\n|\n(?=[A-Z])|$)", response_text, re.DOTALL | re.IGNORECASE)
                
                # Extract thought
                if thought_match:
                    thought = thought_match.group(1).strip()
                    history.append(("ai", f"🤔 Thought: {thought}"))
                
                # Check for Final Answer
                if "Final Answer:" in response_text or "final answer:" in response_text.lower():
                    # Only allow Final Answer if at least one tool was used
                    if tools_used == 0:
                        history.append(("human", "⚠️ You must use at least one tool before providing a Final Answer!"))
                        messages.append(AIMessage(content=response_text))
                        messages.append(HumanMessage(content="ERROR: You MUST use at least one tool (Wikipedia, Arxiv, or Search) before answering. Please use a tool now."))
                        continue
                    
                    # Extract final answer
                    final_answer_match = re.search(r"Final Answer:\s*(.+)", response_text, re.DOTALL | re.IGNORECASE)
                    if final_answer_match:
                        final_answer = final_answer_match.group(1).strip()
                    else:
                        final_answer = response_text.split("Final Answer:")[-1].strip()
                    
                    return {
                        "response": final_answer,
                        "sources": list(set(sources)),
                        "history": history
                    }
                
                # Execute tool action
                if action_match and action_input_match:
                    tool_name = action_match.group(1).strip()
                    tool_input = action_input_match.group(1).strip()
                    
                    # Clean up tool input
                    tool_input = tool_input.replace("[", "").replace("]", "").strip()
                    
                    history.append(("ai", f"🔧 Action: {tool_name}"))
                    history.append(("ai", f"🔍 Input: {tool_input}"))
                    
                    # Execute tool
                    if tool_name in self.tools:
                        try:
                            observation = self.tools[tool_name]["tool"].run(tool_input)
                            tools_used += 1
                            sources.append(f"{tool_name}: {tool_input}")
                            
                            # Truncate observation for display
                            obs_preview = observation[:400] + "..." if len(observation) > 400 else observation
                            history.append(("human", f"📋 Observation: {obs_preview}"))
                            
                            # Add to messages
                            messages.append(AIMessage(content=response_text))
                            messages.append(HumanMessage(content=f"Observation: {observation}\n\nYou can now either use another tool or provide a Final Answer based on this information."))
                            
                        except Exception as e:
                            error_msg = f"Error using {tool_name}: {str(e)}"
                            history.append(("human", f"❌ {error_msg}"))
                            messages.append(AIMessage(content=response_text))
                            messages.append(HumanMessage(content=f"{error_msg}\n\nPlease try a different tool or search query."))
                    else:
                        error_msg = f"Unknown tool: {tool_name}. Must be exactly one of: {', '.join(self.tools.keys())}"
                        history.append(("human", f"❌ {error_msg}"))
                        messages.append(AIMessage(content=response_text))
                        messages.append(HumanMessage(content=error_msg))
                else:
                    # No valid action found
                    if tools_used == 0:
                        history.append(("human", "⚠️ Invalid format! You MUST use a tool first."))
                        messages.append(AIMessage(content=response_text))
                        messages.append(HumanMessage(content="You must provide an Action and Action Input. Use this format:\n\nThought: [your thinking]\nAction: [Wikipedia/Arxiv/Search]\nAction Input: [search query]"))
                    else:
                        # Tools were used, ask for final answer
                        messages.append(AIMessage(content=response_text))
                        messages.append(HumanMessage(content="Please provide your Final Answer based on the information you gathered from the tools."))
            
            # Max iterations reached
            return {
                "response": "I reached the maximum number of search steps. Here's what I found: " + (sources[0] if sources else "Please try asking your question differently."),
                "sources": list(set(sources)),
                "history": history
            }
            
        except Exception as e:
            return {
                "response": f"An error occurred: {str(e)}",
                "sources": [],
                "history": [("ai", f"❌ Error: {str(e)}")]
            }