locals {
  foundry_user_role_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/53ca6127-db72-4b80-b1b0-d745d6d5456d"
  gh_subject_prefix    = "repo:${var.github_owner}/${var.github_repo}"
  gh_issuer            = "https://token.actions.githubusercontent.com"
}

# GitHub Actions identity: managed identity + OIDC (no Entra app registration needed)
resource "azurerm_user_assigned_identity" "gh" {
  name                = "id-${var.prefix}-github"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
}

resource "azurerm_federated_identity_credential" "gh_pr" {
  name                = "gh-pr"
  resource_group_name = azurerm_resource_group.rg.name
  parent_id           = azurerm_user_assigned_identity.gh.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = local.gh_issuer
  subject             = "${local.gh_subject_prefix}:pull_request"
}

resource "azurerm_federated_identity_credential" "gh_main" {
  name                = "gh-main"
  resource_group_name = azurerm_resource_group.rg.name
  parent_id           = azurerm_user_assigned_identity.gh.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = local.gh_issuer
  subject             = "${local.gh_subject_prefix}:ref:refs/heads/main"
  depends_on          = [azurerm_federated_identity_credential.gh_pr]
}

resource "azurerm_federated_identity_credential" "gh_prod" {
  name                = "gh-prod"
  resource_group_name = azurerm_resource_group.rg.name
  parent_id           = azurerm_user_assigned_identity.gh.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = local.gh_issuer
  subject             = "${local.gh_subject_prefix}:environment:production"
  depends_on          = [azurerm_federated_identity_credential.gh_main]
}

resource "azurerm_role_assignment" "gh_foundry" {
  scope              = azapi_resource.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azurerm_user_assigned_identity.gh.principal_id
  principal_type     = "ServicePrincipal"
}

resource "azurerm_role_assignment" "me_foundry" {
  scope              = azapi_resource.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "project_foundry" {
  scope              = azapi_resource.foundry.id
  role_definition_id = local.foundry_user_role_id
  principal_id       = azapi_resource.project.identity[0].principal_id
  principal_type     = "ServicePrincipal"
}

resource "time_sleep" "rbac" {
  create_duration = "180s"
  depends_on      = [azurerm_role_assignment.me_foundry, azurerm_role_assignment.project_foundry]
}
