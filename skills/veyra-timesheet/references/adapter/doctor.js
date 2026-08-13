import { cli, Strategy } from '@jackwener/opencli/registry';

// Veyra adapter 健康检查 — 结构/登录态变化时先跑这个定位问题
const BASE = process.env.VEYRA_BASE_URL || 'https://guance.corpintra.rosettalab.top';

cli({
  site: 'veyra',
  name: 'doctor',
  description: 'Veyra adapter 健康检查：登录态 + 各 API 端点是否仍可用（失效时先跑这个，再按 adapter 自愈 playbook 修）',
  access: 'read',
  example: 'opencli veyra doctor',
  domain: 'guance.corpintra.rosettalab.top',
  strategy: Strategy.COOKIE,
  browser: true,
  columns: ['check', 'ok', 'detail'],
  func: async (page, kwargs) => {
    await page.goto(`${BASE}/timesheets`);
    await page.wait(2);
    return await page.evaluate(`(async()=>{
      const out=[];
      const probe=async(name,path,ok)=>{
        try{
          const res=await fetch('${BASE}'+path,{credentials:'include'});
          const ct=res.headers.get('content-type')||'';
          let j=null; if(ct.includes('json')){try{j=await res.json()}catch(e){}}
          out.push({check:name, ok:ok(res,j), detail:'HTTP '+res.status+' '+(ct.split(';')[0]||'?')});
        }catch(e){out.push({check:name, ok:false, detail:String(e)})}
      };
      await probe('登录态 /api/auth/me','/api/auth/me',(r)=>r.status===200);
      await probe('读 /api/timesheets','/api/timesheets?page=1&pageSize=1',(r,j)=>r.status===200&&!!(j&&j.data&&Array.isArray(j.data.items)));
      await probe('项目 /api/opportunities/select-options','/api/opportunities/select-options',(r,j)=>r.status===200&&!!(j&&Array.isArray(j.data)));
      const bad=out.filter(o=>!o.ok);
      if(bad.length) out.push({check:'>> 诊断', ok:false, detail: bad.some(b=>b.check.includes('auth'))?'登录态失效 → 在该 Chrome 重新登录 Veyra':'端点/结构疑似变化 → 按工时填写 skill 的 references/repair.md 重新探测并改 ~/.opencli/clis/veyra/*.js'});
      return out;
    })()`);
  },
});
