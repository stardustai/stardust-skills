import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";

const BROWSER_CLIENT_PATH =
  "/Users/derek/.codex/plugins/cache/openai-bundled/chrome/26.602.40724/scripts/browser-client.mjs";
const HISTORY_URL = "https://oa.dingtalk.com/meeting_oa#/flash_minutes/history_list";
const DEFAULT_BASE_DIR = "/Users/derek/Documents/memory/AI听记";
const DEFAULT_MIN_AGE_MINUTES = 15;
const DEFAULT_PERMISSION_REQUEST_MESSAGE =
  "AI自动抓取，用于会议纪要整理，如和工作内容无关或者涉及个人隐私，请拒绝";
const DEFAULT_DWS_BIN = "dws";
const PERMISSION_REQUEST_MESSAGE_FIELD_SELECTOR = "textarea,input,[contenteditable='true'],[role='textbox']";

const GET_PAGE_META_JS = () => ({
  title: document.title,
  url: location.href
});

const GET_TRANSCRIPT_STATE_JS = () => {
  const contents =
    document.querySelector('.fm-transcribe-text__variable-size-list > div') ||
    document.querySelector('[data-overlayscrollbars-contents]');
  if (!contents) return { found: false };
  let scroller = contents;
  let cur = contents;
  while (cur) {
    if (cur.scrollHeight > cur.clientHeight + 5) {
      scroller = cur;
      break;
    }
    cur = cur.parentElement;
  }
  const text = (contents.innerText || '').replace(/\u00a0/g, ' ');
  return {
    found: true,
    scrollTop: scroller.scrollTop,
    scrollHeight: scroller.scrollHeight,
    clientHeight: scroller.clientHeight,
    text
  };
};

const GET_AI_SUMMARY_JS = () => {
  const el =
    document.querySelector('.fm-full-text-summary__content') ||
    document.querySelector('.fm-full-text-summary') ||
    document.querySelector('.fm-tiptap-md-editor');
  if (!el) return { found: false };
  const text = (el.innerText || '').replace(/\u00a0/g, ' ').trim();
  return {
    found: true,
    className: String(el.className || ''),
    charCount: text.length,
    text
  };
};

const ENSURE_TRANSCRIPT_TAB_JS = () => {
  const normalize = (value) => ((value || '').replace(/\s+/g, ' ')).trim();
  const candidates = Array.from(document.querySelectorAll('div,span,button')).filter((el) => {
    const text = normalize(el.innerText || el.textContent);
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && (text === '转写' || text === 'Transcribe');
  });
  const target = candidates[0] || null;
  if (!target) return { clicked: false };
  target.click();
  return { clicked: true, text: normalize(target.innerText || target.textContent) };
};

const ENSURE_AI_SUMMARY_TAB_JS = () => {
  const normalize = (value) => ((value || '').replace(/\s+/g, ' ')).trim();
  const candidates = Array.from(document.querySelectorAll('div,span,button')).filter((el) => {
    const text = normalize(el.innerText || el.textContent);
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && (text === 'AI纪要' || text === 'AI Summary');
  });
  const target = candidates[0] || null;
  if (!target) return { clicked: false };
  target.click();
  return { clicked: true, text: normalize(target.innerText || target.textContent) };
};

export const GET_PERMISSION_REQUEST_MESSAGE_FIELD_STATE_JS = ({ index = 0, requestMessage = "" } = {}) => {
  const normalize = (value) => ((value || '').replace(/\s+/g, ' ')).trim();
  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  };
  const readValue = (el) => {
    const tagName = String(el.tagName || "").toUpperCase();
    if (tagName === "INPUT" || tagName === "TEXTAREA") return el.value || "";
    return el.innerText || el.textContent || "";
  };
  const scoreField = (el) => {
    const tagName = String(el.tagName || "").toUpperCase();
    const labelText = normalize([
      el.getAttribute("placeholder"),
      el.getAttribute("aria-label"),
      el.getAttribute("name"),
      el.getAttribute("id"),
      el.closest("label")?.innerText,
      el.parentElement?.innerText,
    ].filter(Boolean).join(" "));
    let score = 0;
    if (/申请|理由|备注|说明|原因|reason|message|remark|comment/i.test(labelText)) score += 10;
    if (tagName === "TEXTAREA") score += 4;
    if (el.getAttribute("role") === "textbox") score += 3;
    if (el.isContentEditable) score += 2;
    return score;
  };
  const fields = Array.from(document.querySelectorAll("textarea,input,[contenteditable='true'],[role='textbox']"))
    .map((el, selectorIndex) => ({ el, selectorIndex }))
    .filter(({ el }) => {
      const tagName = String(el.tagName || "").toUpperCase();
      if (!isVisible(el)) return false;
      if (tagName === "INPUT" && ["button", "checkbox", "file", "hidden", "radio", "submit"].includes(el.type)) return false;
      if (el.disabled || el.readOnly) return false;
      return true;
    })
    .sort((a, b) => scoreField(b.el) - scoreField(a.el));
  const numericIndex = Number(index || 0);
  const fieldEntry = fields[numericIndex] || null;
  if (!fieldEntry) {
    return {
      found: false,
      field_count: fields.length,
      reason: fields.length ? "field_index_missing" : "no_writable_field",
    };
  }
  const field = fieldEntry.el;
  const value = readValue(field);
  const expected = String(requestMessage || "");
  return {
    found: true,
    index: numericIndex,
    selector_index: fieldEntry.selectorIndex,
    field_count: fields.length,
    tag: field.tagName,
    role: field.getAttribute("role") || "",
    placeholder: field.getAttribute("placeholder") || "",
    filled: !!expected && normalize(value) === normalize(expected),
    value_len: value.length,
    reason: "",
  };
};

