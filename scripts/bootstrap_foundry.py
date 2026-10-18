"""Jednorazowy, idempotentny bootstrap: skill v1 + agenci prod/staging z jego treścią."""
import os
import sys

from azure.ai.projects.models import CreateSkillVersionFromFilesBody
from azure.core.exceptions import ResourceNotFoundError

sys.path.insert(0, os.path.dirname(__file__))
from foundry_skills import PROD_AGENT, STAGING_AGENT, client, deploy_agent, zip_skill  # noqa: E402

SKILL = "support-policy"


def exists(fn, *args, **kwargs) -> bool:
    try:
        fn(*args, **kwargs)
        return True
    except ResourceNotFoundError:
        return False


def main() -> None:
    with client() as p:
        if exists(p.beta.skills.get, name=SKILL):
            version = p.beta.skills.get(name=SKILL).default_version
            print(f"[skill] {SKILL} istnieje (default_version={version})")
        else:
            created = p.beta.skills.create_from_files(
                SKILL,
                content=CreateSkillVersionFromFilesBody(files=[(f"{SKILL}.zip", zip_skill(SKILL))]),
            )
            version = created.version
            p.beta.skills.update(SKILL, default_version=version)
            print(f"[skill] utworzono {SKILL} v{version}")

        for agent in (PROD_AGENT, STAGING_AGENT):
            if exists(p.agents.get, agent_name=agent):
                print(f"[agent] {agent} istnieje")
            else:
                print(f"[agent] utworzono {deploy_agent(p, agent, SKILL, version)}")
    print("Bootstrap zakończony.")


if __name__ == "__main__":
    main()
