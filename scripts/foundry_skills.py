"""GenAIOps: skill wersjonowany w Foundry, wstrzykiwany do instrukcji agenta.
  publish <skill> | stage <skill> <v> | promote <skill> <v> | rollback <skill> <v> | current <agent>
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


def client():
    return AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                           credential=DefaultAzureCredential(), allow_preview=True)


def zip_skill(skill):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in Path("skills", skill).rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(Path("skills", skill)))
    return buf.getvalue()


def skill_body(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        name = next(n for n in z.namelist() if n.endswith("SKILL.md"))
        text = z.read(name).decode("utf-8")
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()


def deploy_agent(p, agent, skill, version):
    body = skill_body(b"".join(p.beta.skills.download_version(skill, version)))
    a = p.agents.create_version(
        agent_name=agent,
        definition=PromptAgentDefinition(model=MODEL, tools=[],
                                         instructions=f"{BASE_INSTRUCTIONS}\n\n{body}"),
        metadata={"skill": skill, "skill_version": str(version)},
        description=f"{skill} v{version}",
    )
    return f"{a.name}:{a.version}"


def publish(skill):
    with client() as p:
        v = p.beta.skills.create_from_files(skill, content=CreateSkillVersionFromFilesBody(
            files=[(f"{skill}.zip", zip_skill(skill))]))
        print(v.version)


def stage(skill, version):
    with client() as p:
        print(deploy_agent(p, STAGING_AGENT, skill, version))


def promote(skill, version):
    with client() as p:
        s = p.beta.skills.update(skill, default_version=version)
        print(f"{skill}: default_version = {s.default_version}", file=sys.stderr)
        print(deploy_agent(p, PROD_AGENT, skill, s.default_version))


def current(agent):
    with client() as p:
        v = next(iter(p.agents.list_versions(agent, limit=1, order="desc")))
        print(f"{agent}:{v.version}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"publish": publish, "stage": stage, "promote": promote,
     "rollback": promote, "current": current}[cmd](*args)
