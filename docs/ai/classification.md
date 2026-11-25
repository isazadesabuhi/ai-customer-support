# Customer message classification notes

TASK-008 classifies one message with the existing `LLMClient` and a versioned prompt. See the [classification architecture](../architecture/message-classification.md) for the taxonomy, examples, overlapping intents, and failure contract. The seven seed-based cases exercise the integration using predetermined labels. Sentiment and urgency are scheduled separately in TASK-009.