function emitProgress(message) {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  console.error(`[${hh}:${mm}:${ss}] ${message}`);
}

function sanitizeName(value) {
  const cleaned = String(value || "")
    .replace(/[\\/:*?"<>|\n\r\t]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\.+$/g, "");
  return cleaned || "untitled";
}

function parseLocalTimestamp(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (!match) return null;
  const [, year, month, day, hour = "00", minute = "00", second = "00"] = match;
  return new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second),
    0,
  );
}

function parseChinaTimestamp(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/);
  if (!match) return null;
  const [, year, month, day, hour = "00", minute = "00", second = "00"] = match;
  return new Date(Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour) - 8,
    Number(minute),
    Number(second),
    0,
  ));
}

function decodeRowKey(rowKey) {
  try {
    return Buffer.from(String(rowKey || ""), "hex").toString("utf8");
  } catch {
    return "";
  }
}

function buildTranscribeUrl(rowKey) {
  const decoded = decodeRowKey(rowKey);
  const match = decoded.match(/^v2uid(\d+)_[^_]+_(\d+)$/);
  if (match) {
    return `https://shanji.dingtalk.com/app/transcribes/${rowKey}/${match[1]}/${match[2]}?from=15`;
  }
  return `https://shanji.dingtalk.com/app/transcribes/${rowKey}?from=15`;
}

function buildMarkdownFilename(title, timestamp) {
  const yyyy = timestamp.getFullYear();
  const mm = String(timestamp.getMonth() + 1).padStart(2, "0");
  const dd = String(timestamp.getDate()).padStart(2, "0");
  const hh = String(timestamp.getHours()).padStart(2, "0");
  const mi = String(timestamp.getMinutes()).padStart(2, "0");
  return `${sanitizeName(title)} ${yyyy}-${mm}-${dd} ${hh}:${mi}.md`;
}

function buildSummaryMarkdown(rowKey, payload) {
  const aiSummary = String(payload.ai_summary || "").trimEnd() || "(empty ai_summary)";
  const transcript = String(payload.transcript || "").trimEnd() || "(empty transcript)";
  return [
    `<!-- row_key: ${rowKey} -->`,
    `<!-- source_url: ${payload.url || ""} -->`,
    "",
    "# AI Summary",
    "",
    aiSummary,
    "",
    "# Transcript",
    "",
    transcript,
    "",
  ].join("\n");
}

function execFileJson(bin, args, { timeoutMs = 30000 } = {}) {
  return new Promise((resolve, reject) => {
    execFile(bin, args, { encoding: "utf8", timeout: timeoutMs, maxBuffer: 64 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        const details = [error.message, stdout.trim(), stderr.trim()].filter(Boolean).join("\n");
        reject(new Error(details || `Command failed: ${bin} ${args.join(" ")}`));
        return;
      }
      const text = stdout.trim();
      if (!text) {
        reject(new Error(`Command returned empty stdout: ${bin} ${args.join(" ")}`));
        return;
      }
      try {
        resolve(JSON.parse(text));
      } catch (parseError) {
        reject(new Error(`Command returned non-JSON stdout: ${parseError.message}\n${text.slice(0, 1000)}`));
      }
    });
  });
}

