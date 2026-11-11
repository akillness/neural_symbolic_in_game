"use strict";

// A fixture-only bridge for these three drivers, not a general browser adapter.
// Node retains every assertion. Aside's native request/pageerror callbacks were
// proven unavailable; controlled HTTP/CSP/DOM observers are attested separately.
const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const { spawn } = require("node:child_process");
const { randomUUID } = require("node:crypto");

function pack(value) {
  const encode = (item) => {
    if (item === undefined) return ["undefined"];
    if (typeof item === "number" && !Number.isFinite(item)) return ["number", String(item)];
    if (item === null || typeof item !== "object") return ["value", item];
    if (Array.isArray(item)) return ["array", item.map(encode)];
    return ["object", Object.entries(item).map(([key, child]) => [key, encode(child)])];
  };
  return JSON.stringify(encode(value));
}
function unpack(text) {
  const decode = ([kind, value]) => {
    if (kind === "undefined") return undefined;
    if (kind === "number") return Number(value);
    if (kind === "value") return value;
    if (kind === "array") return value.map(decode);
    if (kind !== "object") throw new Error("invalid fixture wire value");
    const object = {};
    for (const [key, child] of value) Object.defineProperty(object, key, {
      value: decode(child), enumerable: true, writable: true, configurable: true,
    });
    return object;
  };
  return decode(JSON.parse(text));
}

// CLI errors and envelopes are untrusted; publish categories, never their payloads.
function fixtureFailure(error) {
  const message = typeof error === "string" ? error : typeof error?.message === "string" ? error.message : "";
  for (const trusted of ["TypeError: NSG trusted function failure", "TypeError: NSG caught source failure"]) {
    if (message === trusted || message === "Error: " + trusted) return trusted;
  }
  const categories = ["Aside fixture collector failed:", "controlled fixture CSP violation",
    "final fixture pageErrors guard rejected", "final fixture outgoing guard rejected",
    "final fixture CSP guard rejected", "final fixture GET-only guard rejected",
    "Aside exited before observation", "Aside CLI execution envelope invalid",
    "Aside CLI reported an error", "Aside CLI completion receipt invalid", "Aside CLI failed",
    "Aside call exceeded fixture CLI deadline", "Aside CLI omitted its completion receipt",
    "Aside CLI omitted content"];
  const category = categories.find((value) => message.includes(value));
  const detail = ["unexpected fixture auxiliary tab", "task-owned fixture tab inventory readiness missing",
    "task-owned fixture tab closure not ready", "task-owned fixture tab close failed",
    "unexpected fixture resource",
    "fixture observer readiness missing", "unexpected fixture frame/navigation",
    "fixture document changed or collection delivery missing", "fixture predicate timed out",
    "observation delivery failed"].find((value) => message.includes(value));
  return [category, detail].filter(Boolean).join(" ") || "Aside fixture operation failed";
}

function ownershipDiagnostic(value) {
  if (!value || typeof value !== "object") return undefined;
  const phases = ["open-initial", "open-replacement", "close", "fixture"];
  return { phase: phases.includes(value.phase) ? value.phase : "fixture",
    mainPresent: value.mainPresent === true, mainHandleKnownOwned: value.mainHandleKnownOwned === true,
    ...Object.fromEntries(["unknownCount", "staleOwnedCount", "currentTaskOriginCount", "otherKnownTaskOriginCount", "blankOrNewtabCount", "otherCount"].map(key=>[key,Number.isSafeInteger(value[key])&&value[key]>=0?value[key]:null])) };
}

