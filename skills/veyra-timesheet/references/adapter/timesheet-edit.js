import { cli, Strategy } from '@jackwener/opencli/registry';
import { readFileSync } from 'node:fs';

// Veyra 睿策 — 编辑一条已填工时记录（PATCH /api/timesheets/:id）
// 只传要改的字段；project/type 要一起改（opportunityType + opportunityId 是两个顶层字段）。
// Veyra 地址不硬编码：env VEYRA_BASE_URL 优先，否则读本目录 config.json（init 流程写入）。
// 未配置时不在 import 阶段抛错（会让整组命令无法注册、被误诊为未安装），改为占位 domain + 调用时报错。
const CFG = new URL('./config.json', import.meta.url);
const BASE = (() => {
  if (process.env.VEYRA_BASE_URL) return process.env.VEYRA_BASE_URL.replace(/\/+$/, '');
  try {
    const u = JSON.parse(readFileSync(CFG, 'utf8')).veyra_base_url;
    if (u && !u.includes('<')) return u.replace(/\/+$/, '');
  } catch {}
  return null;
})();
const DOMAIN = BASE ? new URL(BASE).host : 'veyra-unconfigured.invalid';
const requireBase = () => { if (!BASE) throw new Error(`Veyra 地址未配置：把公司工时系统地址写入 ${CFG.pathname}（格式见 config.example.json）或设置环境变量 VEYRA_BASE_URL`); return BASE; };

cli({
  site: 'veyra',
  name: 'timesheet-edit',
  description: '编辑一条已填 Veyra 工时记录（改项目/内容/小时/日期）',
  access: 'write',
  example: "opencli veyra timesheet-edit --id cmquu5s9x00lxv10jg9segswt --project cmq7uru49004apv0jzcnr8re6 --type project",
  domain: DOMAIN,
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'id', required: true, help: '工时记录 id（来自 timesheet-list）' },
    { name: 'date', help: '改工时日期 YYYY-MM-DD' },
    { name: 'project', help: '改项目 opportunityId（来自 veyra projects 的 id）；与 --type 一起给' },
    { name: 'type', help: 'opportunityType: lead|deal|project（改项目时一起给）' },
    { name: 'content', help: '改投入事项' },
    { name: 'hours', type: 'int', help: '改小时（数字，8h上限已放开）' },
  ],
  columns: ['status', 'ok', 'id', 'err'],
  func: async (page, kwargs) => {
    requireBase();
    await page.goto(`${BASE}/timesheets`);
    await page.wait(2);
    const body = {};
    if (kwargs.date) body.workDate = kwargs.date;
    if (kwargs.type) body.opportunityType = kwargs.type;
    if (kwargs.project) body.opportunityId = kwargs.project;
    if (kwargs.content) body.content = kwargs.content;
    if (kwargs.hours != null) body.hours = Number(kwargs.hours);
    const payload = JSON.stringify(body);
    const id = kwargs.id;
    const res = await page.evaluate(`(async()=>{
      const r = await fetch('${BASE}/api/timesheets/${id}',{method:'PATCH',credentials:'include',headers:{'Content-Type':'application/json'},body:${JSON.stringify(payload)}});
      let j={}; try{ j=await r.json() }catch(e){}
      return {status:r.status, ok:j.success===true, id:(j.data&&j.data.id)||'${id}', err:(j.error&&j.error.message)||(r.ok?null:('HTTP '+r.status))};
    })()`);
    return [res];
  },
});
