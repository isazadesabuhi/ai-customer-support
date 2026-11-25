# AI engineering notes

The reusable OpenAI client is implemented. Future tasks will use it for support-specific workflows. See the [LLM integration architecture](../architecture/llm-integration.md) and the [roadmap](../tasks/roadmap.md).

- **LLM integration** connects backend code to a provider API and handles request and service failures.
- **Prompt engineering** shapes the instructions, context, and examples a model receives.
- **Structured outputs** express a model response in a machine-readable schema so code can validate and use it.
- **Response evaluation** measures how well model behavior meets defined expectations on representative cases.

See [prompts](prompts.md), [classification](classification.md), and [evaluation](evaluation.md) for what each document will track.