function unwrapDwsResult(data) {
  if (!data || typeof data !== "object") return {};
  if (data.result && typeof data.result === "object") return data.result;
  return data;
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatParagraph(paragraph) {
  const speaker =
    paragraph?.speakerDisplay?.nickName ||
    paragraph?.nickName ||
    paragraph?.speakerNick ||
    "未知发言人";
  const start = formatDuration(paragraph?.startTime);
  const text = String(paragraph?.paragraph || paragraph?.text || "").replace(/\s+/g, " ").trim();
  return text ? `[${start}] ${speaker}: ${text}` : "";
}

async function fetchDwsSummary(rowKey, { dwsBin = DEFAULT_DWS_BIN, timeoutMs = 30000 } = {}) {
  const data = await execFileJson(
    dwsBin,
    ["minutes", "get", "summary", "--id", rowKey, "--format", "json"],
    { timeoutMs },
  );
  const result = unwrapDwsResult(data);
  return String(result.fullSummary || result.summary || result.content || "").trim();
}

async function fetchDwsTranscript(rowKey, { dwsBin = DEFAULT_DWS_BIN, timeoutMs = 30000, maxPages = 100 } = {}) {
  const paragraphs = [];
  const seenTokens = new Set();
  let nextToken = "";
  let pageCount = 0;

  while (pageCount < maxPages) {
    const args = ["minutes", "get", "transcription", "--id", rowKey, "--format", "json"];
    if (nextToken) args.splice(5, 0, "--next-token", nextToken);
    const data = await execFileJson(dwsBin, args, { timeoutMs });
    const result = unwrapDwsResult(data);
    const pageParagraphs =
      result.paragraphList ||
      result.paragraphs ||
      result.itemList ||
      [];
    if (Array.isArray(pageParagraphs)) paragraphs.push(...pageParagraphs);
    pageCount += 1;

    const candidateToken = String(result.nextToken || "").trim();
    if (!candidateToken) break;
    if (seenTokens.has(candidateToken)) {
      throw new Error(`DWS transcription pagination repeated nextToken: ${candidateToken}`);
    }
    seenTokens.add(candidateToken);
    nextToken = candidateToken;
  }

  if (pageCount >= maxPages && nextToken) {
    throw new Error(`DWS transcription pagination exceeded maxPages=${maxPages}`);
  }

  paragraphs.sort((a, b) => Number(a?.startTime || 0) - Number(b?.startTime || 0));
  const lines = paragraphs.map(formatParagraph).filter(Boolean);
  const transcript = lines.join("\n").trim();
  return [
    transcript,
    {
      source: "dws",
      page_count: pageCount,
      paragraph_count: paragraphs.length,
      line_count: lines.length,
      char_count: transcript.length,
    },
  ];
}

function walkMarkdownFiles(rootDir) {
  if (!fs.existsSync(rootDir)) return [];
  const out = [];
  const stack = [rootDir];
  while (stack.length) {
    const current = stack.pop();
    let entries = [];
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(fullPath);
      else if (entry.isFile() && entry.name.endsWith(".md")) out.push(fullPath);
    }
  }
  return out;
}

function captureExists(baseDir, rowKey) {
  const marker = `<!-- row_key: ${rowKey} -->`;
  for (const markdownPath of walkMarkdownFiles(baseDir)) {
    let head = "";
    try {
      head = fs.readFileSync(markdownPath, "utf8").slice(0, 512);
    } catch {
      continue;
    }
    if (head.includes(marker)) return true;
  }
  return false;
}

function saveCapture(baseDir, rowKey, title, payload) {
  const sanitizedTitle = sanitizeName(title);
  const meetingDir = path.join(baseDir, sanitizedTitle);
  fs.mkdirSync(meetingDir, { recursive: true });
  const timestamp = parseLocalTimestamp(payload.history_row?.last_active) || new Date();
  let targetPath = path.join(meetingDir, buildMarkdownFilename(sanitizedTitle, timestamp));
  if (fs.existsSync(targetPath)) {
    const head = fs.readFileSync(targetPath, "utf8").slice(0, 512);
    if (!head.includes(`<!-- row_key: ${rowKey} -->`)) {
      const parsed = path.parse(targetPath);
      targetPath = path.join(parsed.dir, `${parsed.name} ${rowKey.slice(-8)}${parsed.ext}`);
    }
  }
  fs.writeFileSync(targetPath, buildSummaryMarkdown(rowKey, payload), "utf8");
  return targetPath;
}

function normalizeLines(text) {
  return String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim());
}

function mergeSnapshotLines(snapshots) {
  let merged = [];
  for (const snapshot of snapshots) {
    const lines = normalizeLines(snapshot);
    if (!lines.length) continue;
    if (!merged.length) {
      merged = [...lines];
      continue;
    }
    const maxOverlap = Math.min(merged.length, lines.length, 400);
    let overlap = 0;
    for (let width = maxOverlap; width > 0; width -= 1) {
      if (merged.slice(-width).join("\n") === lines.slice(0, width).join("\n")) {
        overlap = width;
        break;
      }
    }
    if (overlap) {
      merged.push(...lines.slice(overlap));
    } else if (!merged.join("\n").includes(lines.join("\n"))) {
      merged.push(...lines);
    }
  }
  return merged.filter((line, index, arr) => index === 0 || line !== arr[index - 1]);
}

async function evaluatePage(tab, pageFunction, arg, options) {
  return tab.playwright.evaluate(pageFunction, arg, options);
}

async function waitForFoundState(tab, stateJs, timeoutMs, pollMs = 200) {
  const deadline = Date.now() + timeoutMs;
  let lastState = { found: false };
  while (Date.now() < deadline) {
    lastState = await evaluatePage(tab, stateJs, undefined, { timeoutMs: 5000 });
    if (lastState?.found) return lastState;
    await tab.playwright.waitForTimeout(pollMs);
  }
  return lastState;
}

