data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}-genaiops"
  location = var.location
}

# Zasób Foundry (AI Services z włączonym zarządzaniem projektami)
resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name      = "${var.prefix}-foundry"
  parent_id = azurerm_resource_group.rg.id
  location  = var.location

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = "${var.prefix}-foundry"
      publicNetworkAccess    = "Enabled"
      disableLocalAuth       = true # tylko Entra ID, bez kluczy API
    }
  }
}

# Projekt Foundry
resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name      = "genaiops"
  parent_id = azapi_resource.foundry.id
  location  = var.location

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      displayName = "GenAIOps demo"
      description = "Agent supportowy sterowany skillami"
    }
  }
}

# Model: mózg agenta + sędzia dla ewaluatorów
resource "azapi_resource" "model" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = var.model_name
  parent_id = azapi_resource.foundry.id

  body = {
    sku = { name = "GlobalStandard", capacity = var.model_capacity }
    properties = {
      model = { format = "OpenAI", name = var.model_name, version = var.model_version }
    }
  }

  depends_on = [azapi_resource.project]
}

locals {
  project_endpoint = "https://${var.prefix}-foundry.services.ai.azure.com/api/projects/${azapi_resource.project.name}"
}
