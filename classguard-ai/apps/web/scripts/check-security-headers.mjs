import assert from "node:assert/strict";

// Exercise the running production server, including non-page responses. Set
// CLASSGUARD_TEST_URL only to a development deployment you are authorized to test.
const base = new URL(process.env.CLASSGUARD_TEST_URL || "http://127.0.0.1:3000");

for (const path of ["/people", "/join", "/icon.svg", "/security-check-not-found"]) {
  const response = await fetch(new URL(path, base), {
    redirect: "error",
    signal: AbortSignal.timeout(10_000),
  });
  assert.equal(response.status, path === "/security-check-not-found" ? 404 : 200);
  const policy = response.headers.get("content-security-policy") || "";
  assert.match(policy, /(?:^|;)\s*frame-ancestors\s+'none'\s*(?:;|$)/);
  assert.match(policy, /(?:^|;)\s*base-uri\s+'self'\s*(?:;|$)/);
  assert.match(policy, /(?:^|;)\s*object-src\s+'none'\s*(?:;|$)/);
  assert.equal(response.headers.get("x-frame-options"), "DENY");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  assert.match(response.headers.get("permissions-policy") || "", /camera=\(self\)/);
  assert.equal(response.headers.get("x-powered-by"), null);
  console.log(`PASS ${path}: framing, MIME, referrer and permission headers`);
  await response.body?.cancel();
}
