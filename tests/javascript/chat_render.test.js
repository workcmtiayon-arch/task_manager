import test from "node:test";
import assert from "node:assert/strict";

globalThis.document = {
  getElementById() { return null; },
  createElement() {
    let text = "";
    return {
      set textContent(value) { text = String(value); },
      get innerHTML() {
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      },
    };
  },
};

const { escapeHtml } = await import("../../static/javascript/chat/helpers.js");

test("escapeHtml protects quoted HTML attributes in uploaded filenames", () => {
  const payload = 'photo.png" onerror="alert(1)';
  const escaped = escapeHtml(payload);

  assert.equal(escaped, "photo.png&quot; onerror=&quot;alert(1)");
  assert.doesNotMatch(escaped, /(?<!&quot;)\"/);
});
