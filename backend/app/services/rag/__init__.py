"""
Agentic RAG — an additional long-term memory layer for ReflectAI.

Nothing in this package touches the existing `profiles` or
`conversations` collections' *content*; it only reads from them to
build a separate `memories` index (see app/database.py) and, at query
time, hands DigitalTwinEngine an extra system message it can choose to
include. If retrieval is skipped or fails for any reason, chat falls
back to exactly the existing (pre-RAG) behavior.

Modules:
  models.py           MemoryRecord / MemoryHit data shapes
  embedding_service.py Pluggable embedding provider abstraction
  memory_store.py      MongoDB-backed storage + vector/brute-force search
  indexer.py           Turns existing ReflectAI data into memory records
  retrieval_agent.py   Bounded agentic retrieval loop
  context_builder.py   Formats retrieved memories into a prompt block
"""
