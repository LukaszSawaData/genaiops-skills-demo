"""Zadaj pytanie agentowi Foundry: python scripts/ask_agent.py <agent> "<pytanie>" """
import os, sys
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

agent, question = sys.argv[1], sys.argv[2]
with AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                     credential=DefaultAzureCredential(), allow_preview=True) as p:
    client = p.get_openai_client()
    r = client.responses.create(
        input=question,
        extra_body={"agent_reference": {"name": agent, "type": "agent_reference"}},
    )
    for item in r.output:
        if item.type != "message":
            print(f"  [narzędzie] {item.type}")
    print(f"\n{agent}:\n{r.output_text}\n")
