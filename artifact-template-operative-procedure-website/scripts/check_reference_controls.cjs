// Focused regression check for the reference camera and responsive interaction handlers.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = path.resolve(__dirname, '../assets/source');
const runtime = fs.readFileSync(path.join(source, 'assets/app.js'), 'utf8');
const html = fs.readFileSync(path.join(source, 'index.html'), 'utf8');
new vm.Script(runtime);
assert(!/operativeView|setOperativeView/.test(runtime + html), 'Removed camera action must not survive');
assert(runtime.includes('interactionActive = true; pickDirty = false'), 'Beginning a gesture must discard queued picking');
assert(runtime.includes('if (interactionActive)\n        pickDirty = false'), 'Redraws during interaction must suppress picking');
assert(runtime.includes('if (pointers.size)\n        return; interactionActive = false'), 'A held gesture must not restore full rendering or picking during a slow frame');
const start = runtime.indexOf('    // One pointer orbits upright');
const end = runtime.indexOf("    canvas.addEventListener('webglcontextlost'", start);
assert(start >= 0 && end > start, 'Camera handlers should be present');
const events = {}, orbits = [], rolls = [], zooms = [], picks = [], renders = [];
const canvas = { setPointerCapture() {}, getBoundingClientRect: () => ({left:0,top:0,width:800,height:600}), addEventListener:(k,v)=>events[k]=v };
const context = {canvas, host:{clientHeight:600}, distance:10, scale:1, viewZoom:1, pan:[0,0], available:true, interactionActive:false, surgeonChosen:false, animationToken:0,
  window:{addEventListener:(type,callback)=>events[type]=callback},
  stopGlide(){}, markInteraction(){}, render(...a){renders.push(a)}, draw(){}, cacheLabelVisibility(){}, clearSelection(){},
  orbitByDrag:(...a)=>orbits.push(a), rollView:a=>rolls.push(a), zoomBy:(...a)=>zooms.push(a), pickIdAt:()=>7, select:id=>picks.push(id),
  $:()=>({click(){}}), wrapAngle:a=>a};
