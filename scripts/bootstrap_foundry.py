"""Jednorazowy, idempotentny bootstrap data-plane Foundry (wołany przez Terraform).

Tworzy, jeśli nie istnieją:
  1. skill  support-policy (wersja 1 z repo)
  2. toolbox support-toolbox-prod     -> skill bez wersji (śledzi default_version skilla)
     toolbox support-toolbox-staging  -> skill przypięty do konkretnej wersji
  3. połączenia (project managed identity) do endpointów MCP obu toolboxów
  4. agenci support-agent i support-agent-staging (prompt agents z narzędziem MCP = toolbox)

Skills/Toolbox API są w preview - nazwy metod mogą się zmienić.
"""
import os
import subprocess
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CreateSkillVersionFromFilesBody,
    MCPTool,
    PromptAgentDefinition,
    ToolboxSkillReference,
)
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

sys.path.insert(0, os.path.dirname(__file__))
from foundry_skills import zip_skill  # noqa: E402

ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL = os.environ.get("MODEL_DEPLOYMENT", "gpt-4.1-mini")
SKILL = "support-policy"

ENVS = {
    # nazwa agenta      : (toolbox,                  przypięta wersja skilla?)
    "support-agent": ("support-toolbox-prod", False),
    "support-agent-staging": ("support-toolbox-staging", True),
}

INSTRUCTIONS = (
    "Jesteś agentem wsparcia klienta. Przed każdą odpowiedzią załaduj skill "
    f"'{SKILL}' z dostępnych zasobów i stosuj go bezwzględnie."
)


def exists(fn, *args, **kwargs) -> bool:
    try:
        fn(*args, **kwargs)
        return True
    except ResourceNotFoundError:
        return False


def toolbox_url(name: str) -> str:
    # endpoint "konsumencki" - serwuje default_version toolboxa
    return f"{ENDPOINT}/toolboxes/{name}/mcp?api-version=v1"


def ensure_skill(p: AIProjectClient) -> str:
    if exists(p.beta.skills.get, name=SKILL):
        v = p.beta.skills.get(name=SKILL).default_version
        print(f"[skill] {SKILL} istnieje (default_version={v})")
        return v
    created = p.beta.skills.create_from_files(
        SKILL,
        content=CreateSkillVersionFromFilesBody(files=[(f"{SKILL}.zip", zip_skill(SKILL))]),
    )
    p.beta.skills.update(SKILL, default_version=created.version)
    print(f"[skill] utworzono {SKILL} v{created.version}")
    return created.version


def ensure_toolbox(p: AIProjectClient, name: str, pinned_version: str | None) -> None:
    try:
        versions = list(p.toolboxes.list_versions(name=name))
    except ResourceNotFoundError:
        versions = []
    if versions:
        print(f"[toolbox] {name} istnieje")
        return
    ref = ToolboxSkillReference(name=SKILL, version=pinned_version) if pinned_version \
        else ToolboxSkillReference(name=SKILL)
    tv = p.toolboxes.create_version(name=name, description=f"{name}", tools=[], skills=[ref])
    print(f"[toolbox] utworzono {name} v{tv.version} (pierwsza wersja = domyślna)")


def ensure_connection(toolbox: str) -> str:
    """Połączenie, którym agent uwierzytelnia się do toolboxa tożsamością projektu."""
    conn = f"{toolbox}-auth"
    subprocess.run(["azd", "ai", "project", "set", ENDPOINT], check=True)
    r = subprocess.run(
        ["azd", "ai", "connection", "create", conn,
         "--kind", "remote-tool",
         "--target", toolbox_url(toolbox),
         "--auth-type", "project-managed-identity",
         "--no-prompt"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print(f"[connection] utworzono {conn}")
    elif "exist" in (r.stderr + r.stdout).lower():
        print(f"[connection] {conn} istnieje")
    else:
        print(r.stdout, r.stderr)
        raise SystemExit(f"Nie udało się utworzyć połączenia {conn}")
    return conn


def ensure_agent(p: AIProjectClient, agent: str, toolbox: str, conn: str) -> None:
    if exists(p.agents.get, agent_name=agent):
        print(f"[agent] {agent} istnieje")
        return
    a = p.agents.create_version(
        agent_name=agent,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=INSTRUCTIONS,
            tools=[MCPTool(
                server_label="toolbox",
                server_url=toolbox_url(toolbox),
                require_approval="never",
                project_connection_id=conn,
            )],
        ),
    )
    print(f"[agent] utworzono {a.name}:{a.version}")


def main() -> None:
    with AIProjectClient(endpoint=ENDPOINT, credential=DefaultAzureCredential(),
                         allow_preview=True) as p:
        version = ensure_skill(p)
        for agent, (toolbox, pinned) in ENVS.items():
            ensure_toolbox(p, toolbox, version if pinned else None)
            conn = ensure_connection(toolbox)
            ensure_agent(p, agent, toolbox, conn)
    print("Bootstrap zakończony.")


if __name__ == "__main__":
    main()
