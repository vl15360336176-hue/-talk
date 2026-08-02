/* 最小 DOM 模拟器 + 新版页面冒烟测试 */
const fs = require("fs");

class ClassList {
  constructor(el){ this.el = el; this.set = new Set(); }
  _sync(){ this.el._className = [...this.set].join(" "); }
  add(...c){ c.forEach(x=>this.set.add(x)); this._sync(); }
  remove(...c){ c.forEach(x=>this.set.delete(x)); this._sync(); }
  toggle(c, force){ const on = force===undefined ? !this.set.has(c) : !!force; on?this.set.add(c):this.set.delete(c); this._sync(); return on; }
  contains(c){ return this.set.has(c); }
}
class El {
  constructor(tag){
    this.tagName = (tag||"div").toUpperCase();
    this.children = []; this._parent = null;
    this._className = ""; this._innerHTML = "";
    this.textContent = ""; this.dataset = {};
    this.style = { setProperty(k,v){ this[k]=v; } };
    this.listeners = {}; this.classList = new ClassList(this);
    this.value = ""; this.checked = false; this.onclick = null;
    this._queryCache = new Map();
  }
  set className(v){ this._className = v; this.classList.set = new Set(String(v).split(/\s+/).filter(Boolean)); }
  get className(){ return this._className; }
  set innerHTML(v){
    this._innerHTML = String(v); this.children = [];
    if(this.tagName === "SELECT"){
      this.options = [...this._innerHTML.matchAll(/<option value="([^"]*)"/g)].map(m=>m[1]);
      if(this.options.length) this.value = this.options[0];
    }
  }
  get innerHTML(){ return this._innerHTML; }
  appendChild(c){ c._parent = this; this.children.push(c); return c; }
  addEventListener(t, fn){ (this.listeners[t] = this.listeners[t]||[]).push(fn); }
  _stubFor(sel){
    if(this._queryCache.has(sel)) return this._queryCache.get(sel);
    let stub = null;
    if(sel.startsWith("#")){
      const m = this._innerHTML.match(new RegExp(`id="${sel.slice(1)}"[^>]*`));
      if(m){ const attrs = m[0]; stub = new El(/type="(password|checkbox)"/.test(attrs)?"input":"div"); if(/type="checkbox"/.test(attrs)) stub.checked = /checked/.test(attrs); const vm = attrs.match(/value="([^"]*)"/); if(vm) stub.value = vm[1]; }
    } else if(sel.startsWith(".")){
      const cls = sel.slice(1);
      const tagRe = /<[^>]+>/g;
      let m;
      while((m = tagRe.exec(this._innerHTML))){
        if(new RegExp(`class="[^"]*\\b${cls}\\b[^"]*"`).test(m[0])){ stub = new El("div"); break; }
      }
    }
    if(stub) this._queryCache.set(sel, stub);
    return stub;
  }
  querySelector(sel){ return this._stubFor(sel); }
  querySelectorAll(sel){
    if(this._queryCache.has(sel)) return this._queryCache.get(sel);
    const out = [];
    if(sel.startsWith(".")){
      const cls = sel.slice(1);
      const tagRe = /<[^>]+>/g;
      let m;
      while((m = tagRe.exec(this._innerHTML))){
        if(new RegExp(`class="[^"]*\\b${cls}\\b[^"]*"`).test(m[0])){
          const s = new El("div");
          const d = m[0].match(/data-([\w-]+)="([^"]*)"/);
          if(d) s.dataset[d[1]] = d[2];
          out.push(s);
        }
      }
    }
    this._queryCache.set(sel, out);
    return out;
  }
  scrollIntoView(){}
  focus(){}
  setAttribute(k,v){ this[k]=v; }
  getAttribute(k){ return this[k]||null; }
  remove(){ if(this._parent){ const i=this._parent.children.indexOf(this); if(i>=0) this._parent.children.splice(i,1); } }
  click(){ if(this.onclick) this.onclick(); (this.listeners["click"]||[]).forEach(f=>f()); }
}

