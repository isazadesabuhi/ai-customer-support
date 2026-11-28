# AI engineering notes

The reusable OpenAI client, customer message classifier, sentiment and urgency analyzer, and customer-response draft generator are implemented. See the [LLM integration architecture](../architecture/llm-integration.md), [classification architecture](../architecture/message-classification.md), [sentiment and urgency architecture](../architecture/sentiment-urgency.md), [draft generation architecture](../architecture/draft-generation.md), and [roadmap](../tasks/roadmap.md).

- **LLM integration** connects backend code to a provider API and handles request and service failures.
- **Prompt engineering** shapes the instructions, context, and examples a model receives.
- **Structured outputs** use a machine-readable schema so the application can verify the response format and supported values. The three services use the [shared validation layer](../architecture/structured-output-validation.md).
- **Response evaluation** measures how well model behavior meets defined expectations on representative cases.

See [prompts](prompts.md), [classification](classification.md), and [evaluation](evaluation.md) for what each document will track.
