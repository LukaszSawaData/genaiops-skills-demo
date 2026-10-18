output "project_endpoint" {
  value = local.project_endpoint
}

output "github_client_id" {
  value = azuread_application.gh.client_id
}

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "portal" {
  value = "https://ai.azure.com"
}
