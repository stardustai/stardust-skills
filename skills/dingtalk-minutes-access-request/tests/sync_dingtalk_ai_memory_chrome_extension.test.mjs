import test from "node:test";
import assert from "node:assert/strict";

import {
  clickSendRequest,
  waitForPermissionState,
} from "../scripts/sync_dingtalk_ai_memory_chrome_extension.mjs";

test("waitForPermissionState waits until the send-request button is rendered", async () => {
  const states = [
    { title: "产品部周会", body: "暂无权限访问", can_request: false, request_button_disabled: false, already_requested: false },
    { title: "产品部周会", body: "暂无权限访问", can_request: false, request_button_disabled: false, already_requested: false },
    { title: "产品部周会", body: "暂无权限访问", can_request: true, request_button_disabled: false, already_requested: false },
  ];
  let calls = 0;
  const tab = {
    playwright: {
      evaluate: async () => states[Math.min(calls++, states.length - 1)],
      waitForTimeout: async () => {},
    },
  };

  const state = await waitForPermissionState(tab, { timeoutMs: 1000, pollMs: 1 });

  assert.equal(state.can_request, true);
  assert.equal(calls, 3);
});

test("clickSendRequest fills the reason through Playwright before clicking send", async () => {
  const calls = [];
  const textareaLocator = {
    count: async () => 1,
    fill: async (value) => calls.push(["fill", value]),
  };
  const sendButtonLocator = {
    count: async () => 1,
    isEnabled: async () => true,
    click: async () => calls.push(["click"]),
  };
  const tab = {
    playwright: {
      getByRole: (role, options) => {
        assert.equal(role, "button");
        assert.equal(options.name, "发送申请");
        return sendButtonLocator;
      },
      locator: (selector) => {
        assert.equal(selector, "textarea");
        return textareaLocator;
      },
      waitForTimeout: async () => {},
    },
  };

  const clicked = await clickSendRequest(tab, "测试申请理由");

  assert.equal(clicked, true);
  assert.deepEqual(calls, [["fill", "测试申请理由"], ["click"]]);
});
