import test from "node:test";
import assert from "node:assert/strict";
import { Api } from "../src/api.mjs";

test("credentialed API calls cannot leave the application API path", async () => {
  let calls = 0;
  const api = new Api(
    "secret",
    () => {},
    async () => {
      calls++;
      return new Response("{}");
    }
  );
  await assert.rejects(() => api.call("https://untrusted.test/steal"));
  await assert.rejects(() => api.call("//untrusted.test/api"));
  assert.equal(calls, 0);
});
test("expired sessions clear credentials and validation errors stay readable", async () => {
  let cleared = 0;
  const api = new Api(
    "secret",
    () => cleared++,
    async () =>
      new Response(JSON.stringify({ detail: "Expired" }), { status: 401 })
  );
  await assert.rejects(() => api.call("/api/me"), /Expired/);
  assert.equal(cleared, 1);
  const validation = new Api(
    "secret",
    () => {},
    async () =>
      new Response(JSON.stringify({ detail: [{ msg: "Title is required" }] }), {
        status: 422,
      })
  );
  await assert.rejects(
    () => validation.call("/api/incidents"),
    /Title is required/
  );
});

test("request functions are invoked without an API-instance receiver", async () => {
  const api = new Api(
    "token",
    () => {},
    async function () {
      assert.equal(this, undefined);
      return new Response("{}");
    }
  );
  await api.call("/api/me");
});
