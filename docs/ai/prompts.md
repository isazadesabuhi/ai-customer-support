# Prompt versions

`classification-v1` requests one category and a concise explanation for a single message. Its fixed instructions and examples use the `developer` role. The supplied message is a separate `user` input. Change the version when the classification policy or output contract changes. See the [source prompt](../../backend/ai/classification/prompts.py) and [classification architecture](../architecture/message-classification.md#prompt-and-input-contract).
