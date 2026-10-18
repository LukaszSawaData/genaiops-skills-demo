terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    azapi   = { source = "Azure/azapi", version = "~> 2.0" }
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
    github  = { source = "integrations/github", version = "~> 6.0" }
    time    = { source = "hashicorp/time", version = "~> 0.12" }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "azapi" {}
provider "azuread" {}

# Token z env GITHUB_TOKEN (uprawnienia: repo admin / Variables + Environments)
provider "github" {
  owner = var.github_owner
}
