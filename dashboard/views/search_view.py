import streamlit as st

def search_view(orchestrator, session_id):
    st.markdown("""
        <style>
        .search-container {
            max-width: 800px;
            margin: 0 auto;
            padding-top: 4rem;
            text-align: center;
        }
        .search-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #4F46E5; /* Indigo-600 */
            margin-bottom: 1rem;
        }
        .search-subtitle {
            font-size: 1.25rem;
            color: #6B7280; /* Gray-500 */
            margin-bottom: 3rem;
        }
        .suggestion-chips {
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 2rem;
        }
        .chip {
            background: white;
            border: 1px solid #E5E7EB;
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            color: #374151;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .chip:hover {
            border-color: #4F46E5;
            color: #4F46E5;
            background: #EEF2FF;
        }
        </style>
    """, unsafe_allow_html=True)

    # Only show welcome screen if no messages
    if len(st.session_state.messages) <= 1:  # Only default message exists
        with st.container():
            st.markdown('<div class="search-container">', unsafe_allow_html=True)
            st.markdown('<div class="search-title">🔍 Need help with your next topic?</div>', unsafe_allow_html=True)
            st.markdown('<div class="search-subtitle">Ask any question to explore the web, Wikipedia, and Arxiv</div>', unsafe_allow_html=True)
            
            # Suggestion Chips (Visual only for now, could be made interactive)
            st.markdown("""
                <div class="suggestion-chips">
                    <div class="chip">🚀 Latest AI Trends</div>
                    <div class="chip">🔬 Quantum Computing</div>
                    <div class="chip">🌍 Climate Change Solutions</div>
                    <div class="chip">📚 History of Mathematics</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
            # Show thinking process if available
            if "history" in msg and msg["history"]:
                with st.expander("💭 Thinking Process"):
                    for item in msg["history"]:
                        if isinstance(item, tuple):
                            role, content = item
                            if role == "ai":
                                st.markdown(f"**🤖 AI:** {content}")
                            elif role == "human":
                                st.markdown(f"**🔍 Observation:** {content}")
                        else:
                            st.write(item)

            # Show sources if available
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 Sources Used"):
                    for source in msg["sources"]:
                        st.markdown(f"- 🔗 {source}")

    # Chat input
    if prompt := st.chat_input("Search for anything...", key="search_input"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🔎 Searching across multiple sources..."):
                try:
                    result = orchestrator.route_query(
                        prompt, 
                        session_id,
                        agent_type="Search Agent"
                    )
                    
                    response_text = result["response"]
                    sources = result.get("sources", [])
                    history = result.get("history", [])
                    
                    # Display response
                    st.write(response_text)
                    
                    # Show thinking process
                    if history:
                        with st.expander("💭 Thinking Process"):
                            for item in history:
                                if isinstance(item, tuple):
                                    role, content = item
                                    if role == "ai":
                                        st.markdown(f"**🤖 AI:** {content}")
                                    elif role == "human":
                                        st.markdown(f"**🔍 Observation:** {content}")
                                else:
                                    st.write(item)
                    
                    # Show sources
                    if sources:
                        with st.expander("📚 Sources Used"):
                            for source in sources:
                                st.markdown(f"- 🔗 {source}")
                    
                    # Add assistant message with metadata
                    st.session_state.messages.append({
                        'role': 'assistant', 
                        "content": response_text,
                        "sources": sources,
                        "history": history
                    })
                    
                    # ✅ FIX: Save session with agent_type
                    st.session_state.session_manager.save_session(
                        session_id, 
                        st.session_state.messages,
                        agent_type="🔍 Search Agent"  # ← الإضافة دي
                    )
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        'role': 'assistant', 
                        "content": error_msg
                    })