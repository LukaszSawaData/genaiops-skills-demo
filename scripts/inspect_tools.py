import os, sys, json
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

agent = sys.argv[1] if len(sys.argv) > 1 else "support-agent"
with AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                     credential=DefaultAzureCredential(), allow_preview=True) as p:
    r = p.get_openai_client().responses.create(
        input="Wypisz nazwy wszystkich dostępnych narzędzi.",
        extra_body={"agent_reference": {"name": agent, "type": "agent_reference"}},
    )
    for item in r.output:
        if item.type == "mcp_list_tools":
            print("NARZĘDZIA Z TOOLBOXA:")
            for t in item.tools:
                print(" -", t.name, "|", (t.description or "")[:100])
        elif item.type != "message":
            print("[inne]", item.type)