const registry = new Map();
global.document = {
  documentElement: new El("html"),
  body: new El("body"),
  getElementById(id){ if(!registry.has(id)) registry.set(id, new El("div")); return registry.get(id); },
  createElement(tag){ return new El(tag); },
  querySelector(){ return null; },
  addEventListener(t, fn){ if(t==="DOMContentLoaded") global._onReady = fn; }
};
const storage = new Map();
global.localStorage = {
  getItem: k => storage.has(k) ? storage.get(k) : null,
  setItem: (k,v) => { storage.set(k, String(v)); },
  removeItem: k => { storage.delete(k); }
};
global.window = globalThis;
global.prompt = () => null;

const html = fs.readFileSync("/Users/job/Documents/Codex/2026-07-31/ni/outputs/brand-roundtable.html", "utf8");
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const byId = id => document.getElementById(id);
byId("productInput").tagName = "TEXTAREA";
byId("industrySelect").tagName = "SELECT";
byId("marketSelect").tagName = "SELECT";
byId("langSelect").tagName = "SELECT";
byId("stage").tagName = "SECTION";
byId("stageView").className = "hidden";   // 静态 HTML 中的 hidden 类
byId("moreMenu").innerHTML = '<div class="menu-item" data-act="usage">使用说明</div><div class="menu-item" data-act="clear">清空历史</div>';
byId("moreMenu").className = "menu hidden";

const hook = `
;globalThis.__test = {
  BRAND_VOICES, INDUSTRY_LINEUP, BRAND_COLORS, DEMO_DATA, BRAND_TAG, brandColor,
  runRoundtable, runCards, setSettings(v){ settings = v; },
  handleFiles, buildAttachmentsBlock, addBrandToLineup, toggleFav, createRole, openRoleModal, voiceCardFor,
  togglePick, renderPickBar, buildPickedLineup, startPickedRoundtable, renderHistorySidebar,
  get picked(){ return picked; },
  get attachments(){ return attachments; },
  get lineup(){ return currentLineup; },
  get running(){ return running; }
};`;
eval(js + hook);

const results = [];
function assert(name, cond, extra=""){
  results.push({name, pass: !!cond, extra});
  if(!cond) console.error("  FAIL:", name, extra);
}
function collect(e, out){ if(!out) out=[]; e.children.forEach(c=>{ out.push(c); collect(c,out); }); return out; }
function findCard(parent, cls, text){ return collect(parent).find(c=>c._className.includes(cls) && c._innerHTML.includes(text)); }
const wait = ms => new Promise(r=>setTimeout(r,ms));
let roleOverlay;