async function extractTranscript(tab, { delayMs = 200, maxSteps = 800, timeoutMs = 240000 } = {}) {
  await evaluatePage(tab, ENSURE_TRANSCRIPT_TAB_JS, undefined, { timeoutMs: 5000 });
  await tab.playwright.waitForTimeout(600);
  const originalState = await waitForFoundState(tab, GET_TRANSCRIPT_STATE_JS, Math.min(timeoutMs, 4000));
  if (!originalState?.found) {
    throw new Error("Transcript container '[data-overlayscrollbars-contents]' was not found.");
  }

  const snapshots = [];
  let lastSignature = null;
  let stableAtBottom = 0;
  const deadline = Date.now() + timeoutMs;

  for (let step = 0; step < maxSteps && Date.now() < deadline; step += 1) {
    const state = await evaluatePage(tab, GET_TRANSCRIPT_STATE_JS, undefined, { timeoutMs: 5000 });
    if (!state?.found) {
      await tab.playwright.waitForTimeout(200);
      continue;
    }
    const text = String(state.text || "").trim();
    if (text) {
      const signature = [
        Number(state.scrollTop || 0),
        text.length,
        text.slice(0, 120),
        text.slice(-120),
      ].join("|");
      if (signature !== lastSignature) {
        snapshots.push(text);
        lastSignature = signature;
      }
    }
    const scrollTop = Number(state.scrollTop || 0);
    const scrollHeight = Number(state.scrollHeight || 0);
    const clientHeight = Number(state.clientHeight || 0);
    if (scrollTop + clientHeight >= scrollHeight - 5) {
      stableAtBottom += 1;
      if (stableAtBottom >= 2) break;
    } else {
      stableAtBottom = 0;
    }
    const stepSize = Math.max(260, Math.floor(clientHeight * 0.8));
    await tab.cua.scroll({ x: 700, y: 520, scrollX: 0, scrollY: stepSize });
    await tab.playwright.waitForTimeout(Math.min(delayMs, Math.max(0, deadline - Date.now())));
  }

  const mergedLines = mergeSnapshotLines(snapshots);
  const transcript = mergedLines.join("\n").trim();
  return [
    transcript,
    {
      snapshot_count: snapshots.length,
      line_count: mergedLines.length,
      char_count: transcript.length,
    },
  ];
}

async function extractAiSummary(tab, timeoutMs = 8000) {
  await evaluatePage(tab, ENSURE_AI_SUMMARY_TAB_JS, undefined, { timeoutMs: 5000 });
  await tab.playwright.waitForTimeout(600);
  const state = await waitForFoundState(tab, GET_AI_SUMMARY_JS, timeoutMs);
  if (!state?.found) {
    throw new Error("AI summary container was not found.");
  }
  const text = String(state.text || "").trim();
  return [text, { char_count: text.length, class_name: state.className || "" }];
}

async function waitForHistoryReady(tab, timeoutMs = 15000) {
  await tab.goto(HISTORY_URL);
  await tab.playwright.waitForLoadState({ state: "domcontentloaded", timeoutMs }).catch(() => {});
  const loginState = await evaluatePage(tab,
    () => {
      const body = (document.body.innerText || '').replace(/\u00a0/g, ' ').trim();
      const title = document.title || '';
      const url = location.href;
      const looksLoggedOut =
        location.hostname === 'login.dingtalk.com' ||
        /登录|登入|login|sign in|扫码|scan/i.test(title) ||
        /扫码登录|账号登录|手机号登录|短信验证码|Scan|QR code/i.test(body);
      return { url, title, body_head: body.slice(0, 500), looks_logged_out: looksLoggedOut };
    },
    undefined,
    { timeoutMs: 5000 },
  );
  if (loginState.looks_logged_out) {
    throw new Error(`Login required before history is accessible: ${JSON.stringify(loginState)}`);
  }
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const ready = await evaluatePage(tab,
    () => {
        if (location.hostname !== 'oa.dingtalk.com' || !location.hash.includes('/flash_minutes/history_list')) return false;
        if (document.querySelector('tr[data-row-key]')) return true;
        const body = (document.body.innerText || '').replace(/\u00a0/g, ' ');
        return body.includes('No content') || body.includes('暂无数据');
      },
      undefined,
      { timeoutMs: 5000 },
    );
    if (ready) return;
    await tab.playwright.waitForTimeout(500);
  }
  throw new Error("History page did not become ready before timeout.");
}

