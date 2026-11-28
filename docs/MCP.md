# Private MCP

The optional MCP server is launched as a local stdio subprocess by a compatible local MCP client. It uses the same SQLite database and domain services as the web application. Network transports, including Streamable HTTP, are not implemented or registered. MCP remains disabled by default.

Install the optional SDK and create an expiring, scoped credential for an existing adult member from a trusted local shell. The supported scopes are currently calendar, chores, shopping, meals and rewards; maintenance, vehicles, inventory and household-summary tools from the Homefront request are not yet available.

```sh
python -m pip install --require-hashes -r requirements-optional.lock
MCP_ENABLED=true DATA_DIR=./data python -m app.private_mcp issue <adult-username> --scopes calendar,shopping
```

Configure the local client to launch `python -m app.private_mcp serve` with the same `DATA_DIR`, `MCP_ENABLED=true`, and the issued `MCP_TOKEN` from its secret configuration. Scope names are `calendar`, `chores`, `shopping`, `meals`, and `rewards`. Read-only is the default. The database stores the token hash, expiry and revocation state. Tool calls and grant changes are audited without recording request text.

To allow grocery proposals, issue a credential with the `shopping` scope and `--allow-grocery-proposals`. Enable `MCP_ENABLED=true` on the web app so the associated member can review proposals in **More → Six**. The member must apply each proposal before its item is added. This workflow works with local AI inference disabled.

Use `python -m app.private_mcp revoke <adult-username> <credential-id>` under the same environment to revoke a credential. Compose users can build with `WITH_MCP=1` and launch the local stdio process using `docker compose exec -T` with the associated token in its environment. No public tunnel or LAN listener is supported. Cloud-hosted ChatGPT cannot directly reach an isolated LAN service; use compatible local stdio clients only. All mutations remain proposals requiring approval in the household app.