(async ()=>{
  const { BRAND_VOICES: V, INDUSTRY_LINEUP: L, BRAND_COLORS: C, DEMO_DATA: D, BRAND_TAG: TAG, brandColor: BC } = global.__test;

  // ---------- 数据完整性 ----------
  assert("84 个品牌", V.length === 84, `got ${V.length}`);
  const allBrands = new Set(V.map(b=>b.brand));
  Object.entries(L).forEach(([k,spec])=>{
    assert(`行业 ${k}: 4 品牌都在数据集中`, spec.brands.length===4 && spec.brands.every(b=>allBrands.has(b)));
    assert(`行业 ${k}: 主持人存在且有颜色`, allBrands.has(spec.host) && !!C[spec.host]);
  });
  V.forEach(b=>assert(`品牌 ${b.brand} 有头像色`, !!BC(b.brand), BC(b.brand)));
  assert("所有品类都有中文标签", V.every(b=>!!TAG[b.category]), [...new Set(V.map(b=>b.category))].join(","));
  assert("演示总结无 pick", !("pick" in D.summary) && D.summary.table.length===4 && D.summary.actions.length===3);

  // ---------- 初始化与首页 ----------
  global._onReady();
  assert("默认浅色主题", document.documentElement.getAttribute("data-theme") === "light");
  assert("首页可见 / 对话视图隐藏", !byId("homeView")._className.includes("hidden") && byId("stageView")._className.includes("hidden"));
  assert("推荐圆桌 6 张卡片", byId("recGrid").children.length === 6, `len=${byId("recGrid").children.length}`);
  assert("品牌卡片 84 张", byId("brandGrid").children.filter(c=>c._className.includes("brand-card")).length === 84);
  assert("标签筛选 8 个（全部激活）", byId("brandTags").children.length === 8 && byId("brandTags").children[0]._className.includes("active"));
  assert("初始行业消费品 + 阵容预览 5 chip", byId("industrySelect").value === "Consumer" && byId("brandPreview").children.length === 5);

  // ---------- 与品牌对话：筛选 / 收藏 / 对话 ----------
  byId("brandTags").children[4].click();
  assert("金融科技标签激活", byId("brandTags").children[4]._className.includes("active"));
  assert("金融科技显示 12 张卡", byId("brandGrid").children.length === 12, `len=${byId("brandGrid").children.length}`);
  byId("brandTags").children[0].click();
  assert("全部标签恢复 84 张卡", byId("brandGrid").children.length === 84);

  byId("brandSearch").value = "stripe";
  byId("brandSearch").listeners["input"][0]({ target: byId("brandSearch") });
  assert("搜索 stripe 只剩 1 张卡", byId("brandGrid").children.length === 1 && byId("brandGrid").children[0]._innerHTML.includes("Stripe"));
  byId("brandSearch").value = "";
  byId("brandSearch").listeners["input"][0]({ target: byId("brandSearch") });

  const stripeCard = findCard(byId("brandGrid"), "brand-card", "Stripe");
  stripeCard.querySelector(".bc-btn").onclick();
  assert("开始对话把 Stripe 放入阵容", global.__test.lineup.brands.includes("Stripe") && global.__test.lineup.brands[3]==="Stripe", JSON.stringify(global.__test.lineup.brands));

  stripeCard.querySelector(".bc-star").onclick();
  assert("收藏 Stripe 已持久化", JSON.parse(localStorage.getItem("brandRoundtableFavs")||"[]").includes("Stripe"));
  const stripeCard2 = findCard(byId("brandGrid"), "brand-card", "Stripe");
  assert("收藏星标高亮", stripeCard2._innerHTML.includes("bc-star fav") && stripeCard2._innerHTML.includes("★"));

  byId("brandSearch").value = "某新品牌";
  byId("brandSearch").listeners["keydown"][0]({ key:"Enter", target: byId("brandSearch") });
  roleOverlay = document.body.children.find(c=>c._className.includes("overlay"));
  assert("回车弹出创建表单并预填名字", !!roleOverlay && roleOverlay.querySelector("#roleName").value==="某新品牌");
  roleOverlay.querySelector("#roleIndustry").value = "AI";
  roleOverlay.querySelector("#roleSave").onclick();
  assert("回车创建自定义品牌并加入阵容", global.__test.lineup.brands.includes("某新品牌") && JSON.parse(localStorage.getItem("brandRoundtableCustoms")||"[]").some(c=>c.name==="某新品牌"&&c.industry==="AI"));
  const customCard = collect(byId("brandGrid")).find(c=>c._innerHTML.includes("某新品牌"));
  assert("自定义品牌卡片显示行业标签与编辑删除按钮", !!customCard && customCard._innerHTML.includes(">AI<") && customCard._innerHTML.includes("bc-edit") && customCard._innerHTML.includes("bc-del"));
  customCard.querySelector(".bc-edit").onclick();
  roleOverlay = document.body.children.find(c=>c._className.includes("overlay"));
  assert("编辑弹窗回填已有字段", !!roleOverlay && roleOverlay.querySelector("#roleName").value==="某新品牌" && roleOverlay.querySelector("#rolePrompt").value==="");
  roleOverlay.querySelector("#rolePrompt").value = "爱用技术黑话，简洁硬核";
  roleOverlay.querySelector("#roleSave").onclick();
  assert("编辑保存更新提示词", JSON.parse(localStorage.getItem("brandRoundtableCustoms")||"[]").some(c=>c.name==="某新品牌"&&c.systemPrompt==="爱用技术黑话，简洁硬核"));

  // ---------- 卡片「+」选择与批量开圆桌 ----------
  findCard(byId("brandGrid"), "brand-card", "Stripe").querySelector(".bc-add").onclick();
  findCard(byId("brandGrid"), "brand-card", "Revolut").querySelector(".bc-add").onclick();
  assert("选择 2 个品牌后显示选择条", global.__test.picked.length === 2 && !byId("pickBar")._className.includes("hidden") && byId("pickCount").textContent === "2");
  const pickChips = byId("pickChips").children;
  assert("选择条渲染品牌 chips", pickChips.length === 2 && pickChips[0]._innerHTML.includes("Stripe"));
  assert("已选卡片显示选中态", findCard(byId("brandGrid"), "brand-card selected", "Stripe") !== undefined);
  assert("已选卡片加号变对勾", findCard(byId("brandGrid"), "brand-card", "Stripe")._innerHTML.includes("bc-add on") && findCard(byId("brandGrid"), "brand-card", "Stripe")._innerHTML.includes("✓"));
  findCard(byId("brandGrid"), "brand-card", "Plaid").querySelector(".bc-add").onclick();
  findCard(byId("brandGrid"), "brand-card", "Adaption").querySelector(".bc-add").onclick();
  findCard(byId("brandGrid"), "brand-card", "Calendly").querySelector(".bc-add").onclick();
  assert("最多选 4 个品牌", global.__test.picked.length === 4, `len=${global.__test.picked.length}`);
  const built = global.__test.buildPickedLineup();
  assert("按选择组建阵容（Stripe/Revolut/Plaid/Adaption）", built.brands[0]==="Stripe" && built.brands[1]==="Revolut" && built.brands[2]==="Plaid" && built.brands[3]==="Adaption", JSON.stringify(built.brands));
  assert("主持人保持行业默认", built.host === "Atlassian", `host=${built.host}`);
  assert("开始圆桌按钮已绑定", typeof byId("pickStart").onclick === "function");

  // 二级页面：选人后先填话题再开始
  byId("pickStart").onclick();
  assert("跳转到二级页面（home 隐藏 / pick 显示）", byId("homeView")._className.includes("hidden") && !byId("pickView")._className.includes("hidden"));
  assert("二级页面渲染 4 嘉宾 + 1 主持人", byId("pickLineup").children.length === 4 && byId("pickHost").children.length === 1 && byId("pickHost").children[0]._innerHTML.includes("主持人"));
  assert("话题框预填自动圆桌的内容", byId("pickInput").value === byId("productInput").value);
  byId("pickInput").value = "测试话题：给这款智能手环想个新品上市传播";
  byId("btnPickStart").onclick();
  assert("点开始讨论进入对话视图且正在运行", !byId("stageView")._className.includes("hidden") && global.__test.running === true);
  assert("话题已同步到自动圆桌输入框", byId("productInput").value.includes("智能手环"));
  for(let i=0;i<150;i++){
    if(!global.__test.running) break;
    await wait(100);
  }
  assert("演示讨论完成并复位", global.__test.running === false);
  localStorage.setItem("brandRoundtableHistory", "[]");
  global.__test.renderHistorySidebar();

  // 重新选择，测试 chips 移除与清空
  findCard(byId("brandGrid"), "brand-card", "Stripe").querySelector(".bc-add").onclick();
  findCard(byId("brandGrid"), "brand-card", "Revolut").querySelector(".bc-add").onclick();
  findCard(byId("brandGrid"), "brand-card", "Plaid").querySelector(".bc-add").onclick();
  findCard(byId("brandGrid"), "brand-card", "Adaption").querySelector(".bc-add").onclick();
  byId("pickChips").children[0].click();
  assert("点击 chip 取消选择 Stripe", global.__test.picked.length === 3 && !global.__test.picked.includes("Stripe"));
  findCard(byId("brandGrid"), "brand-card", "Calendly").querySelector(".bc-add").onclick();
  assert("重新选满 4 个", global.__test.picked.length === 4);
  byId("pickClear").onclick();
  assert("清空选择后选择条隐藏", global.__test.picked.length === 0 && byId("pickBar")._className.includes("hidden"));

  byId("createRoleBtn").onclick();
  roleOverlay = document.body.children.find(c=>c._className.includes("overlay"));
  assert("创建角色弹窗打开", !!roleOverlay && !!roleOverlay.querySelector("#roleName") && !!roleOverlay.querySelector("#roleIndustry") && !!roleOverlay.querySelector("#rolePrompt"));
  roleOverlay.querySelector("#roleName").value = "测试角色";
  roleOverlay.querySelector("#roleIndustry").value = "消费品";
  roleOverlay.querySelector("#rolePrompt").value = "热情亲切，爱用叠词";
  roleOverlay.querySelector("#roleSave").onclick();
  assert("创建角色保存三个字段", JSON.parse(localStorage.getItem("brandRoundtableCustoms")||"[]").some(c=>c.name==="测试角色"&&c.industry==="消费品"&&c.systemPrompt==="热情亲切，爱用叠词"));
  assert("自定义角色卡片显示行业标签", collect(byId("brandGrid")).some(c=>c._innerHTML.includes("测试角色") && c._innerHTML.includes("消费品")));
  assert("声音卡使用自定义行业与提示词", global.__test.voiceCardFor("测试角色").industry==="消费品" && global.__test.voiceCardFor("测试角色").voice_summary==="热情亲切，爱用叠词");
  assert("内置品牌声音卡不受影响", global.__test.voiceCardFor("Stripe").voice_summary.includes("Stripe"));

  // ---------- 设置面板 ----------
  byId("btnSettings").click();
  const overlay = document.body.children.find(c=>c._className.includes("overlay"));
  assert("设置弹窗打开", !!overlay);
  overlay.querySelector("#setKey").value = "sk-test-123";
  overlay.querySelector("#setSave").click();
  assert("设置已写入 localStorage", JSON.parse(localStorage.getItem("brandRoundtableSettings")).apiKey === "sk-test-123");
  assert("设置弹窗已关闭", !document.body.children.some(c=>c._className.includes("overlay")));

  // ---------- 附件 ----------
  await global.__test.handleFiles([{ name:"品牌手册.md", size:1200, text: async()=> "简洁与速度是我们的主张。" }]);
  assert("附件列表渲染 1 条", byId("attachList").children.length === 1);
  assert("资料块包含文件内容", global.__test.buildAttachmentsBlock().includes("简洁与速度"));
  await global.__test.handleFiles([{ name:"超长.txt", size:5000, text: async()=> "长".repeat(20000) }]);
  assert("超长文件截断到 6000 字", global.__test.attachments[1].truncated && global.__test.attachments[1].chars===6000);
  byId("attachList").children[0].children[0].click();
  assert("删除附件后剩 1 条", global.__test.attachments.length === 1);

  // ---------- 演示圆桌 ----------
  localStorage.removeItem("brandRoundtableSettings");
  global.__test.setSettings({ baseUrl:"https://api.openai.com/v1", apiKey:"", model:"gpt-4o-mini", forceDemo:false });
  const t0 = Date.now();
  await global.__test.runRoundtable(true);
  assert("对话视图显示 / 首页隐藏", !byId("stageView")._className.includes("hidden") && byId("homeView")._className.includes("hidden"));
  const stageAll = collect(byId("stage"));
  const stageHtml = stageAll.map(c=>c._innerHTML).join("") + byId("stage")._innerHTML;
  assert("演示圆桌渲染完成（含总结、无 pick）", stageHtml.includes("可执行建议") && !stageHtml.includes("如果只能抄一个"));
  assert("气泡 9 个（1 主持人 + 4 + 4）", stageAll.filter(c=>c._className.includes("bubble-row")).length === 9);
  const hist = JSON.parse(localStorage.getItem("brandRoundtableHistory")||"[]");
  assert("演示后历史 1 条且完整", hist.length === 1 && hist[0].round1.length===5 && hist[0].round2.length===4);
  assert("运行标志已复位", global.__test.running === false);
  assert("耗时合理", Date.now()-t0 < 30000, `${Date.now()-t0}ms`);

  // 左侧历史栏
  const items = byId("historyList").children.filter(c=>c._className.includes("h-item"));
  assert("侧边栏历史 1 条且带日期标签", items.length === 1 && items[0]._innerHTML.includes("今天"));
  items[0].click();
  assert("回看后舞台重渲染", collect(byId("stage")).some(c=>c._innerHTML.includes("便携榨汁杯")));
  const itemsAfter = byId("historyList").children.filter(c=>c._className.includes("h-item"));
  assert("回看条目高亮", itemsAfter.length===1 && itemsAfter[0]._className.includes("active"));

  // ---------- 历史条目 ⋯ 菜单：置顶 / 文件夹 / 删除 ----------
  let hItem = byId("historyList").children.filter(c=>c._className.includes("h-item"))[0];
  hItem.querySelector(".h-more").onclick({});
  let hMenu = document.body.children.find(c=>c._className.includes("menu pop"));
  assert("⋯ 菜单打开且含 3 项", !!hMenu && hMenu.querySelectorAll(".menu-item").length === 3);
  assert("菜单文案为创建文件夹/置顶/删除", hMenu._innerHTML.includes("创建文件夹") && hMenu._innerHTML.includes("置顶") && hMenu._innerHTML.includes("删除"));
  hMenu.querySelectorAll(".menu-item")[1].onclick();
  assert("置顶已持久化", JSON.parse(localStorage.getItem("brandRoundtablePinned")||"[]").length === 1);
  assert("置顶后条目显示 📌", byId("historyList").children.filter(c=>c._className.includes("h-item"))[0]._innerHTML.includes("h-pin"));
  hItem = byId("historyList").children.filter(c=>c._className.includes("h-item"))[0];
  hItem.querySelector(".h-more").onclick({});
  hMenu = document.body.children.find(c=>c._className.includes("menu pop"));
  assert("置顶后菜单文案为取消置顶", hMenu._innerHTML.includes("取消置顶"));
  hMenu.querySelectorAll(".menu-item")[1].onclick();
  assert("取消置顶生效", JSON.parse(localStorage.getItem("brandRoundtablePinned")||"[]").length === 0);

  hItem = byId("historyList").children.filter(c=>c._className.includes("h-item"))[0];
  hItem.querySelector(".h-more").onclick({});
  hMenu = document.body.children.find(c=>c._className.includes("menu pop"));
  hMenu.querySelectorAll(".menu-item")[0].onclick();
  let fOverlay = document.body.children.find(c=>c._className.includes("overlay"));
  assert("创建文件夹弹窗打开", !!fOverlay && !!fOverlay.querySelector("#folderName"));
  fOverlay.querySelector("#folderName").value = "面试案例";
  fOverlay.querySelector("#folderSave").onclick();
  assert("文件夹已创建且对话已移入", JSON.parse(localStorage.getItem("brandRoundtableFolders")||"[]").some(f=>f.name==="面试案例"&&f.items.length===1));
  assert("侧栏出现文件夹与嵌套条目", byId("historyList").children.some(c=>c._className.includes("h-folder") && c._innerHTML.includes("面试案例")) && byId("historyList").children.some(c=>c._className.includes("h-item in-folder")));

  hItem = byId("historyList").children.filter(c=>c._className.includes("h-item"))[0];
  hItem.querySelector(".h-more").onclick({});
  hMenu = document.body.children.find(c=>c._className.includes("menu pop"));
  assert("文件夹内条目菜单显示移出文件夹", hMenu._innerHTML.includes("移出文件夹"));
  hMenu.querySelectorAll(".menu-item")[0].onclick();
  assert("移出后文件夹消失", JSON.parse(localStorage.getItem("brandRoundtableFolders")||"[]").length === 0 && !byId("historyList").children.some(c=>c._className.includes("h-folder")));

  hItem = byId("historyList").children.filter(c=>c._className.includes("h-item"))[0];
  hItem.querySelector(".h-more").onclick({});
  hMenu = document.body.children.find(c=>c._className.includes("menu pop"));
  hMenu.querySelectorAll(".menu-item")[2].onclick();
  assert("删除后历史为空", JSON.parse(localStorage.getItem("brandRoundtableHistory")||"[]").length === 0 && byId("historyList").children.some(c=>c._className.includes("h-empty")));

  // 返回首页 / 新对话
  byId("btnBackHome").onclick();
  assert("返回首页", !byId("homeView")._className.includes("hidden") && byId("stageView")._className.includes("hidden"));
  byId("btnNewChat").onclick();
  assert("新对话回到首页", !byId("homeView")._className.includes("hidden"));

  // 暗色模式
  byId("darkToggle").onclick();
  assert("暗色模式切换并持久化", document.documentElement.getAttribute("data-theme")==="dark" && localStorage.getItem("brandRoundtableTheme")==="dark");
  byId("darkToggle").onclick();
  assert("切回浅色", document.documentElement.getAttribute("data-theme")==="light");

  // 更多菜单：使用说明 + 清空历史
  byId("moreBtn").onclick({ stopPropagation(){} });
  assert("更多菜单展开", !byId("moreMenu")._className.includes("hidden"));
  const menuItems = byId("moreMenu").querySelectorAll(".menu-item");
  menuItems[0].onclick();
  assert("使用说明弹窗打开", document.body.children.some(c=>c._className.includes("overlay")));
  const usageOverlay = document.body.children.find(c=>c._className.includes("overlay"));
  usageOverlay.querySelector("#uClose").onclick();
  menuItems[1].onclick();
  assert("清空历史后侧栏为空", JSON.parse(localStorage.getItem("brandRoundtableHistory")||"[]").length===0 && byId("historyList").children.some(c=>c._className.includes("h-empty")));

  byId("supportBtn").onclick();
  assert("支持按钮打开使用说明", document.body.children.some(c=>c._className.includes("overlay")));

  // 推荐圆桌卡片：点击直接开始（无 Key → 演示）
  byId("recGrid").children[0].click();
  for(let i=0;i<150;i++){
    if(collect(byId("stage")).some(c=>c._innerHTML.includes("可执行建议"))) break;
    await wait(100);
  }
  assert("推荐卡片点击后进入对话视图", !byId("stageView")._className.includes("hidden"));
  assert("推荐卡片填充产品输入", byId("productInput").value.includes("便携榨汁杯"));
  assert("推荐卡片触发后历史新增", JSON.parse(localStorage.getItem("brandRoundtableHistory")||"[]").length === 1);

  // 灵感卡演示
  byId("btnBackHome").onclick();
  await global.__test.runCards();
  assert("灵感卡渲染 4 张", collect(byId("stage")).filter(c=>c._className.includes("inspire-card")).length === 4);

  const failed = results.filter(r=>!r.pass);
  console.log(`\n结果：${results.length - failed.length}/${results.length} 通过`);
  if(failed.length){ console.log("失败项:"); failed.forEach(f=>console.log(" -", f.name, f.extra)); process.exit(1); }
  console.log("冒烟测试全部通过 ✅");
  process.exit(0);
})().catch(e=>{ console.error("测试异常:", e); process.exit(1); });
