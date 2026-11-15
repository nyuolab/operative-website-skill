// Focused regression check for the reference camera and responsive interaction handlers.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const source = path.resolve(__dirname, '../assets/source');
const revision = JSON.parse(fs.readFileSync(path.join(source, 'reference-revision.json'), 'utf8'));
assert(/^[0-9a-f]{40}$/.test(revision.referenceCommit), 'Record the source website commit');
assert(revision.referenceSha256['assets/app.js'], 'Pin the actual website runtime');
for (const [name, hash] of Object.entries(revision.referenceSha256)) {
    assert.equal(createHash('sha256').update(fs.readFileSync(path.join(source, name))).digest('hex'), hash,
        `Reference file differs from website commit: ${name}`);
}
const runtime = fs.readFileSync(path.join(source, 'assets/app.js'), 'utf8');
const html = fs.readFileSync(path.join(source, 'index.html'), 'utf8');
new vm.Script(runtime);
assert(!/operativeView|setOperativeView/.test(runtime + html), 'Removed camera action must not survive');
assert(runtime.includes('interactionActive = true; pickDirty = false'), 'Beginning a gesture must discard queued picking');
assert(runtime.includes('if (interactionActive)\n        pickDirty = false'), 'Redraws during interaction must suppress picking');
assert(runtime.includes('if (pointers.size)\n        return; interactionActive = false'), 'A held gesture must not restore full rendering or picking during a slow frame');
const start = runtime.indexOf('    // Pterional PR #1 trackball');
const end = runtime.indexOf("    canvas.addEventListener('webglcontextlost'", start);
assert(start >= 0 && end > start, 'Camera handlers should be present');
const events = {}, orbits = [], rolls = [], zooms = [], picks = [], renders = [];
const canvas = { setPointerCapture() {}, getBoundingClientRect: () => ({left:0,top:0,width:800,height:600}), addEventListener:(k,v)=>events[k]=v };
const context = {canvas, host:{clientHeight:600}, distance:10, scale:1, viewZoom:1, pan:[0,0], available:true, interactionActive:false,
  window:{addEventListener:(type,callback)=>events[type]=callback},
  stopGlide(){}, markInteraction(){}, render(...a){renders.push(a)}, draw(){}, cacheLabelVisibility(){}, clearSelection(){},
  rotateByDrag:(...a)=>orbits.push(a), rollView:a=>rolls.push(a), zoomBy:(...a)=>zooms.push(a), pickIdAt:()=>7, select:id=>picks.push(id),
  $:()=>({click(){}}), project:()=>[400,300], anatomyCenter:[0,0,0]};
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
canvas.onpointerdown(event(10,10)); move(30,25,{shiftKey:true});
assert(Math.abs(context.pan[0]-2/3)<1e-8 && Math.abs(context.pan[1]+.5)<1e-8,'Shift drag should pan by its screen delta at the pivot');
canvas.onpointerup(event(30,25));
canvas.onpointerdown(event(10,10)); move(20,20,{buttons:2}); canvas.onpointerup(event(20,20,{button:2}));
canvas.onpointerdown(event(10,10,{pointerType:'touch'})); move(30,25,{pointerType:'touch'}); assert.equal(orbits.length,4,'Touch drag should orbit after the threshold');
canvas.onpointerdown(event(100,25,{pointerId:2,pointerType:'touch'})); move(120,60,{pointerId:2,pointerType:'touch'});
assert.equal(rolls.length,2,'Two-finger twist should roll');
assert(Math.abs(rolls[1])>.1,'Twisting should produce a nonzero roll');
assert(zooms.some(x=>x[1]===false),'Pinch zoom should avoid immediate picking refresh');
canvas.onpointerup(event(30,25,{pointerType:'touch'})); canvas.onpointerup(event(120,60,{pointerId:2,pointerType:'touch'})); assert.equal(picks.length,0,'Multi-touch must not select anatomy');
canvas.onpointerdown(event(10,10)); canvas.onpointerup(event(10,10)); assert.deepEqual(picks,[7],'Click selection should remain immediate');
canvas.onkeydown({key:'q',code:'KeyQ',preventDefault(){}});
assert.equal(rolls.length,3,'Q should roll');
canvas.onkeydown({key:'œ',code:'KeyQ',altKey:true,preventDefault(){}});
assert.equal(rolls.length,4,'Option+Q should also roll');
canvas.onpointerdown(event(10,10)); events.lostpointercapture(event(10,10));
move(20,20); assert.equal(orbits.length,4,'Lost capture must clear the gesture');
canvas.onpointerdown(event(10,10)); events.blur();
move(25,25); assert.equal(orbits.length,4,'Window blur must clear the gesture');
const prior=zooms.length; events.wheel({...event(0,0),deltaY:20,deltaMode:0}); canvas.onkeydown({...event(0,0),key:'+'});
assert.equal(zooms.length,prior+2,'Wheel and keyboard zoom should work');
assert(renders.some(x=>x[0]===false),'Camera movement should render without picking every frame');
// Exercise the actual shared controller with both real camera presets.
function section(first, last) {
    const a = runtime.indexOf(first), b = runtime.indexOf(last, a + first.length);
    assert(a >= 0 && b > a, `Could not find runtime section: ${first}`);
    return runtime.slice(a, b);
}
const math = vm.createContext({ sideSign: () => 1, render() {}, stopGlide() {}, host: {clientWidth:800, clientHeight:600}, canonicalPoint:p=>p });
const execute = code => vm.runInContext(code, math);
execute(`
    let viewQ = [0,0,0,1], camFrame = 'head', cameraExplicit = false;
    let distance = 15, viewZoom = 1.4, pan = [32,-21], poseR = [1,0,0,0,1,0,0,0,1];
    const anatomyCenter = Object.freeze([0, -.35, -.41]), scale = 2.05, aspect = 800/600;
    let viewCache = null;
    ${section('    function qMul(', '    const POSE_PIVOT')}
    ${section('    function viewChanged(', '    function markInteraction(')}
    ${section('    function transform(', '    const smoothstep01')}
    ${section('    function rollView(', '    function meshSide(')}
    ${section('    function setView(', '    // ---- Patient Position controls')}
    const front = () => mApply(mT(qMat(viewQ)), [0,0,2]);
    const dragDelta = (dx, dy) => {
        const before = viewQ;
        rotateByDrag(dx, dy);
        return qMul(viewQ, qConj(before));
    };
`);
const near = (a,b) => assert(Math.abs(a-b)<1e-8,`${a} should equal ${b}`);
execute('setSurgeonView()');
assert.equal(execute('viewZoom'),1,'Surgeon’s View restores its preset magnification');
for (const preset of ['setSurgeonView()', 'setView("right")', 'setView("superior")',
    'applyCamera({frame:"head", yaw:1, pitch:.25, zoom:1})', 'setView("anterior")',
    'setSurgeonView()', 'setView("left")', 'setView("posterior")']) {
    execute(`pan = [.8, -.45]; viewZoom = 2; ${preset}`);
    assert.deepEqual(Array.from(execute('pan')), [0,0], `${preset} must clear pan`);
    assert.equal(execute('viewBasis().target === anatomyCenter'),true);
    assert.deepEqual(Array.from(execute('project(anatomyCenter)')), [400,300]);
    execute('rotateByDrag(42, -30); rollView(.2)');
    assert.deepEqual(Array.from(execute('project(anatomyCenter)')), [400,300]);
}
for (const [dx,dy] of [[24,0],[0,21],[15,-22],[-20,12]]) {
    const [x,y,z] = execute(`dragDelta(${dx}, ${dy})`);
    assert(Math.hypot(x,y)>.04,'Ordinary drag must orbit');
    near(z,0);
}
const beforeRoll = Array.from(execute('qMat(viewQ).slice(6,9)'));
const [x,y,z] = execute('const beforeRollQ = viewQ; rollView(.25); qMul(viewQ, qConj(beforeRollQ))');
near(x,0); near(y,0); assert(Math.abs(z)>.1,'Explicit roll should turn about the sightline');
Array.from(execute('qMat(viewQ).slice(6,9)')).forEach((v,i)=>near(v,beforeRoll[i]));
for (const preset of ['setView("anterior")','setSurgeonView()']) {
    execute(preset);
    const coords = execute('{ const point = front(); rotateByDrag(10,-10); mApply(qMat(viewQ),point) }');
    assert(coords[0]>0 && coords[1]>0, 'The front landmark must follow a drag right and up');
    for (const [dx,dy] of [[1,0],[0,1]]) {
        execute(preset);
        const start = Array.from(execute('viewQ'));
        execute(`for (let i=0;i<160;i++) rotateByDrag(${dx},${dy},2*Math.PI/160)`);
        near(Math.abs(Array.from(execute('viewQ')).reduce((sum,v,i)=>sum+v*start[i],0)),1);
    }
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