vm.runInNewContext(runtime.slice(start,end), context);
const event=(x,y,extra={})=>({pointerId:1,clientX:x,clientY:y,button:0,buttons:1,altKey:false,shiftKey:false,preventDefault(){},...extra});
const move=(x,y,extra)=>canvas.onpointermove(event(x,y,extra));
canvas.onpointerdown(event(100,100)); move(102,101); move(99,100); move(103,101); move(100,100);
assert.equal(orbits.length,0,'Back-and-forth press jitter must not accumulate into a drag');
move(106,102); assert.deepEqual(orbits,[[6,2]],'Normal drag must orbit both axes after radial threshold');
move(116,109); assert.deepEqual(orbits[1],[10,7]); move(100,100);
canvas.onpointerup(event(100,100)); assert.equal(picks.length,0,'Returning a real drag to its start must not select anatomy');
canvas.onpointerdown(event(200,200)); move(206,200,{altKey:true}); assert.equal(orbits.length,3,'Alt-drag must not orbit the head');
assert.equal(rolls.length,1,'Alt-drag should roll the camera'); canvas.onpointerup(event(206,200,{altKey:true}));
canvas.onpointerdown(event(10,10)); move(30,25,{shiftKey:true}); assert(context.pan[0]!==0 && context.pan[1]!==0,'Shift drag should pan'); canvas.onpointerup(event(30,25));
canvas.onpointerdown(event(10,10)); move(20,20,{buttons:2}); canvas.onpointerup(event(20,20,{button:2}));
canvas.onpointerdown(event(10,10,{pointerType:'touch'})); move(30,25,{pointerType:'touch'}); assert.equal(orbits.length,4,'Touch drag should orbit after the threshold');
canvas.onpointerdown(event(100,25,{pointerId:2,pointerType:'touch'})); move(120,60,{pointerId:2,pointerType:'touch'});
assert.equal(rolls.length,1,'Touch movement must preserve roll');
assert(zooms.some(x=>x[1]===false),'Pinch zoom should avoid immediate picking refresh');
canvas.onpointerup(event(30,25,{pointerType:'touch'})); canvas.onpointerup(event(120,60,{pointerId:2,pointerType:'touch'})); assert.equal(picks.length,0,'Multi-touch must not select anatomy');
canvas.onpointerdown(event(10,10)); canvas.onpointerup(event(10,10)); assert.deepEqual(picks,[7],'Click selection should remain immediate');
canvas.onkeydown({key:'q',code:'KeyQ',preventDefault(){}});
assert.equal(rolls.length,1,'Q alone must preserve roll');
canvas.onkeydown({key:'œ',code:'KeyQ',altKey:true,preventDefault(){}});
assert.equal(rolls.length,2,'Option+Q must roll');
canvas.onpointerdown(event(10,10)); events.lostpointercapture(event(10,10));
move(20,20); assert.equal(orbits.length,4,'Lost capture must clear the gesture');
canvas.onpointerdown(event(10,10)); events.blur();
move(25,25); assert.equal(orbits.length,4,'Window blur must clear the gesture');
const prior=zooms.length; events.wheel({...event(0,0),deltaY:20,deltaMode:0}); canvas.onkeydown({...event(0,0),key:'+'});
assert.equal(zooms.length,prior+2,'Wheel and keyboard zoom should work');
assert(renders.some(x=>x[0]===false),'Camera movement should render without picking every frame');
// Exercise the actual orientation math, not only the handler's call to orbitByDrag.
const mathStart = runtime.indexOf('    function qMul('), mathEnd = runtime.indexOf('    const POSE_PIVOT', mathStart);
const orbitStart = runtime.indexOf('    function orbitByDrag('), orbitEnd = runtime.indexOf('    function markInteraction(', orbitStart);
assert(mathStart >= 0 && mathEnd > mathStart && orbitStart >= 0 && orbitEnd > orbitStart);
const math = vm.createContext({});
vm.runInContext(`${runtime.slice(mathStart, mathEnd)}\nlet viewQ=[0,0,0,1], camFrame='head', viewCache=null, startQ; function viewChanged(){viewCache=null}\n${runtime.slice(orbitStart,orbitEnd)}`,math);
const eye = () => Array.from(vm.runInContext('qMat(viewQ).slice(6,9)',math));
const near = (a,b) => assert(Math.abs(a-b)<1e-5,`${a} should equal ${b}`);
for(let i=0;i<100;i++)vm.runInContext('orbitByDrag(1,0)',math);
let direction=eye(); near(direction[0],Math.sin(-.8)); near(direction[2],Math.cos(-.8)); near(direction[1],0);
for(let i=0;i<50;i++)vm.runInContext('orbitByDrag(0,-1)',math);
direction=eye(); near(direction[0],Math.cos(-.4)*Math.sin(-.8)); near(direction[1],Math.sin(-.4)); near(direction[2],Math.cos(-.4)*Math.cos(-.8));
vm.runInContext("camFrame='world';viewQ=qLook([0,1,0],[0,0,1]);orbitByDrag(10,-10)",math);
direction=eye(); near(direction[0],Math.cos(-.08)*Math.sin(.08)); near(direction[1],Math.cos(-.08)*Math.cos(-.08)); near(direction[2],Math.sin(-.08));
vm.runInContext("viewQ=qLook([0,0,1],[0,1,0]);camFrame='head';orbitByDrag(1,1)",math);
assert(eye().every(Number.isFinite),'A drag at the pole must stay finite');
vm.runInContext("viewQ=qLook([0,0,1],[0,1,0]);orbitByDrag(10,-10)",math);
const front=Array.from(vm.runInContext('mApply(qMat(viewQ),[0,0,2])',math));
assert(front[0]>0 && front[1]>0,'Dragging right and up should move a visible front landmark right and up');
for (const [frame,eye,up,landmark] of [
  ['head',[0,0,1],[0,1,0],[0,0,2]], ['world',[0,1,0],[0,0,1],[0,2,0]]
]) {
  vm.runInContext(`camFrame='${frame}'; viewQ=qLook(${JSON.stringify(eye)},${JSON.stringify(up)}); startQ=[...viewQ]`,math);
  for (let i=0;i<120;i++) vm.runInContext('orbitByDrag(2*Math.PI/.008/120,0)',math);
  near(Math.abs(vm.runInContext('viewQ.reduce((sum,value,index)=>sum+value*startQ[index],0)',math)),1);
  const projected = vm.runInContext(`viewQ=qMul(qAxis([0,0,1],.8),startQ);
    orbitByDrag(10,-10); mApply(qMat(viewQ),${JSON.stringify(landmark)})`,math);
  assert(projected[0]>0&&projected[1]>0,'Orbit must follow the pointer after an explicit roll');
}
const timerStart=runtime.indexOf('    function markInteraction('), timerEnd=runtime.indexOf('    // Camera glide:',timerStart);
const timers=[], refreshes=[], held=new Map([[1,[0,0]]]);
const timing={pointers:held, interactionActive:false, pickDirty:true, interactionTimer:0,
  setTimeout:f=>{timers.push(f);return timers.length},clearTimeout(){},render:v=>refreshes.push(v)};