async function getHistoryPage(tab) {
  return evaluatePage(tab,
    () => {
      const rows = Array.from(document.querySelectorAll('tr[data-row-key]')).map((tr) => {
        const tds = Array.from(tr.querySelectorAll('td'));
        const titleLink = tds[1]?.querySelector('a') || null;
        return {
          row_key: tr.getAttribute('data-row-key') || '',
          masked_title: titleLink ? (titleLink.innerText || '').trim() : (tds[1] ? (tds[1].innerText || '').trim() : ''),
          role: tds[2] ? (tds[2].innerText || '').trim() : '',
          initiator: tds[3] ? (tds[3].innerText || '').trim() : '',
          duration: tds[4] ? (tds[4].innerText || '').trim() : '',
          size: tds[5] ? (tds[5].innerText || '').trim() : '',
          source: tds[6] ? (tds[6].innerText || '').trim() : '',
          last_active: tds[7] ? (tds[7].innerText || '').trim() : ''
        };
      });
      const currentPage = Number(document.querySelector('li.dtd-pagination-item-active')?.getAttribute('title') || '1');
      const nextEnabled = !!document.querySelector('li.dtd-pagination-next[aria-disabled="false"] button');
      const totalPages = Number(Array.from(document.querySelectorAll('li.dtd-pagination-item')).slice(-1)[0]?.getAttribute('title') || String(currentPage));
      return { current_page: currentPage, total_pages: totalPages, next_enabled: nextEnabled, rows };
    },
    undefined,
    { timeoutMs: 8000 },
  );
}

async function goToNextPage(tab, expectedNextPage, previousFirstRowKey = "") {
  const nextButton = tab.playwright.locator('li.dtd-pagination-next[aria-disabled="false"] button').first();
  if (!(await nextButton.isVisible({ timeoutMs: 2000 }).catch(() => false))) return false;
  await nextButton.click({ timeoutMs: 5000 });
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    const state = await evaluatePage(tab,
    ({ expectedPage, previousFirstRowKey }) => {
        const active = document.querySelector('li.dtd-pagination-item-active');
        const currentPage = Number(active?.getAttribute('title') || '0');
        const firstRowKey = document.querySelector('tr[data-row-key]')?.getAttribute('data-row-key') || '';
        return {
          currentPage,
          firstRowKey,
          ready: currentPage === expectedPage && !!firstRowKey && (!previousFirstRowKey || firstRowKey !== previousFirstRowKey)
        };
      },
      { expectedPage: expectedNextPage, previousFirstRowKey },
      { timeoutMs: 5000 },
    );
    if (state.ready) return true;
    await tab.playwright.waitForTimeout(300);
  }
  return false;
}

async function waitForDetailReady(tab, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const state = await evaluatePage(tab,
    () => {
        const body = (document.body.innerText || '').replace(/\u00a0/g, ' ').trim();
        const transcriptEl = document.querySelector('[data-overlayscrollbars-contents]');
        const transcriptText = transcriptEl ? (transcriptEl.innerText || '').replace(/\u00a0/g, ' ').trim() : '';
        return {
          url: location.href,
          title: document.title,
          is_permission: location.pathname.includes('/app/permission/') || body.includes('暂无权限访问') || body.includes('No permission to access'),
          has_transcript: !!transcriptEl,
          transcript_text_len: transcriptText.length,
          has_ai_summary: !!(
            document.querySelector('.fm-full-text-summary__content') ||
            document.querySelector('.fm-full-text-summary') ||
            document.querySelector('.fm-tiptap-md-editor')
          ),
          body_head: body.slice(0, 400)
        };
      },
      undefined,
      { timeoutMs: 5000 },
    );
    if (state.is_permission) return state;
    if (state.has_transcript && Number(state.transcript_text_len || 0) >= 40) return state;
    if (state.has_ai_summary && state.body_head) return state;
    await tab.playwright.waitForTimeout(300);
  }
  return evaluatePage(tab,
    () => {
      const body = (document.body.innerText || '').replace(/\u00a0/g, ' ').trim();
      const transcriptEl = document.querySelector('[data-overlayscrollbars-contents]');
      const transcriptText = transcriptEl ? (transcriptEl.innerText || '').replace(/\u00a0/g, ' ').trim() : '';
      return {
        url: location.href,
        title: document.title,
        is_permission: location.pathname.includes('/app/permission/') || body.includes('暂无权限访问') || body.includes('No permission to access'),
        has_transcript: !!transcriptEl,
        transcript_text_len: transcriptText.length,
        has_ai_summary: !!(
          document.querySelector('.fm-full-text-summary__content') ||
          document.querySelector('.fm-full-text-summary') ||
          document.querySelector('.fm-tiptap-md-editor')
        ),
        body_head: body.slice(0, 400)
      };
    },
    undefined,
    { timeoutMs: 5000 },
  );
}

