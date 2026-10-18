variable "subscription_id" {
  type = string
}

variable "location" {
  type    = string
  default = "swedencentral"
}

variable "prefix" {
  description = "Krótki, unikalny prefiks (małe litery/cyfry) - z niego powstaje subdomena Foundry"
  type        = string
}

variable "model_name" {
  type    = string
  default = "gpt-4.1-mini"
}

variable "model_version" {
  type    = string
  default = "2025-04-14"
}

variable "model_capacity" {
  description = "Tysiące tokenów na minutę (TPM)"
  type        = number
  default     = 30
}

variable "github_owner" {
  description = "Login lub organizacja GitHub"
  type        = string
}

variable "github_repo" {
  description = "Nazwa istniejącego repo (bez ownera)"
  type        = string
  default     = "genaiops-skills-demo"
}

variable "github_reviewer" {
  description = "Login osoby zatwierdzającej wdrożenia na produkcję"
  type        = string
}

variable "run_bootstrap" {
  description = "Czy po postawieniu infry utworzyć skill, toolboxy i agentów (wymaga Pythona i azd lokalnie)"
  type        = bool
  default     = true
}
