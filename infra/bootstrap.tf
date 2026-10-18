# Skille, toolboxy i agenci to data-plane API w preview - brak zasobów Terraform.
# Terraform woła idempotentny skrypt (drugie uruchomienie niczego nie dubluje).
resource "terraform_data" "bootstrap" {
  count = var.run_bootstrap ? 1 : 0

  triggers_replace = [local.project_endpoint, azapi_resource.model.name]

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = "python scripts/bootstrap_foundry.py"
    environment = {
      FOUNDRY_PROJECT_ENDPOINT = local.project_endpoint
      MODEL_DEPLOYMENT         = azapi_resource.model.name
    }
  }

  depends_on = [azapi_resource.model, time_sleep.rbac]
}
