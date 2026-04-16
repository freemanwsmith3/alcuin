import os
import logging

logger = logging.getLogger(__name__)

VAULT_URL = os.environ.get("AZURE_KEY_VAULT_URL")


def load_secrets() -> None:
    """Fetch all secrets from Azure Key Vault and inject into os.environ.

    Only runs if AZURE_KEY_VAULT_URL is set. Uses the VM's managed identity
    automatically — no credentials needed.
    """
    if not VAULT_URL:
        return

    from azure.identity import ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=VAULT_URL, credential=ManagedIdentityCredential())

    for secret in client.list_properties_of_secrets():
        try:
            value = client.get_secret(secret.name).value
            # Convert Key Vault hyphens back to underscores for env var names
            env_key = secret.name.replace("-", "_")
            os.environ[env_key] = value
        except Exception:
            logger.warning("Failed to load secret %s from Key Vault", secret.name)

    logger.info("Loaded secrets from Key Vault: %s", VAULT_URL)
