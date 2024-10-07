import test from "node:test";
import assert from "node:assert/strict";
import { mergeQueue, mergeSnapshot } from "../src/queue.mjs";

test("an older queue response cannot replace the selected incident's newer status", () => {
  const initial = [
    { id: "a", revision: 1, status: "awaiting_approval" },
    { id: "b", revision: 2, status: "new" },
  ];
  const detail = mergeSnapshot(initial, {
    id: "a",
    revision: 4,
    status: "resolved",
  });
  const raced = mergeQueue(detail, [
    { id: "a", revision: 2, status: "approved" },
    { id: "b", revision: 3, status: "diagnosing" },
  ]);
  assert.equal(raced[0].status, "resolved");
  assert.equal(raced[1].status, "diagnosing");
  assert.equal(
    mergeSnapshot(raced, { id: "a", revision: 1, status: "new" })[0].status,
    "resolved"
  );
});
