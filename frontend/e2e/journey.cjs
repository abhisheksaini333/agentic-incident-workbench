const fs = require("fs");
const { chromium } = require("playwright-core");
const out = process.env.BROWSER_OUTPUT || "artifacts/browser";
const cfg = { demo_password: process.env.DEMO_PASSWORD };
if (!cfg.demo_password)
  throw Error("Set DEMO_PASSWORD for the seeded local accounts");
fs.mkdirSync(out, { recursive: true });
const origin = process.env.INCIDENT_ORIGIN || "http://127.0.0.1:8085";
(async () => {
  const session = await fetch(origin + "/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject: "acme.admin",
      password: cfg.demo_password,
    }),
  }).then((r) => r.json());
  const headers = {
    Authorization: "Bearer " + session.access_token,
    "Content-Type": "application/json",
  };
  const injected = await fetch(origin + "/api/simulation", {
    method: "POST",
    headers,
    body: JSON.stringify({ service: "heap-api", faults: ["memory_pressure"] }),
  });
  if (!injected.ok) throw Error("Demo fault injection failed");
  await fetch(origin + "/api/session", { method: "DELETE", headers });
  const browser = await chromium.launch({
    channel: process.env.BROWSER_CHANNEL === "bundled" ? undefined : "chrome",
    headless: true,
  });
  const errors = [];
  const pages = [];
  async function login(subject) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
    });
    const p = await context.newPage();
    pages.push(p);
    p.on("pageerror", (e) => {
      errors.push(e.message);
      console.error("PAGE", e.message);
    });
    p.on("console", (e) => console.log("CONSOLE", e.text()));
    await p.goto(origin);
    await p.getByLabel("Account", { exact: true }).fill(subject);
    await p.getByLabel("Password", { exact: true }).fill(cfg.demo_password);
    await p.getByRole("button", { name: "Sign in to workbench" }).click();
    await p
      .getByRole("button", { name: "Sign out" })
      .waitFor({ timeout: 5000 })
      .catch(async (e) => {
        console.log(await p.locator("body").innerText());
        await p.screenshot({ path: out + "/browser-login-failure.png" });
        throw e;
      });
    return p;
  }
  const title =
    process.env.INCIDENT_TEST_TITLE ||
    "Browser verified heap recovery " + Date.now();
  const op = await login("acme.operator");
  await op.getByRole("button", { name: "Open incident", exact: true }).click();
  await op.getByLabel("Incident title").fill(title);
  if (process.env.DIAGNOSIS_MODE)
    await op
      .getByLabel("Diagnosis approach")
      .selectOption(process.env.DIAGNOSIS_MODE);
  await op.getByRole("button", { name: "Collect evidence" }).click();
  await op.getByText("Review the exact plan", { exact: true }).waitFor();
  const rev = await login("acme.approver");
  await rev.getByRole("button").filter({ hasText: title }).click();
  await rev.getByText("Request changes instead", { exact: true }).click();
  await rev
    .getByLabel("Changes needed")
    .fill("Confirm the heap evidence before restart.");
  await rev.getByRole("button", { name: "Send change request" }).click();
  await rev
    .getByText("Changes requested by acme.approver:", { exact: false })
    .waitFor();
  await op
    .getByText("Changes requested by acme.approver:", { exact: false })
    .waitFor();
  await op.getByRole("button", { name: "Edit proposed plan" }).click();
  await op
    .getByLabel("Reason for this plan")
    .fill(
      "Heap memory is above threshold; restart the isolated simulator service."
    );
  await op.getByRole("button", { name: "Save new plan version" }).click();
  await rev.getByText("HUMAN DECISION / PLAN 2", { exact: true }).waitFor();
  await rev.getByRole("checkbox").check();
  await rev.getByRole("button", { name: "Approve this exact plan" }).click();
  await op.getByText("Recorded effects", { exact: true }).waitFor();
  await op
    .locator(".incident-heading .status")
    .filter({ hasText: "resolved" })
    .waitFor();
  if (process.env.DIAGNOSIS_MODE === "graph") {
    await op.getByText("Model review records", { exact: true }).click();
    await op.getByText("capacity / snapshot 1", { exact: true }).waitFor();
    await op
      .getByText("change and dependency / snapshot 1", { exact: true })
      .waitFor();
    await op
      .getByText("storage and queue / snapshot 1", { exact: true })
      .waitFor();
  }
  await op.screenshot({
    path: out + "/browser-foundation.png",
    fullPage: true,
  });
  const viewer = await login("acme.viewer");
  if (
    await viewer
      .getByRole("button", { name: "Open incident", exact: true })
      .count()
  )
    throw Error("Viewer create control exposed");
  await viewer.getByRole("button").filter({ hasText: title }).click();
  await viewer.getByText("Recorded effects", { exact: true }).waitFor();
  const beta = await login("beta.viewer");
  if (await beta.getByText(title, { exact: true }).count())
    throw Error("Cross-tenant row visible");
  await beta.getByRole("button", { name: "Sign out" }).click();
  await beta.getByRole("button", { name: "Sign in to workbench" }).waitFor();
  await op.setViewportSize({ width: 390, height: 844 });
  await op.screenshot({
    path: out + "/browser-foundation-mobile.png",
    fullPage: true,
  });
  if (errors.length) throw Error(errors.join("\n"));
  fs.writeFileSync(
    out + "/browser-foundation.json",
    JSON.stringify(
      {
        passed: true,
        diagnosis_mode: process.env.DIAGNOSIS_MODE || "rules",
        application_origin: origin,
        steps: [
          "operator create",
          "independent request changes",
          "versioned plan edit",
          "exact approval",
          "actual PostgreSQL worker and HTTP simulator recovery",
          "viewer read only",
          "tenant isolation",
          "logout",
          "mobile screenshot",
        ],
        page_errors: errors,
      },
      null,
      2
    )
  );
  await browser.close();
  console.log("Foundation browser journey passed");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
