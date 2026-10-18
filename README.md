# GenAIOps na skillach w Microsoft Foundry – minimalny przykład

Zachowanie agenta (polityka obsługi zgłoszeń) żyje w pliku `SKILL.md` w Git,
a nie w kodzie agenta. Zmiana zachowania przechodzi ten sam cykl co kod:
**PR → walidacja → staging → ewaluacja → akceptacja → produkcja → monitoring/rollback**.

> Skills API w Foundry jest w **preview** (nagłówek `Foundry-Features: Skills=V1Preview`).
> Nazwy metod SDK i inputy GitHub Action sprawdź w aktualnej dokumentacji przed użyciem.

## Struktura

```
skills/support-policy/SKILL.md     # "artefakt" – zachowanie agenta
evals/support-policy.json          # zbiór testowy + lista ewaluatorów Foundry
scripts/validate_skill.py          # lint SKILL.md (bez kosztów LLM)
scripts/foundry_skills.py          # publish / pin staging / promote / rollback
scripts/bootstrap_foundry.py       # jednorazowo: skill v1, toolboxy, połączenia, agenci
infra/                             # Terraform: całe środowisko bez klikania
.github/workflows/genaiops-skill.yml
```

## Postawienie wszystkiego Terraformem

Co robi `terraform apply`:

| Warstwa | Jak | Co powstaje |
|---|---|---|
| Azure (natywnie) | `azapi`, `azurerm` | resource group, zasób Foundry, projekt, deployment modelu |
| Tożsamość (natywnie) | `azuread`, `azurerm` | aplikacja dla GitHub + 3 federated credentials (OIDC), role Foundry User dla: GitHub, Ciebie, tożsamości projektu |
| GitHub (natywnie) | `github` | 5 zmiennych Actions, środowisko `production` z wymaganą akceptacją, tylko z `main` |
| Foundry data-plane | `local-exec` → `bootstrap_foundry.py` | skill v1, 2 toolboxy, 2 połączenia, 2 agentów |

Ostatnia warstwa to API w preview, którego nie obsługuje jeszcze żaden provider Terraform.
Skrypt jest idempotentny: ponowne uruchomienie niczego nie dubluje.

### Wymagania lokalne

```bash
az login                                  # konto z Owner na subskrypcji + prawo do tworzenia aplikacji w Entra ID
azd auth login && azd extension install microsoft.foundry
pip install azure-ai-projects azure-identity
export GITHUB_TOKEN=<fine-grained PAT: Administration, Variables, Environments = Read/Write na tym repo>
```

### Uruchomienie

```bash
# 1. repo musi istnieć w GitHub przed apply
gh repo create genaiops-skills-demo --private --source . --push

# 2. infrastruktura + bootstrap
cd infra
cp terraform.tfvars.example terraform.tfvars    # uzupełnij
terraform init
terraform apply

# 3. sprzątanie po demo
terraform destroy
```

`apply` trwa ok. 10 minut, w tym 3 minuty celowego czekania na propagację RBAC.
Jeśli bootstrap się wyłoży (np. zmiana API w preview), infrastruktura zostaje - popraw skrypt
i uruchom go ręcznie: `FOUNDRY_PROJECT_ENDPOINT=$(terraform output -raw project_endpoint) python ../scripts/bootstrap_foundry.py`,
albo ustaw `run_bootstrap = false` i utwórz agentów w portalu.

`terraform destroy` usuwa zasób Foundry razem ze skillami, toolboxami i agentami.
Usunięty zasób AI Services jest przez 48 h w stanie *soft-delete* - przy ponownym `apply`
z tym samym `prefix` użyj innego prefiksu albo zrób purge:
`az cognitiveservices account purge -g <rg> -n <prefix>-foundry -l <region>`.

## Co powstaje w Foundry

| Zasób | Rola |
|---|---|
| Toolbox `support-toolbox-prod` | odwołuje się do skilla **bez wersji** → zawsze `default_version` |
| Toolbox `support-toolbox-staging` | przypinany przez pipeline do **konkretnej** wersji kandydata |
| Agent `support-agent` | produkcyjny, podpięty do toolboxa prod (MCP) |
| Agent `support-agent-staging` | ten sam agent, podpięty do toolboxa staging |
| Deployment modelu-sędziego | np. `gpt-4.1-mini`, używany przez ewaluatory AI |

Uprawnienia: tożsamość pipeline'u (federated credential / OIDC) z rolą **Foundry User** na projekcie.

## Przebieg

1. **Zmiana** – ktoś edytuje `SKILL.md` i otwiera PR.
2. **Lint** – `validate_skill.py` sprawdza format (nazwa, opis bez cudzysłowów, treść).
3. **Publish** – nowa, niezmienna wersja skilla w Foundry. Produkcja jej **nie widzi**,
   bo `default_version` się nie zmienia.
4. **Staging** – powstaje nowa wersja toolboxa staging przypięta do nowej wersji skilla
   i od razu zostaje jego `default_version` (toolbox też ma wersje - bez promocji
   endpoint MCP serwowałby starą).
5. **Ewaluacja** – `microsoft/ai-agent-evals` porównuje agenta staging z produkcyjnym
   na tym samym zbiorze pytań. Wyniki trafiają do podsumowania runa w GitHub Actions i do portalu Foundry.
6. **Bramka** – merge do `main` + akceptacja w środowisku `production` (required reviewers).
7. **Promocja** – `default_version` = nowa wersja. Agent produkcyjny ładuje nowy skill
   **bez redeployu kodu**.
8. **Rollback** – `python scripts/foundry_skills.py rollback support-policy <poprzednia>`
   (zmiana tylko metadanych, natychmiastowa).
9. **Monitoring** – tracing i ciągła ewaluacja w Foundry na ruchu produkcyjnym; nowe trudne
   przypadki dopisujesz do `evals/support-policy.json` i pętla się zamyka.

## Demo lokalnie

```bash
python scripts/validate_skill.py
export FOUNDRY_PROJECT_ENDPOINT="https://<konto>.services.ai.azure.com/api/projects/<projekt>"
az login
python scripts/foundry_skills.py publish support-policy        # -> np. 2
python scripts/foundry_skills.py pin     support-policy 2
python scripts/foundry_skills.py promote support-policy 2
```

Alternatywa bez Pythona: `azd ai skill create/update`, `azd ai toolbox ...`.
