"""Operacje GenAIOps na skillach i agentach Foundry (lokalnie i w pipeline).

Skill jest wersjonowany w Foundry Skills API. Agent dostaje treść konkretnej wersji
skilla wstrzykniętą do instrukcji - każda zmiana skilla = nowa wersja agenta.

  publish  <skill>            -> nowa wersja skilla (NIE domyślna), wypisuje numer
  stage    <skill> <version>  -> nowa wersja agenta STAGING z tą wersją skilla
  promote  <skill> <version>  -> default_version = <version> + nowa wersja agenta PROD
  rollback <skill> <version>  -> to samo co promote
  current  <agent>            -> wypisuje <agent>:<najnowsza wersja>
"""
import io
import os
import re
import sys
import zipfile
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import CreateSkillVersionFromFilesBody, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

PROD_AGENT = "support-agent"
STAGING_AGENT = "support-agent-staging"
MODEL = os.environ.get("MODEL_DEPLOYMENT", "gpt-4.1-mini")

BASE_INSTRUCTIONS = (
    "Jesteś agentem wsparcia klienta. Poniższa polityka (skill) jest wiążąca "
    "i ma pierwszeństwo przed Twoją ogólną wiedzą."
)


def client() -> AIProjectClient:
    return AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )


def zip_skill(skill: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in Path("skills", skill).rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(Path("skills", skill)))
    return buf.getvalue()


def skill_body(zip_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        name = next(n for n in z.namelist() if n.endswith("SKILL.md"))
        text = z.read(name).decode("utf-8")
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()


def deploy_agent(p, agent: str, skill: str, version: str) -> str:
    body = skill_body(b"".join(p.beta.skills.download_version(skill, version)))
    a = p.agents.create_version(
        agent_name=agent,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=f"{BASE_INSTRUCTIONS}\n\n{body}",
            tools=[],
        ),
        metadata={"skill": skill, "skill_version": str(version)},
        description=f"{skill} v{version}",
    )
    return f"{a.name}:{a.version}"


def latest_agent_version(p, agent: str) -> str:
    v = next(iter(p.agents.list_versions(agent, limit=1, order="desc")))
    return f"{agent}:{v.version}"


def publish(skill: str) -> None:
    with client() as p:
        v = p.beta.skills.create_from_files(
            skill,
            content=CreateSkillVersionFromFilesBody(files=[(f"{skill}.zip", zip_skill(skill))]),
        )
        print(v.version)


def stage(skill: str, version: str) -> None:
    with client() as p:
        print(deploy_agent(p, STAGING_AGENT, skill, version))


def promote(skill: str, version: str) -> None:
    with client() as p:
        s = p.beta.skills.update(skill, default_version=version)
        print(f"{skill}: default_version = {s.default_version}", file=sys.stderr)
        print(deploy_agent(p, PROD_AGENT, skill, s.default_version))


def current(agent: str) -> None:
    with client() as p:
        print(latest_agent_version(p, agent))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"publish": publish, "stage": stage, "promote": promote,
     "rollback": promote, "current": current}[cmd](*args)
