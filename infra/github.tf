# Repo musi istnieć (git push przed terraform apply)
data "github_user" "reviewer" {
  username = var.github_reviewer
}

locals {
  gh_vars = {
    FOUNDRY_PROJECT_ENDPOINT = local.project_endpoint
    AZURE_CLIENT_ID          = azurerm_user_assigned_identity.gh.client_id
    AZURE_TENANT_ID          = data.azurerm_client_config.current.tenant_id
    AZURE_SUBSCRIPTION_ID    = var.subscription_id
    JUDGE_MODEL_DEPLOYMENT   = azapi_resource.model.name
  }
}

resource "github_actions_variable" "vars" {
  for_each      = local.gh_vars
  repository    = var.github_repo
  variable_name = each.key
  value         = each.value
}

# Bramka jakości: promocja na prod wymaga akceptacji człowieka
resource "github_repository_environment" "production" {
  repository  = var.github_repo
  environment = "production"

  reviewers {
    users = [data.github_user.reviewer.id]
  }

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "main_only" {
  repository     = var.github_repo
  environment    = github_repository_environment.production.environment
  branch_pattern = "main"
}

# GitHub OIDC wysyła subject z numerycznymi ID: repo:<owner>@<owner_id>/<repo>@<repo_id>:...
data "github_user" "owner" {
  username = var.github_owner
}

data "github_repository" "repo" {
  full_name = "${var.github_owner}/${var.github_repo}"
}