vm.createContext(timing);vm.runInContext(runtime.slice(timerStart,timerEnd)+'\nmarkInteraction()',timing);
assert.equal(timing.interactionActive,true);assert.equal(timing.pickDirty,false);
timers.shift()();assert.equal(timing.interactionActive,true,'Idle timer must not end an active held gesture');
assert.equal(refreshes.length,0,'Held pointer must not trigger full-resolution picking');
held.clear();vm.runInContext('markInteraction()',timing);timers.shift()();
assert.equal(timing.interactionActive,false);assert.deepEqual(refreshes,[true],'Full-quality picking resumes after release');
console.log('PASS: continuous orbit, pole stability, radial drag threshold, held-gesture quality and picking');

const clearanceStart = runtime.indexOf('    function hiddenByClearance()');
const clearanceEnd = runtime.indexOf('    function baseVisible(',clearanceStart);
assert(clearanceStart >= 0 && clearanceEnd > clearanceStart);
const moving = {id:'moving'}, stationary = {id:'stationary'};
const scene = {
    separateLayers:false, procedure:true, steps:[{id:'open'},{id:'close'}], stage:0, opening:0,
    config:{b:'two',a:'one'}, operativeSide:()=> 'right',
    displayConflicts:{'a=one&b=two|right|open':[['moving','stationary']]},
    clearanceMeshById:new Map([[moving.id,moving],[stationary.id,stationary]]),
    baseVisible:(mesh,wholeStep)=>!!mesh && !mesh.hidden &&
        (mesh===stationary||wholeStep||scene.opening>.5), moving, stationary,
};
vm.createContext(scene);
vm.runInContext(runtime.slice(clearanceStart,clearanceEnd),scene);
for (const p of [0,.25,.5,.75,1]) {
    scene.opening=p;
    assert(!vm.runInContext('visible(stationary)',scene),'Overlap should hide from the start through the end');
    if (p>.5) assert(vm.runInContext('visible(moving)',scene),'The moving participant must remain visible');
}
scene.stage=1;
assert(vm.runInContext('visible(stationary)',scene),'Stationary mesh should return in the next step');
scene.stage=0; moving.hidden=true;
assert(vm.runInContext('visible(stationary)',scene),'A layer hidden by the user must not hide other objects');
console.log('PASS: step-wide visibility, next-step restoration and explicit layer preferences');
