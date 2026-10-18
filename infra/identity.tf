# Rola "Foundry User" (dawniej "Azure AI User") - po ID, bo nazwa się zmienia
locals {
  foundry_user_role_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/53ca6127-db72-4b80-b1b0-d745d6d5456d"
}

# --- Tożsamość GitHub Actions (OIDC, bez sekretów) ---
resource "azuread_application" "gh" {
  display_name = "gh-${var.prefix}-genaiops"
}

resource "azuread_service_principal" "gh" {
  client_id = azuread_application.gh.client_id
}

locals {
  oidc_subjects = {
    pr   = "repo:${var.github_owner}/${var.github_repo}:pull_request"
    main = "repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/main"
    prod = "repo:${var.github_owner}/${var.github_repo}:environment:production"
  }
}

resource "azuread_application_federated_identity_credential" "gh" {
  for_each       = local.oidc_subjects
  application_id = azuread_application.gh.id
  display_name   = "gh-${each.key}"
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = each.value
  audiences      = ["api://AzureADTokenExchange"]
}

# --- Uprawnienia do Foundry ---
resource "azurerm_role_assignment" "gh_foundry" {
  scope              = azapi_resource.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azuread_service_principal.gh.object_id
}

# Ty (osoba uruchamiająca terraform) - potrzebne do bootstrapu skilli/agentów
resource "azurerm_role_assignment" "me_foundry" {
  scope              = azapi_resource.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = data.azurerm_client_config.current.object_id
}

# Tożsamość projektu - agenci promptowi wołają nią toolbox (MCP)
resource "azurerm_role_assignment" "project_foundry" {
  scope              = azapi_resource.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azapi_resource.project.identity[0].principal_id
}

# Propagacja RBAC trwa kilka minut - bez tego bootstrap dostaje 403
resource "time_sleep" "rbac" {
  create_duration = "180s"
  depends_on = [
    azurerm_role_assignment.me_foundry,
    azurerm_role_assignment.project_foundry,
  ]
}
