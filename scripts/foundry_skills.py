"""Operacje na skillach i toolboxach w Foundry używane przez pipeline.

Użycie:
  python scripts/foundry_skills.py publish  <skill>            -> tworzy nową wersję, wypisuje jej numer
  python scripts/foundry_skills.py pin      <skill> <version>  -> toolbox STAGING przypięty do tej wersji
  python scripts/foundry_skills.py promote  <skill> <version>  -> ustawia default_version (= produkcja)
  python scripts/foundry_skills.py rollback <skill> <version>  -> to samo co promote, dla czytelności logów

Wymaga: pip install azure-ai-projects azure-identity
Zmienne: FOUNDRY_PROJECT_ENDPOINT, STAGING_TOOLBOX (domyślnie support-toolbox-staging)
Skills API jest w preview - nazwy metod mogą się zmienić, sprawdź aktualną dokumentację.
"""
import io
import os
import sys
import zipfile
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CreateSkillVersionFromFilesBody,
    ToolboxSkillReference,
)
from azure.identity import DefaultAzureCredential


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


def publish(skill: str) -> None:
    with client() as p:
        v = p.beta.skills.create_from_files(
            skill,
            content=CreateSkillVersionFromFilesBody(
                files=[(f"{skill}.zip", zip_skill(skill))]
            ),
        )
        # Nowa wersja NIE staje się automatycznie domyślną - produkcja jej jeszcze nie widzi.
        print(v.version)


def pin_staging(skill: str, version: str) -> None:
    toolbox = os.environ.get("STAGING_TOOLBOX", "support-toolbox-staging")
    with client() as p:
        tv = p.toolboxes.create_version(
            name=toolbox,
            description=f"staging: {skill} v{version}",
            tools=[],
            skills=[ToolboxSkillReference(name=skill, version=version)],
        )
        # Nowa wersja toolboxa NIE jest aktywna, dopóki jej nie promujesz -
        # bez tego endpoint MCP stagingu dalej serwowałby starą wersję skilla.
        p.toolboxes.update(toolbox_name=toolbox, default_version=tv.version)
        print(f"{toolbox} -> aktywna wersja toolboxa {tv.version} ({skill} v{version})")


def promote(skill: str, version: str) -> None:
    with client() as p:
        s = p.beta.skills.update(skill, default_version=version)
        print(f"{skill}: default_version = {s.default_version}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"publish": publish, "pin": pin_staging, "promote": promote, "rollback": promote}[cmd](*args)
