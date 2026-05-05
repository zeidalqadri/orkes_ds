Fix concurrent session handling for harga chatbot:
1. Fix fetchChatSessions frontend bug (unwrap {sessions: [...]})
2. Add POST /chat/sessions for explicit session creation
3. Update resetChatSession to create backend sessions
4. Verify: Flask 200, E2E tests pass