async function launch() {
  const guardMs = process.env.NSG_ASIDE_GUARD_MS === undefined ? 115000 : Number(process.env.NSG_ASIDE_GUARD_MS);
  assert(Number.isInteger(guardMs) && guardMs >= 100 && guardMs <= 115000, "invalid fixture CLI test deadline");
  const token = randomUUID();
  const nonce = randomUUID();
  const routes = [];
  const listeners = new Map();
  const exposed = new Map();
  const initScripts = [];
  const requests = [];
  const cumulativeErrors = [], cumulativeOutgoing = [], cumulativeViolations = [];
  let probing = false;
  let sourceOrigin;
  let content = "";
  let sequence = 0;
  let pending;
  let nextResponse;
  let frameUrls = [];
  let failure;
  let observerControls;
  const pieces = new Map();
  let ownershipReported = false;
  const reportOwnership = (value) => { const diagnostic=ownershipDiagnostic(value);if(diagnostic&&!ownershipReported){ownershipReported=true;process.stderr.write(JSON.stringify({fixtureOwnershipFailure:diagnostic})+"\n");} };
  const fail = (error) => {
    failure ||= error;
    if (pending) { pending.reject(failure); pending = undefined; }
  };
  const respond = (response, status, body, type = "application/json", headers = {}) => {
    response.writeHead(status, { "Content-Type": type, "Cache-Control": "no-store, max-age=0", ...headers });
    response.end(body);
  };
  const observerScript = () => `(() => {
    const errors=[], violations=[], outgoing=[];let drain=0;
    const barrier=()=>new Promise(resolve=>{const channel=new MessageChannel();channel.port1.onmessage=()=>{channel.port1.close();channel.port2.close();queueMicrotask(resolve);};channel.port2.postMessage(null);});
    const observer=Object.freeze({token:${JSON.stringify(token)},documentId:${JSON.stringify(randomUUID())},barrier,drain:()=>({documentId:observer.documentId,drain:++drain,errors:errors.splice(0),violations:violations.splice(0),outgoing:outgoing.splice(0)})});
    Object.defineProperty(window,"__nsgAsideObserver",{value:observer});
    document.documentElement.dataset.nsgObserverReady=${JSON.stringify(token)};
    window.addEventListener("error",event=>{if(event instanceof ErrorEvent)errors.push(event.message||String(event.error));},true);
    window.addEventListener("unhandledrejection",event=>errors.push("unhandledrejection: "+String(event.reason)),true);
    window.addEventListener("securitypolicyviolation",event=>violations.push({directive:event.effectiveDirective,blocked:event.blockedURI}),true);
    Object.defineProperty(window,"open",{value:()=>{errors.push("unexpected fixture popup attempt");return null;}});
    const stopLink=event=>{const link=event.target instanceof Element?event.target.closest("a,area"):null;if(link){event.preventDefault();errors.push("unexpected fixture link navigation");}};
    document.addEventListener("click",stopLink,true);document.addEventListener("auxclick",stopLink,true);
    const formTargetAllowed=(form,submitter)=>{const target=submitter?.getAttribute("formtarget")||form.getAttribute("target")||document.querySelector("base[target]")?.getAttribute("target")||"_self";return target.toLowerCase()==="_self"||[...document.querySelectorAll("iframe[name]")].some(frame=>frame.name===target);};
    document.addEventListener("submit",event=>{if(!formTargetAllowed(event.target,event.submitter)){event.preventDefault();errors.push("unexpected fixture form popup");}},true);
    for(const name of ["submit","requestSubmit"]){const original=HTMLFormElement.prototype[name];Object.defineProperty(HTMLFormElement.prototype,name,{value:function(...args){if(!formTargetAllowed(this,args[0])){errors.push("unexpected fixture form popup");return;}return original.apply(this,args);}});}
    let parserFrame;let parsing=true;
    document.addEventListener("DOMContentLoaded",()=>{parsing=false;},{once:true});
    new MutationObserver(records=>{for(const record of records){if(record.type==="attributes"){if(record.target.matches("iframe"))errors.push("unexpected fixture frame attribute mutation");continue;}for(const node of [...record.addedNodes,...record.removedNodes]){if(node.nodeType!==1)continue;const frames=[...(node.matches("iframe")?[node]:[]),...node.querySelectorAll("iframe")];for(const frame of frames){if(parsing&&frame===parserFrame&&[...record.addedNodes].includes(node))continue;if(parsing&&!parserFrame&&window===window.top&&frame.isConnected&&new URL(frame.src,location.href).pathname==="/public/index.html"){parserFrame=frame;continue;}errors.push("unexpected fixture frame topology mutation");}}}}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:["src","srcdoc"]});
    ${[...exposed.keys()].map((name) => `window[${JSON.stringify(name)}]=value=>outgoing.push([${JSON.stringify(name)},value]);`).join("")}
    ${initScripts.map((code) => `(${code})();`).join("")}
  })();`;
  const html = (body) => {
    const script = `<script nonce="${nonce}">${observerScript()}</script>`;
    const injected = /<head\b[^>]*>/i.test(body) ? body.replace(/<head\b[^>]*>/i, (head) => head + script)
      : body.replace(/<!doctype[^>]*>/i, (doctype) => doctype + script);
    assert.notEqual(injected, body, "fixture HTML lacks an instrumentation insertion point");
    return { body: injected, headers: { "Content-Security-Policy": [
      "default-src 'none'", `script-src 'self' 'nonce-${nonce}'`, "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:", "font-src 'self'", "connect-src 'self'", "frame-src 'self'",
      "worker-src 'none'", "child-src 'self'", "object-src 'none'", "base-uri 'none'",
      "form-action 'self'", "frame-ancestors 'self'", "media-src 'none'", "manifest-src 'none'",
      "sandbox allow-scripts allow-same-origin allow-forms",
    ].join("; ") } };
  };
  const sendHtml = (response, status, body) => {
    const rendered = html(body);
    respond(response, status, rendered.body, "text/html; charset=utf-8", rendered.headers);
  };
  let sinkRequests = 0;
  const sink = http.createServer((request, response) => { sinkRequests++; request.resume(); respond(response, 200, "{}"); });
  await new Promise((resolve) => sink.listen(0, "127.0.0.1", resolve));
  const sinkOrigin = `http://127.0.0.1:${sink.address().port}`;
  const allowed = new Set(["/dashboard/index.html", "/dashboard/dashboard.css", "/dashboard/dashboard.js", "/dashboard/ontology-map.json", "/dashboard/disclosure-reference.json", "/public/index.icon.png"]);
  const approvedGetReceiptPaths = [...allowed, "/public/index.html", "/__nsg_figure", "/favicon.ico"];
  const server = http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, "http://127.0.0.1");
      const control = `/${token}/`;
      if (url.pathname === `${control}next`) {
        assert.equal(request.method, "GET");
        assert(!nextResponse, "duplicate Aside command poll");
        if (pending && !pending.sent) { pending.sent = true; respond(response, 200, pack(pending.command)); }
        else nextResponse = response;
        return;
      }
      if (url.pathname === `${control}result`) {
        assert.equal(request.method, "GET");
        assert(pending, "unsolicited Aside observation");
        assert.equal(Number(url.searchParams.get("id")), pending.command.id, "stale Aside observation");
        const index = Number(url.searchParams.get("index"));
        assert.equal(index, pieces.size, "missing or duplicate Aside observation chunk");
        pieces.set(index, url.searchParams.get("data"));
        if (url.searchParams.get("last") === "1") {
          const result = unpack(Buffer.from([...pieces.values()].join(""), "base64").toString("utf8"));
          pieces.clear();
          assert.equal(result.id, pending.command.id);
          reportOwnership(result.ownershipFailure);
          const current = pending;
          {
            assert(Array.isArray(result.frames) && Array.isArray(result.outgoing) && Array.isArray(result.pageErrors) && Array.isArray(result.violations), "incomplete Aside observation");
            frameUrls = result.frames;
            if (result.collectorFailure) {
              cumulativeErrors.push(...result.pageErrors);
              cumulativeOutgoing.push(...result.outgoing.filter(([name]) => name === "captureOutgoing"));
              cumulativeViolations.push(...result.violations);
              throw Object.assign(new Error("Aside fixture collector failed: " + result.collectorFailure), {
                observation: { pageErrors: result.pageErrors, outgoing: result.outgoing, violations: result.violations },
                sourceError: result.error,
              });
            }
            if (current.command.operation === "probe") {
              if (result.error) throw new Error(result.error);
              const probeRequests = requests.filter((item) => item.probe);
              assert(probeRequests.some((item) => item.method === "POST" && item.path === "/__nsg_probe_write"), "fixture recorder missed real same-origin POST");
              assert.throws(() => assert(probeRequests.every((item) => item.method === "GET")), assert.AssertionError);
              for (const document of ["top", "iframe"]) {
                const errors = result.pageErrors.filter((message) => message.includes(`NSG_${document}_`));
                assert(errors.some((message) => message.includes("async-exception")), `${document} async exception was not observed`);
                assert(errors.some((message) => message.includes("unhandled-rejection")), `${document} unhandled rejection was not observed`);
                assert.throws(() => assert.deepEqual(errors, []), assert.AssertionError);
              }
              assert(result.violations.some((item) => item.directive === "connect-src" && item.blocked.startsWith(sinkOrigin)), "off-origin POST was not contained");
              assert(result.violations.some((item) => item.directive === "form-action" && item.blocked.startsWith(sinkOrigin)), "off-origin form was not contained");
              assert.throws(() => assert.deepEqual(result.violations, []), assert.AssertionError);
              assert.equal(result.value.cspControls.length,4);
              for(const control of result.value.cspControls){assert.deepEqual(control.pageErrors,[]);assert(control.violations.some(violation=>violation.directive===control.directive),JSON.stringify(control));for(const violation of control.violations){assert([control.directive,...(control.directive==="form-action"?["frame-src"]:[])].includes(violation.directive),JSON.stringify(control));assert(violation.blocked.startsWith(sinkOrigin),JSON.stringify(control));}assert.throws(()=>assert.deepEqual(control.violations,[]),assert.AssertionError);}
              assert(result.value.cspControls.every(control=>["connect-src","form-action"].includes(control.directive)),"unexpected fixture CSP control directive");
              assert.equal(sinkRequests, 0, "negative-control request escaped fixture CSP");
              const commands = result.outgoing.filter(([name]) => name === "captureOutgoing").map(([, value]) => value);
              assert.deepEqual(commands, [{ nsgObserverNegativeControl: true }], "parent command observer lost actual iframe message");
              assert.throws(() => assert.deepEqual(commands, []), assert.AssertionError);
              for (const [name, pattern] of Object.entries({missingReadiness:/observer readiness missing/,extraFrame:/unexpected fixture frame/,changedDocument:/unexpected fixture frame/,reloadedDocument:/fixture document changed/,missingDelivery:/collection delivery missing/})) {
                assert.match(result.value.guards[name],pattern, `${name} did not exercise its actual guard`);
              }
              assert.equal(result.value.independentErrors.length,4);
              for(const control of result.value.independentErrors){assert.equal(control.errors.length,1);assert.match(control.errors[0],/NSG_(top|iframe)_(async-exception|unhandled-rejection)/);assert.throws(()=>assert.deepEqual(control.errors,[]),assert.AssertionError);}
              assert.deepEqual(result.value.earlyTopology.pageErrors, ["unexpected fixture frame topology mutation", "unexpected fixture frame topology mutation"]);
              assert.deepEqual(result.value.earlyTopology.violations, []);
              assert.throws(()=>assert.deepEqual(result.value.earlyTopology.pageErrors,[]),assert.AssertionError);
              assert.equal(result.value.popupControls.length,4);
              for(const control of result.value.popupControls){assert.deepEqual(control.pageErrors,["unexpected fixture link navigation"]);assert.deepEqual(control.violations,[]);assert.equal(control.newTabs,0);assert.throws(()=>assert.deepEqual(control.pageErrors,[]),assert.AssertionError);}
              assert.equal(result.value.formPopupControls.length,4);
              for(const control of result.value.formPopupControls){assert.deepEqual(control.pageErrors,["unexpected fixture form popup"]);assert.deepEqual(control.violations,[]);assert.equal(control.newTabs,0);assert.throws(()=>assert.deepEqual(control.pageErrors,[]),assert.AssertionError);}
              observerControls = {
                sameOriginPost: "original GET-only assertion rejected actual POST501",
                offOriginPostAndForm: result.value.cspControls.map(control=>({directive:control.directive,pageErrorCount:control.pageErrors.length,outgoingCount:control.outgoing.length,violations:control.violations.map(violation=>({directive:violation.directive,blockedFixtureSink:true}))})),
                topAndIframeErrors: result.value.independentErrors.map(control=>({errors:[/NSG_(top|iframe)_(async-exception|unhandled-rejection)/.exec(control.errors[0])[0]]})),
                parentCommand: "original empty-outgoing assertion rejected",
                earlyTopology: "pre-DOMContentLoaded transient frame rejected",
                popupControls: result.value.popupControls.map(()=>({pageErrors:["unexpected fixture link navigation"],violations:[],newTabs:0})),
                formPopupControls: result.value.formPopupControls.map(()=>({pageErrors:["unexpected fixture form popup"],violations:[],newTabs:0})),
                guards:Object.fromEntries(["missingReadiness","extraFrame","changedDocument","reloadedDocument","missingDelivery"].map(name=>[name,fixtureFailure(result.value.guards[name])])),
              };
              process.stderr.write(JSON.stringify({ backend: "aside", boundedFixtureObserverControls: observerControls, nativeRequestAndPageerror: "unavailable; prior real controls reported zero callbacks; not recertified" }) + "\n");
            } else {
              cumulativeErrors.push(...result.pageErrors);
              cumulativeOutgoing.push(...result.outgoing.filter(([name]) => name === "captureOutgoing"));
              cumulativeViolations.push(...result.violations);
              assert.deepEqual(result.violations, [], "controlled fixture CSP violation");
              if (!listeners.has("pageerror")) assert.deepEqual(result.pageErrors, [], "unhandled fixture page error");
              for (const [name, value] of result.outgoing) { assert(exposed.has(name)); exposed.get(name)(value); }
              for (const message of result.pageErrors) listeners.get("pageerror")?.({ message });
            }
            if (result.error) current.reject(new Error(result.error));
            else current.resolve(result.value);
          }
          pending = undefined;
        }
        respond(response, 200, "{}");
        return;
      }
      // Authoritative actual method, recorded before handling, rejecting, or proxying.
      const observed = { url: `http://${request.headers.host}${request.url}`, path: url.pathname, method: request.method, probe: probing };
      requests.push(observed);
      if (!probing) listeners.get("request")?.({ url: () => observed.url, method: () => observed.method });
      if (url.pathname === "/__nsg_probe") { sendHtml(response, 200, '<!doctype html><html><head><title>Observer controls, NOT GAMEPLAY</title></head><body><iframe src="/public/index.html"></iframe></body></html>'); return; }
      if (url.pathname === "/__nsg_bootstrap") { sendHtml(response,200,`<!doctype html><html><head><title>Early topology control</title></head><body><iframe src="/public/index.html"></iframe><script nonce="${nonce}">const extra=document.createElement("iframe");extra.src="about:blank";document.body.append(extra);extra.remove();</script></body></html>`);return; }
      if (url.pathname === "/__nsg_probe_write") { request.resume(); respond(response, request.method === "POST" ? 501 : 200, "{}"); return; }
      if (url.pathname === "/__nsg_figure") { sendHtml(response, 200, `<!doctype html><html><head><meta charset="utf-8"></head><body>${content}</body></html>`); return; }
      if (url.pathname === "/favicon.ico") { respond(response, 404, "no fixture favicon"); return; }
      assert(allowed.has(url.pathname) || url.pathname === "/public/index.html", "unexpected fixture resource");
      const route = routes.find(([pattern]) => url.pathname === (pattern === "**/public/index.html" ? "/public/index.html" : "/dashboard/ontology-map.json"));
      if (route) {
        let fulfilled = false;
        await route[1]({ fulfill: async (options) => {
          assert(!fulfilled, "fixture fulfilled twice"); fulfilled = true;
          const body = Object.hasOwn(options, "json") ? JSON.stringify(options.json) : options.body;
          const type = options.contentType || (Object.hasOwn(options, "json") ? "application/json" : "text/plain");
          if (type.includes("html")) sendHtml(response, options.status || 200, body);
          else respond(response, options.status || 200, body, type);
        } });
        assert(fulfilled, "fixture route was not fulfilled");
        return;
      }
      assert(sourceOrigin && allowed.has(url.pathname), `unexpected fixture resource: ${url.pathname}`);
      const upstream = http.request(`${sourceOrigin}${request.url}`, { method: request.method }, (incoming) => {
        if (incoming.statusCode >= 300 && incoming.statusCode < 400) { incoming.resume(); fail(new Error("fixture upstream redirect is forbidden")); respond(response, 502, "redirect forbidden"); return; }
        const chunks = [];
        incoming.on("data", (chunk) => chunks.push(chunk));
        incoming.on("end", () => {
          const body = Buffer.concat(chunks);
          const type = incoming.headers["content-type"] || "application/octet-stream";
          if (type.includes("html")) sendHtml(response, incoming.statusCode, body.toString("utf8"));
          else respond(response, incoming.statusCode, body, type);
        });
      });
      upstream.on("error", (error) => { fail(error); respond(response, 502, error.message); });
      request.pipe(upstream);
    } catch (error) { fail(error); if (!response.headersSent) respond(response, 500, error.stack); else response.end(); }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const rpc = (operation, args = {}) => {
    if (failure) return Promise.reject(failure);
    assert(!pending, "concurrent Aside operation is unsupported");
    return new Promise((resolve, reject) => {
      pending = { command: { id: ++sequence, operation, ...args }, resolve, reject, sent: false };
      if (nextResponse) { pending.sent = true; respond(nextResponse, 200, pack(pending.command)); nextResponse = undefined; }
    });
  };
  const worker = `const nsgPack=${pack.toString()};const nsgUnpack=${unpack.toString()};const nsgFailure=${fixtureFailure.toString()};
const nsgBase=${JSON.stringify(`${origin}/${token}/`)};const nsgToken=${JSON.stringify(token)};
let nsgTab;let nsgCount=0;let nsgGuarded=false;let nsgExpected;let nsgViewport;let nsgMedia;let nsgDocuments=new Map();
let nsgBaseline;let nsgTabFailure;let nsgTabPhase="open-initial";let nsgOwnershipDiagnostic;const nsgOwnedTargets=new Set();const nsgTaskOrigin=new URL(nsgBase).origin;const nsgKnownTaskOrigins=new Set([nsgTaskOrigin]);
const nsgInventoryGuard=current=>{if(!nsgTabFailure){const unknown=current.filter(tab=>!nsgBaseline.has(tab.targetId)&&!nsgOwnedTargets.has(tab.targetId));if(unknown.length){const counts={currentTaskOriginCount:0,otherKnownTaskOriginCount:0,blankOrNewtabCount:0,otherCount:0};for(const tab of unknown){if(["about:blank","about:newtab","chrome://newtab/","chrome://new-tab-page/"].includes(tab.url)){counts.blankOrNewtabCount++;continue;}try{const origin=new URL(tab.url).origin;counts[origin===nsgTaskOrigin?"currentTaskOriginCount":nsgKnownTaskOrigins.has(origin)?"otherKnownTaskOriginCount":"otherCount"]++;}catch{counts.otherCount++;}}nsgOwnershipDiagnostic={phase:nsgTabPhase,unknownCount:unknown.length,mainPresent:current.some(tab=>tab.targetId===nsgTab?.targetId),mainHandleKnownOwned:nsgOwnedTargets.has(nsgTab?.targetId),staleOwnedCount:current.filter(tab=>nsgOwnedTargets.has(tab.targetId)&&tab.targetId!==nsgTab?.targetId).length,...counts};console.log(JSON.stringify({nsgFixtureOwnershipFailure:nsgOwnershipDiagnostic}));nsgTabFailure=new Error("unexpected fixture auxiliary tab");}}if(nsgTabFailure)throw nsgTabFailure;};
const nsgClose=async()=>{nsgTabPhase="close";const ownedTarget=nsgTab.targetId;let closeFailure;try{await closeTab(nsgTab);}catch(error){const missing=/Tab ([A-Fa-f0-9]+) is no longer available/.exec(String(error));if(!missing||missing[1]!==ownedTarget)closeFailure=new Error("task-owned fixture tab close failed");}const deadline=Date.now()+15000;do{const current=await listBrowserTabs();try{nsgInventoryGuard(current);}catch(error){closeFailure||=error;}if(!current.some(tab=>nsgOwnedTargets.has(tab.targetId))){nsgTab=undefined;if(closeFailure)throw closeFailure;return;}if(Date.now()>=deadline)throw closeFailure||new Error("task-owned fixture tab closure not ready");}while(true);};
try {
 nsgBaseline=new Set((await listBrowserTabs()).map(tab=>tab.targetId));
 nsgTab=await openTab("about:blank");
 nsgOwnedTargets.add(nsgTab.targetId);
 // The pre-open inventory never absorbs later auxiliary targets. Await the exact
 // handle returned by openTab; an incomplete inventory is not a popup baseline.
 const nsgOwnedTabs=async()=>{const deadline=Date.now()+15000;do{const current=await listBrowserTabs();nsgInventoryGuard(current);if(current.some(tab=>tab.targetId===nsgTab.targetId)&&!current.some(tab=>nsgOwnedTargets.has(tab.targetId)&&tab.targetId!==nsgTab.targetId))return current;}while(Date.now()<deadline);throw new Error("task-owned fixture tab inventory readiness missing");};
 await nsgOwnedTabs();
 const nsgLocator=(spec)=>{let item=nsgTab;for(let index=0;index<spec.length;index++){const step=spec[index];if(step.kind==="locator"){let selector=step.selector;if(spec[index+1]?.kind==="filter"){const has=spec[++index].has;if(!has.every(part=>part.kind==="locator"))throw new Error("unsupported descendant filter");selector+=":has("+has.map(part=>part.selector).join(" ")+")";}item=item.locator(selector);}else if(step.kind==="first")item=item.first();else throw new Error("unknown locator step");}return item;};
 let nsgEvaluation=0;
 const nsgEvaluate=async(frame,source,arg)=>{
  source=typeof source==="function"?source.toString():source;
  const text=await nsgTab.evaluate(async({source,encoded,nonce,packer,unpacker,id,target})=>{
   const documents=[];const visit=win=>{documents.push(win.document);for(let index=0;index<win.frames.length;index++)visit(win.frames[index]);};visit(window);
   const doc=target?documents.find(doc=>doc.location.href===target):document;if(!doc)throw new Error("target fixture document disappeared: "+target);
   const holder=doc.createElement("script");holder.type="application/json";holder.id=id;
   const code=doc.createElement("script");code.nonce=nonce;
   code.textContent="(async()=>{const pack="+packer+";const unpack="+unpacker+";const output=document.getElementById("+JSON.stringify(id)+");try{const value=await ("+source+")(unpack("+JSON.stringify(encoded)+"));output.textContent=pack({value});}catch(error){output.textContent=pack({error:String(error)});}})();";
   const completed=new Promise(resolve=>{const observer=new MutationObserver(()=>{if(holder.textContent){observer.disconnect();resolve(holder.textContent);}});observer.observe(holder,{childList:true,characterData:true,subtree:true});});
   doc.documentElement.append(holder,code);
   try{return await completed;}finally{holder.remove();code.remove();}
  },{source,encoded:nsgPack(arg),nonce:${JSON.stringify(nonce)},packer:${JSON.stringify(pack.toString())},unpacker:${JSON.stringify(unpack.toString())},id:nsgToken+"-evaluation-"+(++nsgEvaluation),target:typeof frame==="string"?frame:undefined});
  const result=nsgUnpack(text);if(!result||!Object.hasOwn(result,"value")&&!result.error)throw new Error("missing main-world observation");if(result.error)throw new Error(result.error);return result.value;
 };
 const nsgFrameTargets=()=>nsgTab.evaluate(()=>{const urls=[];const visit=win=>{urls.push(win.location.href);for(let index=0;index<win.frames.length;index++)visit(win.frames[index]);};visit(window);return urls;});
 const nsgCollect=async(collected={pageErrors:[],violations:[],outgoing:[]})=>{
  await nsgOwnedTabs();
  if(!nsgGuarded)return collected;
  const urls=await nsgFrameTargets();const figure=nsgExpected.includes("/__nsg_figure?");
  if(urls.length!==(figure?1:2)||!urls.includes(nsgExpected)||(!figure&&!urls.includes(${JSON.stringify(origin + "/public/index.html")})))throw new Error("unexpected fixture frame/navigation: "+JSON.stringify(urls));
  for(const url of urls){const state=await nsgEvaluate(url,async(token)=>{
   const observer=window.__nsgAsideObserver;if(!observer||observer.token!==token||document.documentElement.dataset.nsgObserverReady!==token)throw new Error("fixture observer readiness missing at "+location.href);
   if(navigator.serviceWorker.controller||(await navigator.serviceWorker.getRegistrations()).length)throw new Error("fixture service worker could bypass recorder");
   await observer.barrier();await observer.barrier();return observer.drain();
  },nsgToken);if(!state||!state.documentId||!Number.isInteger(state.drain)||!Array.isArray(state.errors)||!Array.isArray(state.violations)||!Array.isArray(state.outgoing))throw new Error("incomplete observer collection");const prior=nsgDocuments.get(url);if(prior&&(prior.documentId!==state.documentId||state.drain!==prior.drain+1))throw new Error("fixture document changed or collection delivery missing: "+url);nsgDocuments.set(url,{documentId:state.documentId,drain:state.drain});collected.pageErrors.push(...state.errors);collected.violations.push(...state.violations);collected.outgoing.push(...state.outgoing);}
  return collected;
 };
 while(true){
  const command=nsgUnpack(await(await fetch(nsgBase+"next")).text());
  nsgTabPhase="fixture";
  let value;let error;let closing=false;
  try {
   const source=command.fn;
   if(command.operation==="goto"){nsgExpected=command.url;nsgDocuments.clear();nsgGuarded=true;await nsgTab.goto(command.url,{waitUntil:"domcontentloaded"});if(!command.url.includes("/__nsg_figure?"))await nsgTab.waitForFunction(()=>document.querySelector("iframe")?.contentDocument?.readyState==="complete"&&document.querySelector("iframe").contentDocument.location.pathname==="/public/index.html");}
   else if(command.operation==="probe"){
    if(command.sourceOrigin)nsgKnownTaskOrigins.add(command.sourceOrigin);
    nsgGuarded=true;nsgExpected=command.url.replace("/__nsg_probe","/__nsg_bootstrap");nsgDocuments.clear();await nsgTab.goto(nsgExpected,{waitUntil:"domcontentloaded"});
    await nsgTab.waitForFunction(()=>document.querySelector("iframe")?.contentDocument?.readyState==="complete"&&document.querySelector("iframe").contentDocument.location.pathname==="/public/index.html");console.log((await snapshot(nsgTab)).tree);
    const earlyTopology=await nsgCollect();
    nsgExpected=command.url;nsgDocuments.clear();await nsgTab.goto(command.url,{waitUntil:"domcontentloaded"});
    await nsgTab.waitForFunction(()=>document.querySelector("iframe")?.contentDocument?.readyState==="complete"&&document.querySelector("iframe").contentDocument.location.pathname==="/public/index.html");console.log((await snapshot(nsgTab)).tree);
    const initial=await nsgCollect();if(initial.pageErrors.length||initial.violations.length)throw new Error("initial fixture collectors were not clean: "+JSON.stringify(initial));value={earlyTopology,independentErrors:[],cspControls:[],popupControls:[],formPopupControls:[],guards:{}};
    const observed={pageErrors:[],violations:[],outgoing:[]};
    const collect=async()=>{const state=await nsgCollect();for(const key of Object.keys(observed))observed[key].push(...state[key]);return state;};
    for(const frame of await nsgFrameTargets()){
     for(const kind of ["async-exception","unhandled-rejection"]){
      await nsgEvaluate(frame,async(kind)=>{const label=window===window.top?"top":"iframe";await new Promise(resolve=>{window.addEventListener(kind==="async-exception"?"error":"unhandledrejection",resolve,{once:true});if(kind==="async-exception")queueMicrotask(()=>{throw new Error("NSG_"+label+"_"+kind);});else Promise.reject("NSG_"+label+"_"+kind);});},kind);
      const state=await collect();value.independentErrors.push({errors:state.pageErrors});
     }
     await nsgEvaluate(frame,async()=>{const response=await fetch("/__nsg_probe_write",{method:"POST",body:"negative control; no state written"});if(response.status!==501)throw new Error("POST rejection control expected501");});await collect();
     await nsgEvaluate(frame,async(sink)=>{await fetch(sink+"/blocked-post",{method:"POST",body:"must not leave fixture"}).catch(()=>{});},command.sink);
     {const state=await collect();value.cspControls.push({directive:"connect-src",...state});}
     await nsgEvaluate(frame,async(sink)=>{const target=document.createElement("iframe");target.name="nsg-form-negative-target";target.src="/public/index.html";const loaded=new Promise(resolve=>target.addEventListener("load",resolve,{once:true}));document.body.append(target);await loaded;const form=document.createElement("form");form.action=sink+"/blocked-form";form.method="POST";form.target=target.name;document.body.append(form);const blocked=new Promise(resolve=>{const handler=event=>{if(event.effectiveDirective==="form-action"){window.removeEventListener("securitypolicyviolation",handler);resolve();}};window.addEventListener("securitypolicyviolation",handler);});form.submit();await blocked;form.remove();target.remove();},command.sink);
     {const state=await collect();const expected=state.pageErrors.filter(message=>message==="unexpected fixture frame topology mutation");if(expected.length!==2)throw new Error("form control did not observe actual temporary frame topology");state.pageErrors=state.pageErrors.filter(message=>message!=="unexpected fixture frame topology mutation");observed.pageErrors=observed.pageErrors.filter(message=>message!=="unexpected fixture frame topology mutation");value.cspControls.push({directive:"form-action",...state});}
    }
    for(const frame of await nsgFrameTargets())for(const href of ["/public/index.html","#popup"]){
     const before=(await nsgOwnedTabs()).map(tab=>tab.targetId);
     await nsgEvaluate(frame,href=>{const anchor=document.createElement("a");anchor.href=href;anchor.target="_blank";anchor.rel="noopener";anchor.textContent="Controlled full-screen fixture link";document.body.append(anchor);anchor.click();anchor.remove();},href);
     const state=await nsgCollect();value.popupControls.push({...state,newTabs:(await nsgOwnedTabs()).filter(tab=>!before.includes(tab.targetId)).length});
    }
    for(const frame of await nsgFrameTargets())for(const method of ["submit","requestSubmit"]){
     const before=(await nsgOwnedTabs()).map(tab=>tab.targetId);
     await nsgEvaluate(frame,method=>{const form=document.createElement("form");form.action="/public/index.html";form.target="_blank";document.body.append(form);form[method]();form.remove();},method);
     const state=await nsgCollect();value.formPopupControls.push({...state,newTabs:(await nsgOwnedTabs()).filter(tab=>!before.includes(tab.targetId)).length});
    }
    await nsgEvaluate(nsgTab,()=>document.querySelector("iframe").contentWindow.postMessage({nsgObserverNegativeControl:true},location.origin));await collect();
    const guard=async(name,mutate,restore,pattern)=>{await mutate();try{await nsgCollect();throw new Error("negative control guard unexpectedly accepted "+name);}catch(error){if(!pattern.test(String(error)))throw error;value.guards[name]=nsgFailure(error);}finally{await restore();}};
    await guard("missingReadiness",()=>nsgEvaluate(nsgTab,()=>delete document.documentElement.dataset.nsgObserverReady),()=>nsgEvaluate(nsgTab,token=>document.documentElement.dataset.nsgObserverReady=token,nsgToken),/observer readiness missing/);
    await guard("extraFrame",()=>nsgEvaluate(nsgTab,async()=>{const extra=document.createElement("iframe");extra.id="nsg-extra-control";extra.src="about:blank";const loaded=new Promise(resolve=>extra.addEventListener("load",resolve,{once:true}));document.body.append(extra);await loaded;}),()=>nsgEvaluate(nsgTab,()=>document.getElementById("nsg-extra-control").remove()),/unexpected fixture frame/);
    {const state=await collect();if(state.pageErrors.filter(message=>message==="unexpected fixture frame topology mutation").length!==2)throw new Error("transient extra frame was not observed");observed.pageErrors=observed.pageErrors.filter(message=>message!=="unexpected fixture frame topology mutation");}
    await guard("changedDocument",()=>nsgEvaluate(nsgTab,async()=>{const frame=document.querySelector("iframe");const loaded=new Promise(resolve=>frame.addEventListener("load",resolve,{once:true}));frame.src="/public/index.html?unexpected-document";await loaded;}),()=>nsgEvaluate(nsgTab,async()=>{const frame=document.querySelector("iframe");const loaded=new Promise(resolve=>frame.addEventListener("load",resolve,{once:true}));frame.src="/public/index.html";await loaded;}),/unexpected fixture frame/);
    try{await nsgCollect();throw new Error("reloaded document was accepted");}catch(error){if(!/fixture document changed/.test(String(error)))throw error;value.guards.reloadedDocument=nsgFailure(error);}
    nsgDocuments.clear();await nsgCollect();value.observed=observed;
    await guard("missingDelivery",()=>nsgEvaluate(nsgTab,()=>{window.__nsgAsideObserver.drain();}),async()=>{nsgDocuments.clear();await nsgCollect();},/collection delivery missing/);
   }
   else if(command.operation==="viewport"){nsgViewport=command.value;await nsgTab.setViewportSize(command.value);}
   else if(command.operation==="media"){nsgMedia=command.value;await nsgTab.emulateMedia(command.value);}
   else if(command.operation==="evaluate")value=await nsgEvaluate(nsgTab,source,command.arg);
   else if(command.operation==="wait")value=await nsgEvaluate(nsgTab,"async(arg)=>{const predicate=("+source+");const deadline=performance.now()+15000;while(!await predicate(arg)){if(performance.now()>deadline)throw new Error('fixture predicate timed out');await new Promise(requestAnimationFrame);}}",command.arg);
   else if(command.operation==="frame")value=await nsgEvaluate(command.url,source,command.arg);
   else if(command.operation==="locator"){const locator=nsgLocator(command.spec);value=command.method==="evaluate"?await nsgEvaluate(nsgTab,"(input)=>{let nodes=[document];for(let index=0;index<input.spec.length;index++){const step=input.spec[index];if(step.kind==='locator')nodes=nodes.flatMap(node=>[...node.querySelectorAll(step.selector)]);else if(step.kind==='first')nodes=nodes.slice(0,1);else throw new Error('unsupported evaluation selector');}if(nodes.length!==1)throw new Error('fixture evaluation requires one element, got '+nodes.length);return ("+source+")(nodes[0],input.arg);}",{spec:command.spec,arg:command.arg}):command.method==="allTextContents"?await locator.evaluateAll(nodes=>nodes.map(node=>node.textContent)):await locator[command.method](...(command.args||[]));}
   else if(command.operation==="keyboard")await nsgTab.keyboard.press(command.key);
   else if(command.operation==="close"){
    closing=true;
    if(command.fault==="error")await nsgEvaluate(nsgTab,async()=>{await new Promise(resolve=>{window.addEventListener("error",resolve,{once:true});queueMicrotask(()=>{throw new Error("NSG final drain exception");});});});
    if(command.fault==="outgoing")await nsgEvaluate(nsgTab,()=>document.querySelector("iframe").contentWindow.postMessage({nsgFinalDrainControl:true},location.origin));
    if(command.fault==="post")await nsgEvaluate(nsgTab,async()=>{await fetch("/__nsg_probe_write",{method:"POST",body:"late read-only violation"});});
   }
   else throw new Error("unknown Aside operation: "+command.operation);
   if(["goto","keyboard"].includes(command.operation)||command.method==="focus"){const state=await snapshot(nsgTab);console.log(state.diff||state.tree);}
  }catch(caught){error=nsgFailure(caught);}
  let observed={pageErrors:[],violations:[],outgoing:[]};let collectorFailure;try{await nsgCollect(observed);}catch(caught){collectorFailure=nsgFailure(caught);}
  if(command.operation==="probe"&&value?.observed){observed=value.observed;delete value.observed;}
  const frames=await nsgFrameTargets();
  if(closing){await nsgClose();}
  const data=Buffer.from(nsgPack({id:command.id,value,error,collectorFailure,frames,ownershipFailure:nsgOwnershipDiagnostic,...observed})).toString("base64");
  for(let index=0;index*6000<data.length;index++){const part=data.slice(index*6000,(index+1)*6000);const reply=await fetch(nsgBase+"result?id="+command.id+"&index="+index+"&last="+((index+1)*6000>=data.length?1:0)+"&data="+encodeURIComponent(part));if(!reply.ok)throw new Error("observation delivery failed");}
  nsgCount++;if(closing)break;
  if(command.operation==="probe"&&!error){await nsgClose();nsgTab=await openTab("about:blank");nsgOwnedTargets.add(nsgTab.targetId);nsgTabPhase="open-replacement";await nsgOwnedTabs();if(nsgViewport)await nsgTab.setViewportSize(nsgViewport);if(nsgMedia)await nsgTab.emulateMedia(nsgMedia);}
 }
 console.log(JSON.stringify({nsgAsideReceipt:true,backend:"aside",commands:nsgCount,closed:true}));
}finally{if(nsgTab)await nsgClose();}`;
  const child = spawn(process.env.ASIDE_BIN || "aside", ["repl", "--json", "--file", "-", ...(process.env.NSG_ASIDE_PROFILE ? ["--profile", process.env.NSG_ASIDE_PROFILE] : [])], { stdio: ["pipe", "pipe", "pipe"], detached: true });
  let stdout = ""; let stderr = "";
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  let childClosed = false, forceTimer, exitTimer, resolveExit;
  const signalChildGroup = (signal) => {
    if (!child.pid) return;
    try { process.kill(-child.pid, signal); }
    catch (error) { if (error.code !== "ESRCH") fail(error); }
  };
  const groupExists = () => {
    if (!child.pid) return false;
    try { process.kill(-child.pid, 0); return true; }
    catch (error) { if (error.code === "ESRCH") return false; if (error.code === "EPERM") return true; throw error; }
  };
  let groupCleanup;
  const ensureGroupAbsent = () => groupCleanup ||= (async () => {
    if (!groupExists()) return;
    process.stderr.write("Task-owned Aside CLI process-group SIGKILL cleanup; leader closure is not group absence\n");
    signalChildGroup("SIGKILL");
    const deadline = Date.now() + 3000;
    await new Promise((resolve, reject) => {
      const inspect = () => {
        try {
          if (!groupExists()) { resolve(); return; }
          if (Date.now() >= deadline) { reject(new Error("Aside task process group still present after SIGKILL; cleanup failed")); return; }
          setImmediate(inspect);
        } catch (error) { reject(error); }
      };
      inspect();
    });
  })();
  const exited = new Promise((resolve) => {
    resolveExit = resolve;
    child.on("error", () => { fail(new Error("Aside CLI could not start")); childClosed = true; resolve(-1); });
    child.on("close", (code) => {
      childClosed = true;
      let category = "Aside fixture operation failed";
      try {
        const envelope = JSON.parse(stdout);
        category = fixtureFailure(envelope.run?.error);
        for (const item of envelope.run?.content || []) {
          if (item?.type !== "text" || typeof item.text !== "string") continue;
          for (const line of item.text.split("\n")) {
            try { reportOwnership(JSON.parse(line).nsgFixtureOwnershipFailure); } catch {}
          }
        }
      } catch {}
      if (pending) fail(new Error(`Aside exited before observation (${code}): ${category}`));
      resolve(code);
    });
  });
  child.stdin.on("error", () => fail(new Error("Aside CLI input delivery failed")));
  child.stdin.end(worker);
  const timer = setTimeout(() => {
    fail(new Error(`Aside call exceeded fixture CLI deadline (${guardMs}ms)`));
    signalChildGroup("SIGTERM");
    forceTimer = setTimeout(() => {
      process.stderr.write("Task-owned Aside CLI SIGKILL escalation after ignored SIGTERM\n");
      signalChildGroup("SIGKILL");
    }, 1000);
    exitTimer = setTimeout(() => {
      if (!childClosed) { fail(new Error("Aside CLI exit unconfirmed after SIGKILL; cleanup failed")); resolveExit(-1); }
    }, 3000);
  }, guardMs);
  const locator = (spec) => ({
    locator: (selector) => locator([...spec, { kind: "locator", selector }]),
    filter: ({ has }) => locator([...spec, { kind: "filter", has: has.spec }]),
    first: () => locator([...spec, { kind: "first" }]),
    spec,
    ...Object.fromEntries(["focus", "count", "textContent", "allTextContents", "getAttribute"].map((method) => [method, (...args) => rpc("locator", { spec, method, args })])),
    evaluate: (fn, arg) => rpc("locator", { spec, method: "evaluate", fn: fn.toString(), arg }),
  });
  let probed = false;
  const probe = async () => {
    if (!routes.some(([pattern]) => pattern === "**/public/index.html")) return;
    if (!probed) {
      probing = true;
      try { await rpc("probe", { url: `${origin}/__nsg_probe`, sink: sinkOrigin, nonce, sourceOrigin }); probed = true; }
      finally { probing = false; }
    }
  };
  const page = {
    fixtureSinkOrigin: sinkOrigin,
    locator: (selector) => locator([{ kind: "locator", selector }]),
    evaluate: (fn, arg) => rpc("evaluate", { fn: fn.toString(), arg }),
    waitForFunction: (fn, arg) => rpc("wait", { fn: fn.toString(), arg }),
    goto: async (url) => { const parsed = new URL(url); assert(parsed.protocol === "http:" && parsed.hostname === "127.0.0.1", "fixture source must be task-owned loopback"); sourceOrigin = parsed.origin; await probe(); return rpc("goto", { url: origin + parsed.pathname + parsed.search }); },
    setContent: async (body) => { content = body; await probe(); return rpc("goto", { url: `${origin}/__nsg_figure?revision=${sequence}` }); },
    on: (event, handler) => { assert(["pageerror", "request"].includes(event)); listeners.set(event, handler); },
    route: async (pattern, handler) => { assert(["**/public/index.html", "**/ontology-map.json"].includes(pattern)); routes.push([pattern, handler]); },
    exposeFunction: async (name, handler) => { assert(["captureOutgoing", "captureNonParent"].includes(name)); exposed.set(name, handler); },
    addInitScript: async (fn) => { initScripts.push(fn.toString()); },
    frames: () => frameUrls.map((url) => ({ url: () => url, evaluate: (fn, arg) => rpc("frame", { url, fn: fn.toString(), arg }) })),
    keyboard: { press: (key) => rpc("keyboard", { key }) },
  };
  const newPage = async (options = {}) => {
    if (options.viewport) await rpc("viewport", { value: options.viewport });
    if (options.reducedMotion) await rpc("media", { value: { reducedMotion: options.reducedMotion } });
    return page;
  };
  return {
    newPage,
    newContext: async (options) => ({ newPage: () => newPage(options) }),
    close: async () => {
      try {
        const fault = process.env.NSG_ASIDE_CLOSE_CONTROL;
        assert(!fault || ["error", "outgoing", "post"].includes(fault), "unsupported close-boundary test control");
        if (!failure) await rpc("close", { fault });
        const code = await exited;
        await ensureGroupAbsent();
        if (failure) throw failure;
        let envelope;try{envelope=JSON.parse(stdout);}catch{throw new Error("Aside CLI execution envelope invalid");}
        assert.equal(code, 0, "Aside CLI failed");
        assert(envelope?.run?.error === null, "Aside CLI reported an error");
        assert(Array.isArray(envelope.run.content) && envelope.run.content.every(item=>item&&typeof item==="object"&&(item.type!=="text"||typeof item.text==="string")), "Aside CLI omitted content");
        const receipts = envelope.run.content.filter((item) => item.type === "text").flatMap((item) => item.text.split("\n")).map((text) => { try { return JSON.parse(text); } catch { return null; } }).filter((item) => item?.nsgAsideReceipt);
        assert.equal(receipts.length, 1, "Aside CLI omitted its completion receipt");
        const completion=receipts[0];assert(Object.keys(completion).sort().join(",")==="backend,closed,commands,nsgAsideReceipt"&&completion.nsgAsideReceipt===true&&completion.backend==="aside"&&completion.commands===sequence&&completion.closed===true,"Aside CLI completion receipt invalid");
        assert.deepEqual(cumulativeErrors, [], "final fixture pageErrors guard rejected");
        assert.deepEqual(cumulativeOutgoing, [], "final fixture outgoing guard rejected");
        assert.deepEqual(cumulativeViolations, [], "final fixture CSP guard rejected");
        assert(requests.filter((request) => !request.probe).every((request) => request.method === "GET"), "final fixture GET-only guard rejected");
        if (probed) {
          assert(observerControls, "fixture observer controls were not completed");
          for (const path of ["/dashboard/index.html", "/public/index.html", "/dashboard/ontology-map.json", "/dashboard/disclosure-reference.json"]) assert(requests.some((item) => !item.probe && item.path === path && item.method === "GET"), `missing actual fixture GET receipt: ${path}`);
          assert.equal(sinkRequests, 0, "fixture containment failed");
        }
        const receipt = { nsgAsideReceipt: true, backend: "aside", commands: sequence, closed: true, driver: "tests/" + process.argv[1].split("/").pop(), fixture: "publication/component transport only; NOT GAMEPLAY", observerModel: "bounded loopback HTTP recorder + early DOM error/CSP collectors; not native network monitoring", nativeRequestAndPageerror: "unavailable; prior real controls reported zero callbacks; not recertified", fixtureGetReceipts: approvedGetReceiptPaths.filter(path => requests.some(request => !request.probe && request.method === "GET" && request.path === path)), ...(probed ? { observerControls } : {}) };
        process.stderr.write(JSON.stringify(receipt) + "\n");
        if (process.env.NSG_ASIDE_RECEIPT_PATH) fs.appendFileSync(process.env.NSG_ASIDE_RECEIPT_PATH, JSON.stringify(receipt) + "\n");
      } finally {
        clearTimeout(timer);
        clearTimeout(forceTimer); clearTimeout(exitTimer);
        let cleanupError;
        try { await ensureGroupAbsent(); } catch (error) { cleanupError = error; }
        if (nextResponse) nextResponse.destroy();
        server.closeAllConnections(); sink.closeAllConnections();
        await Promise.all([new Promise((resolve) => server.close(resolve)), new Promise((resolve) => sink.close(resolve))]);
        if (cleanupError) throw cleanupError;
      }
    },
  };
}
module.exports = { chromium: { launch }, fixtureFailure };
