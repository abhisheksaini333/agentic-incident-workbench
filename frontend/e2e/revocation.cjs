const fs = require("fs");
const { chromium } = require("playwright-core");
const origin = process.env.INCIDENT_ORIGIN || "http://127.0.0.1:8085";
const password = process.env.DEMO_PASSWORD;
const output = process.env.BROWSER_OUTPUT || "artifacts/browser";
if (!password) throw Error("Set DEMO_PASSWORD for local seeded accounts");

(async () => {
  const response = await fetch(origin + "/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject: "acme.admin", password }),
  });
  const administrator = (await response.json()).access_token;
  if (!administrator) throw Error("Administrator sign-in failed");
  const headers = {
    Authorization: "Bearer " + administrator,
    "Content-Type": "application/json",
  };
  async function roles(values) {
    const result = await fetch(origin + "/api/accounts/acme.operator/roles", {
      method: "PUT",
      headers,
      body: JSON.stringify({ roles: values }),
    });
    if (!result.ok) throw Error("Role change failed");
  }
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL === "bundled" ? undefined : "chrome",
  });
  try {
    const page = await browser.newPage();
    let token = "";
    page.on("request", (request) => {
      if (request.url().endsWith("/api/me"))
        token = request.headers().authorization || token;
    });
    await page.goto(origin);
    await page.getByLabel("Account", { exact: true }).fill("acme.operator");
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in to workbench" }).click();
    await page
      .getByRole("button", { name: "Open incident", exact: true })
      .waitFor();
    await roles(["viewer"]);
    const denied = await fetch(origin + "/api/incidents", {
      method: "POST",
      headers: { Authorization: token, "Content-Type": "application/json" },
      body: JSON.stringify({
        service: "heap-api",
        title: "Revoked operator must not create",
      }),
    });
    if (denied.status !== 403)
      throw Error("Existing token retained operator authority");
    await page
      .getByRole("button", { name: "Open incident", exact: true })
      .waitFor({ state: "hidden", timeout: 15000 });
    await roles([]);
    const revoked = await fetch(origin + "/api/incidents", {
      headers: { Authorization: token },
    });
    if (revoked.status !== 401) throw Error("Revoked account retained access");
    await page
      .getByRole("button", { name: "Sign in to workbench" })
      .waitFor({ timeout: 15000 });
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(
      output + "/revocation.json",
      JSON.stringify(
        {
          passed: true,
          existing_token_write_status: denied.status,
          revoked_account_read_status: revoked.status,
          role_controls_refreshed: true,
          session_cleared: true,
        },
        null,
        2
      )
    );
    console.log("Live role and account revocation browser check passed");
  } finally {
    await roles(["operator"]);
    await fetch(origin + "/api/session", { method: "DELETE", headers });
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