async function getPermissionState(tab) {
  return evaluatePage(tab,
    () => {
      const normalize = (value) => ((value || '').replace(/\s+/g, ' ')).trim();
      const directButton = Array.from(document.querySelectorAll('button')).find((el) => {
        const text = normalize(el.innerText || el.textContent);
        return /^(发送申请|Send Application)$/i.test(text);
      });
      const body = (document.body.innerText || '').replace(/\u00a0/g, ' ').trim();
      const match = body.match(/(?:暂无权限访问|No permission to access)\s*["“”「]?\s*([\s\S]*?)\s*["“”」]?\s*(?:当前账号|Current account|Request permission from)/);
      return {
        title: match ? match[1].replace(/\s+/g, ' ').trim() : '',
        body,
        can_request: !!directButton,
        request_button_text: directButton ? normalize(directButton.innerText || directButton.textContent) : '',
        request_button_disabled: !!(directButton && directButton.disabled),
        already_requested: /已发送|申请已发送|等待审批|审批中|已向|Applied to|Reapply|Refresh Page/.test(body)
      };
    },
    undefined,
    { timeoutMs: 5000 },
  );
}

export async function waitForPermissionState(tab, { timeoutMs = 6000, pollMs = 250 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let state = await getPermissionState(tab);
  while (Date.now() < deadline) {
    if (state.already_requested || state.can_request) return state;
    await tab.playwright.waitForTimeout(pollMs);
    state = await getPermissionState(tab);
  }
  return state;
}

export async function clickSendRequest(tab, requestMessage) {
  if (requestMessage) {
    const fieldState = await evaluatePage(
      tab,
      GET_PERMISSION_REQUEST_MESSAGE_FIELD_STATE_JS,
      {},
      { timeoutMs: 5000 },
    );
    if (!fieldState?.found) {
      emitProgress(`Permission request reason field was not found: ${fieldState?.reason || "unknown"}`);
      return false;
    }
    const fields = tab.playwright.locator(PERMISSION_REQUEST_MESSAGE_FIELD_SELECTOR);
    const fieldCount = await fields.count();
    const selectorIndex = Number(fieldState.selector_index ?? fieldState.index);
    if (fieldCount <= selectorIndex) {
      emitProgress(`Permission request reason field index disappeared: index=${selectorIndex} count=${fieldCount}`);
      return false;
    }
    await fields.nth(selectorIndex).fill(requestMessage, { timeoutMs: 5000 });
    await tab.playwright.waitForTimeout(250);
    const filledState = await evaluatePage(
      tab,
      GET_PERMISSION_REQUEST_MESSAGE_FIELD_STATE_JS,
      { index: fieldState.index, requestMessage },
      { timeoutMs: 5000 },
    );
    if (!filledState?.filled) {
      emitProgress(`Permission request reason was not filled: ${filledState?.reason || "message_not_read_back"}`);
      return false;
    }
  }

  let button = tab.playwright.getByRole("button", { name: "发送申请", exact: true });
  let buttonCount = await button.count();
  if (buttonCount !== 1) {
    button = tab.playwright.getByRole("button", { name: "Send Application", exact: true });
    buttonCount = await button.count();
  }
  if (buttonCount !== 1) return false;

  for (let attempt = 0; attempt < 12; attempt += 1) {
    if (await button.isEnabled()) {
      await button.click({ timeoutMs: 5000 });
      return true;
    }
    await tab.playwright.waitForTimeout(250);
  }
  return false;
}

async function processRow(detailTab, baseDir, row, requestPermissions, requestMessage, extractOptions) {
  const rowKey = row.row_key;
  const label = row.masked_title || rowKey;
  emitProgress(`Processing ${label} (${rowKey})`);

  if (captureExists(baseDir, rowKey)) {
    emitProgress(`Skipped existing ${label}`);
    return { row_key: rowKey, status: "skipped_existing", topic: row.masked_title || "" };
  }

  await detailTab.goto(buildTranscribeUrl(rowKey));
  await detailTab.playwright.waitForLoadState({ state: "domcontentloaded", timeoutMs: 15000 }).catch(() => {});
  const ready = await waitForDetailReady(detailTab);
  const url = ready.url || (await detailTab.url());

  if (ready.is_permission || url.includes("/app/permission/")) {
    let state = await waitForPermissionState(detailTab);
    const topic = state.title || row.masked_title || rowKey;
    if (state.already_requested) {
      emitProgress(`permission_requested ${topic}`);
      return {
        ok: false,
        status: "permission_requested",
        row_key: rowKey,
        topic,
        source_url: url,
        history_row: row,
        page_state: state,
        permission_attempts: 1,
        last_checked_at: Date.now() / 1000,
      };
    }
    if (!requestPermissions) {
      emitProgress(`permission_required ${topic}`);
      return {
        ok: false,
        status: "permission_required",
        row_key: rowKey,
        topic,
        source_url: url,
        history_row: row,
        page_state: state,
        permission_attempts: 0,
        last_checked_at: Date.now() / 1000,
      };
    }
    const requested = await clickSendRequest(detailTab, requestMessage);
    await detailTab.playwright.waitForTimeout(requested ? 3000 : 500);
    state = await getPermissionState(detailTab);
    const status = requested ? "permission_requested" : "permission_required";
    emitProgress(`${status} ${topic}`);
    return {
      ok: false,
      status,
      row_key: rowKey,
      topic,
      source_url: url,
      history_row: row,
      page_state: state,
      permission_attempts: requested ? 1 : 0,
      last_checked_at: Date.now() / 1000,
    };
  }

  if (url.includes("/app/transcribes/") && ready.has_transcript) {
    const pageMeta = await evaluatePage(detailTab, GET_PAGE_META_JS, undefined, { timeoutMs: 5000 });
    let transcript;
    let transcriptMeta;
    try {
      [transcript, transcriptMeta] = await fetchDwsTranscript(rowKey, {
        dwsBin: extractOptions.dwsBin,
        timeoutMs: extractOptions.dwsTimeoutMs,
        maxPages: extractOptions.dwsMaxTranscriptPages,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const topic = pageMeta.title || row.masked_title || rowKey;
      if (/no permission|B_PERMISSION|permission denied/i.test(message)) {
        emitProgress(`permission_required ${topic}`);
        return {
          ok: false,
          status: "permission_required",
          row_key: rowKey,
          topic,
          source_url: pageMeta.url || url,
          history_row: row,
          error: message,
          last_checked_at: Date.now() / 1000,
        };
      }
      if (/task not found/i.test(message)) {
        emitProgress(`Unexpected page for ${topic}: task not found`);
        return {
          ok: false,
          status: "unexpected_page",
          row_key: rowKey,
          topic,
          source_url: pageMeta.url || url,
          history_row: row,
          error: message,
          last_checked_at: Date.now() / 1000,
        };
      }
      throw error;
    }
    let aiSummary = await fetchDwsSummary(rowKey, {
      dwsBin: extractOptions.dwsBin,
      timeoutMs: extractOptions.dwsTimeoutMs,
    });
    let aiSummaryMeta = { source: "dws", char_count: aiSummary.length };
    if (!aiSummary) {
      const [domSummary, domSummaryMeta] = await extractAiSummary(detailTab);
      aiSummary = domSummary;
      aiSummaryMeta = { ...domSummaryMeta, source: "dom" };
    }
    if (!transcript || transcriptMeta.paragraph_count === 0) {
      throw new Error("DWS transcription returned no paragraphs.");
    }
    const title = pageMeta.title || row.masked_title || rowKey;
    const payload = {
      ok: true,
      status: "downloaded",
      row_key: rowKey,
      title,
      url: pageMeta.url || url,
      history_row: row,
      transcript,
      ai_summary: aiSummary,
      transcript_meta: transcriptMeta,
      ai_summary_meta: aiSummaryMeta,
    };
    const savedPath = saveCapture(baseDir, rowKey, title, payload);
    payload.saved_path = savedPath;
    payload.saved_dir = path.dirname(savedPath);
    emitProgress(`Downloaded ${title}`);
    return payload;
  }

  const topic = row.masked_title || rowKey;
  emitProgress(`Unexpected page for ${topic}`);
  return {
    ok: false,
    status: "unexpected_page",
    row_key: rowKey,
    topic,
    source_url: url,
    history_row: row,
    detail_state: ready,
    last_checked_at: Date.now() / 1000,
  };
}

export async function runChromeDingTalkSync(options = {}) {
  if (!options.browser) {
    const { setupBrowserRuntime } = await import(options.browserClientPath || BROWSER_CLIENT_PATH);
    await setupBrowserRuntime({ globals: globalThis });
  }
  if (!options.browser && !options.agent && typeof agent === "undefined") {
    throw new Error("runChromeDingTalkSync must run inside the Codex browser runtime with an agent object.");
  }
  const runtimeAgent = options.agent || (typeof agent === "undefined" ? null : agent);
  const browser = options.browser || (await runtimeAgent.browsers.get("extension"));

  const baseDir = options.baseDir || DEFAULT_BASE_DIR;
  const cutoffDate = parseLocalTimestamp(options.stopBeforeDate || "");
  const maxItems = Number(options.maxItems || 0);
  const maxPages = Number(options.maxPages || 0);
  const minAgeMinutes = Number(options.minAgeMinutes ?? DEFAULT_MIN_AGE_MINUTES);
  const requestPermissions = options.requestPermissions !== false;
  const requestMessage = options.permissionRequestMessage || DEFAULT_PERMISSION_REQUEST_MESSAGE;
  const extractOptions = {
    maxSteps: Number(options.transcriptMaxSteps || 120),
    timeoutMs: Number(options.transcriptTimeoutMs || 90000),
    delayMs: Number(options.transcriptDelayMs || 200),
    dwsBin: options.dwsBin || DEFAULT_DWS_BIN,
    dwsTimeoutMs: Number(options.dwsTimeoutMs || 30000),
    dwsMaxTranscriptPages: Number(options.dwsMaxTranscriptPages || 100),
  };
  fs.mkdirSync(baseDir, { recursive: true });

  let historyTab;
  if (options.useExistingHistoryTab === true) {
    const openTabs = await browser.user.openTabs();
    const historyInfo =
      openTabs.find((tab) => (tab.url || "").includes("oa.dingtalk.com/meeting_oa#/flash_minutes/history_list")) ||
      openTabs.find((tab) => (tab.title || "").includes("AI") && (tab.title || "").includes("听记")) ||
      openTabs[0];
    historyTab = await browser.user.claimTab(historyInfo);
  } else {
    historyTab = await browser.tabs.new();
  }
  const detailTab = await browser.tabs.new();

  const results = [];
  const seenRowKeys = new Set();
  let processedCount = 0;
  let stopDueToCutoff = false;

  try {
    emitProgress(`Opening DingTalk AI history through real Chrome`);
    await waitForHistoryReady(historyTab, Number(options.historyReadyTimeoutMs || 60000));
    emitProgress(`History ready; scratch tab opened`);

    while (true) {
      const pageState = await getHistoryPage(historyTab);
      const currentPage = Number(pageState.current_page || 1);
      const rows = pageState.rows || [];
      emitProgress(`History page ${currentPage}: ${rows.length} rows`);
      if (!rows.length) break;

      for (const row of rows) {
        const rowKey = row.row_key;
        if (!rowKey || seenRowKeys.has(rowKey)) continue;
        const rowLastActive = parseLocalTimestamp(row.last_active || "");
        if (cutoffDate && rowLastActive && rowLastActive < cutoffDate) {
          emitProgress(
            `Stopping at ${row.masked_title || rowKey}: ${row.last_active} is older than cutoff ${options.stopBeforeDate}`,
          );
          stopDueToCutoff = true;
          break;
        }
        const rowLastActiveChina = parseChinaTimestamp(row.last_active || "");
        if (minAgeMinutes > 0 && rowLastActiveChina) {
          const ageMs = Date.now() - rowLastActiveChina.getTime();
          if (ageMs < minAgeMinutes * 60 * 1000) {
            emitProgress(`Skipped recent ${row.masked_title || rowKey}: ${row.last_active} is within ${minAgeMinutes} minutes`);
            results.push({
              row_key: rowKey,
              status: "skipped_recent",
              topic: row.masked_title || "",
              history_row: row,
              min_age_minutes: minAgeMinutes,
              last_checked_at: Date.now() / 1000,
            });
            processedCount += 1;
            continue;
          }
        }
        seenRowKeys.add(rowKey);
        let result;
        try {
          result = await processRow(detailTab, baseDir, row, requestPermissions, requestMessage, extractOptions);
        } catch (error) {
          const topic = row.masked_title || rowKey;
          result = {
            ok: false,
            status: "failed",
            row_key: rowKey,
            topic,
            history_row: row,
            error: error instanceof Error ? error.message : String(error),
            last_checked_at: Date.now() / 1000,
          };
          emitProgress(`Failed ${topic}: ${result.error}`);
        }
        results.push(result);
        processedCount += 1;
        if (maxItems && processedCount >= maxItems) {
          stopDueToCutoff = true;
          break;
        }
      }

      if (stopDueToCutoff) break;
      if (maxPages && currentPage >= maxPages) break;
      if (!pageState.next_enabled) break;
      const previousFirstRowKey = rows[0]?.row_key || "";
      emitProgress(`Advancing to history page ${currentPage + 1}`);
      const advanced = await goToNextPage(historyTab, currentPage + 1, previousFirstRowKey);
      if (!advanced) break;
    }
  } finally {
    await detailTab.close().catch(() => {});
    if (options.useExistingHistoryTab !== true) {
      await historyTab.close().catch(() => {});
    }
  }

  const summary = {
    ok: true,
    backend: "chrome_extension",
    base_dir: baseDir,
    cutoff_before: options.stopBeforeDate || "",
    processed: results.length,
    downloaded: results.filter((item) => item.status === "downloaded").length,
    skipped_existing: results.filter((item) => item.status === "skipped_existing").length,
    skipped_recent: results.filter((item) => item.status === "skipped_recent").length,
    permission_requested: results.filter((item) => item.status === "permission_requested").length,
    permission_required: results.filter((item) => item.status === "permission_required" || item.status === "permission_pending").length,
    failed: results.filter((item) => item.status === "failed").length,
    unexpected_page: results.filter((item) => item.status === "unexpected_page").length,
    results,
  };
  emitProgress(
    `Done: processed=${summary.processed} downloaded=${summary.downloaded} skipped=${summary.skipped_existing} skipped_recent=${summary.skipped_recent} permission_requested=${summary.permission_requested} permission_required=${summary.permission_required} failed=${summary.failed} unexpected_page=${summary.unexpected_page}`,
  );
  return summary;
}
