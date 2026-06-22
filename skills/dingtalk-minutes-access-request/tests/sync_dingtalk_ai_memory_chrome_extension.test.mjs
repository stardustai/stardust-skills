import test from "node:test";
import assert from "node:assert/strict";

import {
  clickSendRequest,
  GET_PERMISSION_REQUEST_MESSAGE_FIELD_STATE_JS,
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
  const fieldLocator = {
    fill: async (value) => calls.push(["fill", value]),
  };
  const fieldsLocator = {
    count: async () => 2,
    nth: (index) => {
      assert.equal(index, 1);
      return fieldLocator;
    },
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
      evaluate: async (pageFunction, arg) => {
        assert.equal(pageFunction, GET_PERMISSION_REQUEST_MESSAGE_FIELD_STATE_JS);
        if (arg?.requestMessage) {
          assert.deepEqual(arg, { index: 0, requestMessage: "测试申请理由" });
          calls.push(["read"]);
          return { found: true, index: 0, filled: true };
        }
        assert.deepEqual(arg, {});
        calls.push(["select"]);
        return { found: true, index: 0, selector_index: 1, filled: false };
      },
      locator: (selector) => {
        assert.equal(selector, "textarea,input,[contenteditable='true'],[role='textbox']");
        return fieldsLocator;
      },
      waitForTimeout: async () => {},
    },
  };

  const clicked = await clickSendRequest(tab, "测试申请理由");

  assert.equal(clicked, true);
  assert.deepEqual(calls, [["select"], ["fill", "测试申请理由"], ["read"], ["click"]]);
});

test("clickSendRequest does not send when the reason is not read back", async () => {
  const calls = [];
  const fieldLocator = {
    fill: async (value) => calls.push(["fill", value]),
  };
  const fieldsLocator = {
    count: async () => 2,
    nth: () => fieldLocator,
  };
  const sendButtonLocator = {
    count: async () => 1,
    isEnabled: async () => true,
    click: async () => calls.push(["click"]),
  };
  const tab = {
    playwright: {
      getByRole: () => sendButtonLocator,
      evaluate: async (_pageFunction, arg) => {
        if (arg?.requestMessage) {
          calls.push(["read_failed"]);
          return { found: true, index: 0, selector_index: 1, filled: false, reason: "message_not_read_back" };
        }
        calls.push(["select"]);
        return { found: true, index: 0, selector_index: 1, filled: false };
      },
      locator: () => fieldsLocator,
      waitForTimeout: async () => {},
    },
  };

  const clicked = await clickSendRequest(tab, "测试申请理由");

  assert.equal(clicked, false);
  assert.deepEqual(calls, [["select"], ["fill", "测试申请理由"], ["read_failed"]]);
});
