# Switch default model from DeepSeek V4 Pro to V4 Flash

Switched primary execution model from deepseek/deepseek-v4-pro (~$0.40/M input) to deepseek/deepseek-v4-flash (~$0.028/M input) for all agent loop steps. The Pro model is ~14x more expensive and slower due to full reasoning. Flash handles the vast majority of agent tasks adequately. The `deepfix` command is still pinned to Pro for difficult implementation work where reasoning depth matters.
