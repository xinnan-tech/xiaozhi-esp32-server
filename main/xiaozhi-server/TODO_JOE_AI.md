# Joe AI - Future Features TODO

## Ready for Testing
- [x] Multilingual support (responds in user's language)
- [x] CGM status always in context
- [x] CGM trends injection when asked
- [x] News RAG injection when asked
- [x] History RAG (past conversations)
- [x] Concise, casual persona

## Planned Features
- [ ] Schedule/Calendar awareness
  - Integrate with Google Calendar or iCloud
  - Detect queries like "what do I have tomorrow?"
  - Add `needs_schedule` to classifier
  
- [ ] Class notes RAG
  - Index notes/documents for specific classes
  - Useful for study help, assignment reminders
  - Add `needs_class_notes` to classifier

- [ ] Activity tracking (LOCAL on device, exposed via MCP)
  - Use gyroscope + accelerometer for step counting
  - Detect activity level (walking, stationary, sleeping)
  - Expose as MCP tool: `get_activity_stats`
  - Similar to existing `get_battery_level` pattern
  - Server can query when relevant to conversation

- [ ] Reduce classifier latency
  - Currently 4-7 seconds per call
  - Consider smaller model for intent detection
  - Or run classifier in parallel with other processing

## Architecture Notes
- Context classifier: `core/utils/cgm_intent.py`
- Context injection: `core/connection.py` (lines ~930-1000)
- Client configs: `data/<client-id>/config.json`
- Persona prompts: `data/<client-id>/prompt.txt`

To add a new context type:
1. Update classifier prompt in `cgm_intent.py`
2. Add injection logic in `connection.py`
3. (Optional) Add config flag in client's `config.json`
