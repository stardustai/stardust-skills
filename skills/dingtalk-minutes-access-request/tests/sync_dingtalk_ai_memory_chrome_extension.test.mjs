import test from "node:test";
import assert from "node:assert/strict";

import {
  clickSendRequest,
  GET_DINGTALK_HISTORY_GATE_STATE_JS,
  GET_PERMISSION_REQUEST_MESSAGE_FIELD_STATE_JS,
  resolveDingTalkHistoryGate,
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

test("resolveDingTalkHistoryGate selects the configured DingTalk organization and returns to history", async () => {
  const calls = [];
  const targetOrg = "北京星尘纪元智能科技有限公司";
  const orgLocator = {
    isVisible: async () => true,
    click: async () => calls.push(["click_org", targetOrg]),
  };
  const tab = {
    url: async () => "https://oa.dingtalk.com/index.htm#/welcome",
    goto: async (url) => calls.push(["goto", url]),
    playwright: {
      evaluate: async (pageFunction, arg) => {
        assert.equal(pageFunction, GET_DINGTALK_HISTORY_GATE_STATE_JS);
        assert.deepEqual(arg, { targetOrgName: targetOrg });
        return {
          target_org_visible: true,
          target_org_name: targetOrg,
          stale_refresh_visible: false,
          has_secret_prompt: false,
          on_dingtalk_home: false,
          looks_logged_out: false,
        };
      },
      getByText: (text, options) => {
        assert.equal(text, targetOrg);
        assert.deepEqual(options, { exact: true });
        return {
          count: async () => 1,
          nth: (index) => {
            assert.equal(index, 0);
            return orgLocator;
          },
        };
      },
      waitForTimeout: async (ms) => calls.push(["wait", ms]),
      waitForLoadState: async () => calls.push(["load"]),
    },
  };

  const result = await resolveDingTalkHistoryGate(tab, { targetOrgName: targetOrg });

  assert.equal(result.acted, true);
  assert.equal(result.action, "select_org");
  assert.deepEqual(calls, [
    ["click_org", targetOrg],
    ["wait", 1500],
    ["goto", "https://oa.dingtalk.com/meeting_oa#/flash_minutes/history_list"],
    ["load"],
  ]);
});

test("resolveDingTalkHistoryGate stops on secret DingTalk prompts", async () => {
  const calls = [];
  const tab = {
    playwright: {
      evaluate: async () => ({
        has_secret_prompt: true,
        target_org_visible: false,
        stale_refresh_visible: false,
        looks_logged_out: true,
      }),
      getByText: () => {
        calls.push(["getByText"]);
        return {
          count: async () => 0,
          nth: () => {
            throw new Error("unexpected locator use");
          },
        };
      },
    },
  };

  const result = await resolveDingTalkHistoryGate(tab, {
    targetOrgName: "北京星尘纪元智能科技有限公司",
  });

  assert.equal(result.acted, false);
  assert.equal(result.action, "secret_prompt");
  assert.deepEqual(calls, []);
});

test("resolveDingTalkHistoryGate selects target org before honoring background secret text", async () => {
  const calls = [];
  const targetOrg = "北京星尘纪元智能科技有限公司";
  const orgLocator = {
    isVisible: async () => true,
    click: async () => calls.push(["click_org", targetOrg]),
  };
  const tab = {
    url: async () => "https://login.dingtalk.com/oauth2/challenge.htm#/welcome",
    goto: async (url) => calls.push(["goto", url]),
    playwright: {
      evaluate: async () => ({
        target_org_visible: true,
        target_org_name: targetOrg,
        stale_refresh_visible: false,
        has_secret_prompt: true,
        on_dingtalk_home: false,
        looks_logged_out: true,
      }),
      getByText: () => ({
        count: async () => 1,
        nth: () => orgLocator,
      }),
      waitForTimeout: async (ms) => calls.push(["wait", ms]),
      waitForLoadState: async () => calls.push(["load"]),
    },
  };

  const result = await resolveDingTalkHistoryGate(tab, { targetOrgName: targetOrg });

  assert.equal(result.acted, true);
  assert.equal(result.action, "select_org");
  assert.equal(calls[0][0], "click_org");
});

test("DingTalk gate state ignores hidden secret text when target org is visible", () => {
  const originalDocument = globalThis.document;
  const originalWindow = globalThis.window;
  const originalLocation = globalThis.location;
  const makeElement = (text, display) => ({
    innerText: text,
    textContent: text,
    getBoundingClientRect: () => ({ width: display === "none" ? 0 : 100, height: display === "none" ? 0 : 20 }),
  });
  const hidden = makeElement("请设置密码 短信验证码 使用钉钉扫码", "none");
  const target = makeElement("北京星尘纪元智能科技有限公司", "block");

  try {
    globalThis.window = {
      getComputedStyle: (el) => ({
        visibility: "visible",
        display: el === hidden ? "none" : "block",
      }),
    };
    globalThis.document = {
      title: "钉钉管理后台 - 钉钉统一身份认证",
      body: {
        innerText: "请设置密码 短信验证码 使用钉钉扫码 北京星尘纪元智能科技有限公司",
      },
      querySelectorAll: () => [hidden, target],
      querySelector: () => null,
    };
    globalThis.location = {
      href: "https://login.dingtalk.com/oauth2/challenge.htm#/welcome",
      hostname: "login.dingtalk.com",
      hash: "#/welcome",
      pathname: "/oauth2/challenge.htm",
    };

    const state = GET_DINGTALK_HISTORY_GATE_STATE_JS({
      targetOrgName: "北京星尘纪元智能科技有限公司",
    });

    assert.equal(state.target_org_visible, true);
    assert.equal(state.has_secret_prompt, false);
    assert.equal(state.looks_logged_out, false);
  } finally {
    globalThis.document = originalDocument;
    globalThis.window = originalWindow;
    globalThis.location = originalLocation;
  }
});
