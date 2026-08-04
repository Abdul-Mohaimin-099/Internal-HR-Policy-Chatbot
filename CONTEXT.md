# HR Policy Chat

Internal chatbot that holds a conversation with an employee while
answering their questions about company HR policies, so the employee can
get accurate, policy-grounded answers without waiting for HR staff.

## Language

**Policy Query**:
The underlying question an employee wants answered about company policy.
It persists across the whole conversation — many messages may refine one query.
_Avoid_: ticket, issue, request, case

**Policy Response**:
The chatbot's current answer to a Policy Query. Produced fresh on every
turn and expected to improve as the conversation reveals more detail; it is
never final.
_Avoid_: classification, verdict, label

**Policy Category**:
Which area of HR policy a Policy Query belongs to. Drawn from a fixed,
closed set — the chatbot may not invent new ones.
_Avoid_: type, topic, intent, tag

**Conversation**:
One employee's continuous exchange with the chatbot about a single Policy
Query. Survives across HTTP requests.
_Avoid_: session, chat, thread

**Reply**:
The employee-facing text the chatbot says back on a turn. Carried alongside the
Policy Response, not derived from it.
_Avoid_: message, answer, response
