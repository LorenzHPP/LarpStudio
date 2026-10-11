'use strict';
const $ = id => document.getElementById(id);
const DEFAULT = [52.516275, 13.377704];
const modes = {pin:{speed:4.8,min:1,max:12,label:'Fixed point'},walk:{speed:4.8,min:1,max:12,label:'Walking'},run:{speed:9,min:3,max:25,label:'Running'},drive:{speed:40,min:5,max:160,label:'Driving'}};
const activePhases = ['preparing','running','paused','holding','stopping'];
let mode='pin', speed=4.8, selected=DEFAULT.slice(), selectedName='Brandenburg Gate', selectedDetail='Pariser Platz · Berlin';
let waypoints=[], planned=[], routeDistance=0, routeGeneration=0, planning=false, searching=false;
let autoDrive=true, drivingProfile=null, drivingNote='', previewDriving=null, previewDriveElapsed=0;
let state={phase:'disconnected',message:'Connect your iPhone by USB.',device:null,position:null,logs:[],favorites:[{name:'Brandenburg Gate',detail:selectedDetail,point:DEFAULT}],sent_count:0};
let preview=true, previewTimer=null, previewTravel=0, previewStarted=0, previewPaused=false, previewPlan=null, previewLengths=[];
let favoriteKey='', lastError='', toastTimer, searchGeneration=0, tilesFailed=0;
const fmt=new Intl.NumberFormat('en-GB',{maximumFractionDigits:1});
const number=n=>fmt.format(Number(n)||0);
const meters=n=>n>=1000?number(n/1000)+' km':Math.round(n)+' m';
const duration=n=>{const seconds=Math.max(0,Math.round((Number(n)||0)*60));if(seconds<60)return seconds+' s';const minutes=Math.ceil(seconds/60);return minutes<60?minutes+' min':Math.floor(minutes/60)+' h '+minutes%60+' min'};
const clock=n=>{n=Math.floor(n||0);return Math.floor(n/60).toString().padStart(2,'0')+':'+(n%60).toString().padStart(2,'0')};
const coords=p=>Math.abs(p[0]).toFixed(6)+'° '+(p[0]<0?'S':'N')+' · '+Math.abs(p[1]).toFixed(6)+'° '+(p[1]<0?'W':'E');
const svg=id=>'<svg><use href="#i-'+id+'"/></svg>';
const active=()=>activePhases.includes(state.phase);
function mapInset(){return document.querySelector('.sidebar').getBoundingClientRect().right+24;}
function routeBounds(){return {paddingTopLeft:[mapInset(),130],paddingBottomRight:[88,155]};}
function focusPoint(point,zoom=15){
  const center=map.unproject(map.project(point,zoom).subtract([mapInset()/2,0]),zoom);
  map.flyTo(center,zoom,{duration:.7});
}
const map=L.map('map',{zoomControl:false,attributionControl:true,preferCanvas:false,worldCopyJump:true}).setView(DEFAULT,15);
map.panBy([-mapInset()/2,0],{animate:false});
map.attributionControl.setPrefix('');
L.control.scale({imperial:false,position:'bottomleft',maxWidth:90}).addTo(map);
let tileLayer;
function useTiles(url){
  if(tileLayer?._url===url)return;
  if(tileLayer)map.removeLayer(tileLayer);
  tileLayer=L.tileLayer(url,{maxZoom:19,minZoom:2,keepBuffer:1,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'}).addTo(map);
  tileLayer.on('tileerror',()=>{if(++tilesFailed>=3){$('mapStatus').textContent='Map tiles could not load. Check your internet connection; coordinates are still available.';$('mapStatus').hidden=false;}});
  tileLayer.on('load',()=>{if(tilesFailed===0)$('mapStatus').hidden=true;});
}
useTiles('https://tile.openstreetmap.org/{z}/{x}/{y}.png');
const layer=L.layerGroup().addTo(map);
let pinMarker, movingMarker, routeLine;
function toast(message,error=false){$('toast').textContent=message;$('toast').classList.toggle('error',error);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,error?6500:3500);}
function log(message,kind='info'){state.logs.push({time:new Date().toLocaleTimeString('en-GB'),message,kind});state.logs=state.logs.slice(-50);}
function sphericalDistance(a,b){const r=Math.PI/180;const h=Math.sin((b[0]-a[0])*r/2)**2+Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin((b[1]-a[1])*r/2)**2;return 6371008.8*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)));}
function interpolate(points,lengths,d){if(!lengths.length||d<=0)return points[0];if(d>=lengths.at(-1))return points.at(-1);let i=1;while(lengths[i]<d)i++;const f=(d-lengths[i-1])/(lengths[i]-lengths[i-1]);return points[i-1].map((n,j)=>n+(points[i][j]-n)*f);}
function makeDrivingProfile(samples){
  if(!Array.isArray(samples)||samples.length<3)return null;
  const times=[0];for(let i=1;i<samples.length;i++){const dt=2*(samples[i][0]-samples[i-1][0])/(samples[i][1]+samples[i-1][1]);if(!Number.isFinite(dt)||dt<=0)return null;times.push(times.at(-1)+dt);}
  const total=samples.at(-1)[0],seconds=times.at(-1);
  const at=t=>{if(t<=0)return [0,0];if(t>=seconds)return [total,0];let low=0,high=times.length-1;while(low+1<high){const middle=(low+high)>>1;if(times[middle]<=t)low=middle;else high=middle;}const dt=times[low+1]-times[low],x=t-times[low],v=samples[low][1],a=(samples[low+1][1]-v)/dt;return [samples[low][0]+v*x+.5*a*x*x,v+a*x];};
  return {samples,duration:seconds,travel(t,loop){if(!loop){const [d,v]=at(t);return [d,d,v,Math.max(0,seconds-t)];}const cycles=Math.floor(t/(2*seconds)),cycle=t%(2*seconds),forward=cycle<=seconds;const [d,v]=at(forward?cycle:2*seconds-cycle);return [d,cycles*2*total+(forward?d:2*total-d),v,forward?seconds-cycle:2*seconds-cycle];}};
}
function previewStart(plan){
  previewPlan=plan;previewTravel=0;previewPaused=false;previewStarted=Date.now();previewLengths=[0];
  for(let i=1;i<plan.points.length;i++)previewLengths.push(previewLengths.at(-1)+sphericalDistance(plan.points[i-1],plan.points[i]));
  previewDriving=plan.speed_mode==='auto'?makeDrivingProfile(plan.driving_profile):null;previewDriveElapsed=0;
  state.phase=plan.mode==='pin'?'holding':'running';state.mode=plan.mode;state.position=plan.points[0];state.distance=previewLengths.at(-1);state.message='Map preview active · your iPhone location is unchanged.';state.sent_count=0;state.speed_mode=plan.speed_mode;state.current_speed=0;state.remaining=previewDriving?.duration||state.distance/(speed/3.6);
  log('Map preview started. No iPhone connected.');
  clearInterval(previewTimer);
  let last=Date.now();
  previewTimer=setInterval(()=>{
    const now=Date.now(),delta=Math.min(3,(now-last)/1000);last=now;const total=previewLengths.at(-1);let d,v,remaining;
    if(previewDriving){if(!previewPaused)previewDriveElapsed+=delta;[d,previewTravel,v,remaining]=previewDriving.travel(previewDriveElapsed,plan.loop);}
    else{if(!previewPaused&&previewPlan.mode!=='pin')previewTravel+=speed/3.6*delta;d=Math.min(previewTravel,total);remaining=(total-d)/(speed/3.6);if(plan.loop&&total){const cycle=previewTravel%(2*total);d=cycle<=total?cycle:2*total-cycle;remaining=(cycle<=total?total-cycle:2*total-cycle)/(speed/3.6);}v=plan.mode!=='pin'&&(plan.loop||d<total)?speed/3.6:0;}
    const arrived=!plan.loop&&(previewDriving?previewDriveElapsed>=previewDriving.duration:d>=total);if(arrived)d=total;
    state.current_speed=previewPaused?0:v*3.6;state.remaining=remaining;state.position=interpolate(plan.points,previewLengths,d);state.progress=total?d/total:0;state.traveled=previewTravel;state.elapsed=(now-previewStarted)/1000;state.last_sent=now/1000;state.sent_count++;state.phase=previewPaused?'paused':plan.mode==='pin'||arrived?'holding':'running';renderState();
  },400);
}
async function call(method,...args){
  let reply;
  if(window.pywebview?.api){reply=await window.pywebview.api[method](...args);}
  else if(['search_places','plan_route','get_settings'].includes(method)){
    const response=await fetch('/api/'+method,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(args)});reply=await response.json();
  }else{
    if(method==='get_state')reply={ok:true,data:state};
    else if(method==='set_connection'){state.connection=args[0];state.phase='disconnected';state.message=args[0]==='wifi'?'Wi-Fi is only available in the Windows app.':'Map preview · your iPhone location is unchanged';reply={ok:true};}
    else if(method==='prepare_wifi')reply={ok:false,error:'Wi-Fi setup requires the Windows app and your connected iPhone.'};
    else if(method==='connect_device')reply={ok:false,error:'This is a map preview. Open the Windows app to control your iPhone.'};
    else if(method==='start_session'){previewStart(args[0]);reply={ok:true};}
    else if(method==='pause_session'){previewPaused=!previewPaused;state.phase=previewPaused?'paused':'running';log(previewPaused?'Map preview paused.':'Map preview resumed.');reply={ok:true};}
    else if(method==='stop_session'||method==='recover_device'){clearInterval(previewTimer);previewTimer=null;state.phase='disconnected';state.position=null;state.message='Map preview stopped · your iPhone location is unchanged.';log(state.message);reply={ok:true};}
    else if(method==='set_speed'){speed=Number(args[0]);reply={ok:true};}
    else if(method==='save_favorite'){state.favorites=[{name:args[0],point:args[1],detail:args[2]},...state.favorites.filter(x=>x.name!==args[0])].slice(0,20);localStorage.setItem('atlas-favorites',JSON.stringify(state.favorites));reply={ok:true};}
    else reply={ok:false,error:'This feature is available in the desktop app.'};
  }
  if(!reply?.ok)throw new Error(reply?.error||'The app did not return a valid response.');
  return reply.data;
}
async function action(method,...args){try{const result=await call(method,...args);await poll();return result;}catch(error){toast(error.message,true);}}
function markerIcon(number=null){return L.divIcon({className:'',html:number===null?'<div class="map-pin-label">Destination</div><div class="map-pin"><img src="assets/map-pin.svg" alt=""></div>':'<div class="route-waypoint">'+number+'</div>',iconSize:number===null?[32,40]:[27,27],iconAnchor:number===null?[16,39]:[13.5,13.5]});}
function drawMap(){
  layer.clearLayers();pinMarker=null;routeLine=null;
  if(mode==='pin'){
    pinMarker=L.marker(selected,{icon:markerIcon(),draggable:!active()}).addTo(layer);
    pinMarker.on('dragend',event=>{const p=event.target.getLatLng();setPoint([p.lat,p.lng]);});
  }else{
    if(waypoints.length>1)routeLine=L.polyline(planned.length?planned:waypoints.map(x=>x.point),{color:document.querySelector('.map-workspace').classList.contains('light-map')?'#141414':'#f5f5f5',weight:planned.length?4:2,opacity:1,dashArray:planned.length?null:'6 7',className:'atlas-route'}).addTo(layer);
    waypoints.forEach((item,i)=>{
      const marker=L.marker(item.point,{icon:markerIcon(i+1),draggable:!active(),title:'Route point '+(i+1)}).addTo(layer);
      marker.on('dragend',event=>{if(active()){drawMap();return;}const p=event.target.getLatLng();waypoints[i]={point:[p.lat,p.lng],title:'Point '+(i+1)};invalidateRoute();renderEditor();drawMap();});
      const remove=document.createElement('button');remove.type='button';remove.className='remove-waypoint waypoint-popup-delete';remove.textContent='Remove point '+(i+1);remove.disabled=active();
      remove.onclick=event=>{event.stopPropagation();removeWaypoint(i);};
      marker.bindPopup(remove,{className:'waypoint-popup'});
      marker.on('popupopen',()=>{remove.disabled=active();});
    });
  }
  if(movingMarker)map.removeLayer(movingMarker);movingMarker=null;
  if(active()&&state.position)updateMoving();
}
function updateMoving(){if(!state.position)return;if(!movingMarker)movingMarker=L.marker(state.position,{icon:L.divIcon({className:'',html:'<div class="moving-avatar"><img src="assets/mode-'+mode+'.svg" alt=""></div>',iconSize:[36,36],iconAnchor:[18,18]}),zIndexOffset:1000}).addTo(map);else movingMarker.setLatLng(state.position);}
function setPoint(point,title='Selected point',detail='Selected on the map'){
  if(active()){toast('Stop your current session before changing the location.');return false;}
  const [lat,lon]=point.map(Number);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180){toast('Enter valid coordinates.',true);return false;}
  if(mode!=='pin'&&waypoints.length>=12){toast('Use up to twelve points per route.',true);return false;}
  selected=[lat,lon];selectedName=title;selectedDetail=detail;
  if(mode!=='pin'){waypoints.push({point:selected.slice(),title});invalidateRoute();}
  renderEditor();drawMap();
  return true;
}
function invalidateRoute(){planned=[];routeDistance=0;drivingProfile=null;drivingNote='';routeGeneration++;$('routeNote').textContent=waypoints.length>=2?'Points changed. Plan your route again.':'Add at least two points to the map.';renderSpeed();renderSummary();}
function removeWaypoint(index){
  if(active()){toast('Stop your current session before removing route points.');return;}
  if(!Number.isInteger(index)||index<0||index>=waypoints.length)return;
  waypoints.splice(index,1);invalidateRoute();renderEditor();drawMap();
}
function switchMode(next){
  if(active()){toast('Stop the session before switching modes.');return;}
  const previous=mode;mode=next;speed=modes[mode].speed;
  if(mode!=='pin'&&!waypoints.length)waypoints=[{point:selected.slice(),title:selectedName}];
  if(mode!=='pin'&&previous!==mode&&!(previous==='walk'&&mode==='run'||previous==='run'&&mode==='walk'))invalidateRoute();
  $('speedRange').min=modes[mode].min;$('speedRange').max=modes[mode].max;$('speedRange').value=speed;
  $('speedMin').textContent=modes[mode].min+' km/h';$('speedMax').textContent=modes[mode].max+' km/h';
  renderEditor();renderSpeed();drawMap();renderState();
}
function renderSpeed(){
  const automatic=mode==='drive'&&autoDrive,live=automatic&&active();
  $('driveSpeedOptions').hidden=mode!=='drive';$('manualSpeedControls').hidden=automatic;$('driveSpeedNote').hidden=mode!=='drive';
  $('autoDriveButton').setAttribute('aria-pressed',String(autoDrive));$('fixedDriveButton').setAttribute('aria-pressed',String(!autoDrive));
  $('speedUnit').textContent=automatic&&!live?'avg km/h':'km/h';
  $('speedNumber').textContent=live?number(state.phase==='paused'?0:state.current_speed):automatic?(drivingProfile?number(routeDistance/drivingProfile.duration*3.6):'—'):number(speed);
  $('speedDescription').textContent=automatic?(live?'Current':'Average'):mode==='drive'?'Constant':mode==='run'?'Running pace':'Walking pace';
  $('driveSpeedNote').textContent=automatic?(drivingNote&&!drivingProfile?drivingNote:'Speed follows each road section, with corner handling and smooth transitions. No live traffic data.'):'The same speed throughout the route. Roads and corners do not affect it.';
  renderSummary();
}
function renderEditor(){
  document.querySelectorAll('.mode').forEach(button=>{const yes=button.dataset.mode===mode;button.classList.toggle('active',yes);button.setAttribute('aria-pressed',String(yes));});
  $('targetCard').hidden=mode!=='pin';$('routeEditor').hidden=mode==='pin';$('speedSection').hidden=mode==='pin';$('destinationTitle').textContent=mode==='pin'?'Destination':'Route';
  $('pointName').textContent=selectedName;$('pointDetail').textContent=selectedDetail;$('pointCoordinates').textContent=coords(selected);
  $('mapInstruction').innerHTML=svg(mode==='pin'?'pin':'route')+(mode==='pin'?'Click the map to place your pin.':'Click the map to add route points.');
  const container=$('waypoints');container.replaceChildren();
  waypoints.forEach((item,i)=>{
    const row=document.createElement('div');row.className='waypoint';
    const badge=document.createElement('span');badge.className='waypoint-number';badge.textContent=i+1;
    const text=document.createElement('span');text.className='waypoint-copy';text.textContent=item.title;
    const small=document.createElement('small');small.textContent=item.point.map(n=>n.toFixed(5)).join(', ');text.append(small);
    const remove=document.createElement('button');remove.type='button';remove.className='remove-waypoint waypoint-delete';remove.innerHTML=svg('close');
    remove.title='Remove point '+(i+1);remove.setAttribute('aria-label',remove.title);remove.disabled=active();remove.onclick=()=>removeWaypoint(i);
    row.append(badge,text,remove);container.append(row);
  });
  if(mode!=='pin'&&!waypoints.length){const note=document.createElement('p');note.className='field-note';note.textContent='Place your starting point on the map.';container.append(note);}
  renderSummary();renderState();
}
function renderSummary(){
  $('routeSummary').hidden=mode==='pin'||!planned.length||active();
  $('routeDistance').textContent=meters(routeDistance);$('routeDuration').textContent=mode==='drive'&&autoDrive?(drivingProfile?'~ '+duration(drivingProfile.duration/60):'—'):'~ '+duration(routeDistance/(speed/3.6)/60);
  $('buildRoute').disabled=planning||active()||waypoints.length<2;
  $('buildRoute').innerHTML=svg('route')+(planning?'Planning route …':'Plan route');
}
function renderFavorites(){
  const key=JSON.stringify(state.favorites||[]);if(key===favoriteKey)return;favoriteKey=key;
  $('favorites').replaceChildren();
  for(const item of state.favorites||[]){const button=document.createElement('button');button.className='favorite';button.innerHTML=svg('pin');const name=document.createElement('span');name.className='favorite-name';name.textContent=item.name;const detail=document.createElement('small');detail.className='favorite-detail';detail.textContent=item.detail||'Saved place';name.append(detail);const arrow=document.createElement('span');arrow.textContent='↗︎';button.append(name,arrow);button.onclick=()=>{setPoint(item.point,item.name,item.detail);if(!active())focusPoint(item.point);};$('favorites').append(button);}
}
function renderLogs(){
  $('activityLog').replaceChildren();
  if(!(state.logs||[]).length){const note=document.createElement('p');note.className='dialog-note';note.textContent='Your session events will appear here.';$('activityLog').append(note);}
  for(const item of [...(state.logs||[])].reverse()){const row=document.createElement('div');row.className='log-entry '+(item.kind==='error'?'error':'');const time=document.createElement('time');time.textContent=item.time;const text=document.createElement('span');text.textContent=item.message;row.append(time,text);$('activityLog').append(row);}
}
function renderState(){
  preview=!window.pywebview?.api;
  $('previewBadge').hidden=!preview;
  const connected=Boolean(state.device)&&!['error','disconnected','connecting'].includes(state.phase);
  const wifi=state.connection==='wifi';
  for(const id of ['usbConnection','wifiConnection','wifiSetupButton','prepareWifiButton'])$(id).disabled=isDeviceBusy();
  $('usbConnection').setAttribute('aria-pressed',String(!wifi));$('wifiConnection').setAttribute('aria-pressed',String(wifi));
  $('connectionIndicator').classList.toggle('connected',connected&&!preview);
  $('connectionIndicator').lastChild.textContent=preview?'iPhone disconnected':connected?'iPhone connected · '+(wifi?'Wi-Fi':'USB'):state.phase==='connecting'?'Checking connection …':'iPhone disconnected';
  $('deviceName').textContent=state.device?.name||'Your iPhone';
  const models={'iPhone16,2':'iPhone 15 Pro Max','iPhone16,1':'iPhone 15 Pro'};
  $('deviceDetail').textContent=state.device?(models[state.device.model]||state.device.model||'iPhone')+' · iOS '+state.device.ios:wifi?'Same Wi-Fi network · unlock iPhone':'Connect USB & unlock';
  $('connectButton').disabled=active()||state.busy||state.phase==='connecting';
  $('connectButton').textContent=state.phase==='connecting'?'Checking …':connected?'Check':'Connect';
  const isActive=active();
  $('startButton').hidden=isActive;$('sessionControls').hidden=!isActive;
  $('startButton').disabled=planning||(!preview&&!connected)||(mode!=='pin'&&planned.length<2)||(mode==='drive'&&autoDrive&&!drivingProfile)||state.busy||state.needs_clear;
  $('startButton').querySelector('span').textContent=preview?'Start preview':mode==='pin'?'Set location':'Start route';
  $('pauseButton').disabled=!['running','paused','holding'].includes(state.phase);
  $('pauseButton').querySelector('span').textContent=state.phase==='paused'?'Resume':'Pause';
  $('pauseButton').querySelector('use').setAttribute('href',state.phase==='paused'?'#i-play':'#i-pause');
  $('stopButton').disabled=state.phase==='stopping';
  $('resetButton').disabled=isActive||state.busy||(!preview&&!state.device);
  $('sessionHint').classList.toggle('error',state.phase==='error');
  $('sessionHint').querySelector('span:last-child').textContent=state.phase==='disconnected'&&preview?'Map preview · your iPhone location is unchanged':state.message.slice(0,210);
  document.querySelectorAll('.mode').forEach(button=>button.disabled=isActive);
  $('undoPoint').disabled=isActive||!waypoints.length;$('clearRoute').disabled=isActive||!waypoints.length;
  document.querySelectorAll('.remove-waypoint').forEach(button=>button.disabled=isActive);
  $('loopRoute').disabled=isActive;$('coordinateButton').disabled=isActive;
  $('autoDriveButton').disabled=isActive;$('fixedDriveButton').disabled=isActive;$('speedRange').disabled=mode==='drive'&&autoDrive;
  $('mapInstruction').hidden=isActive;
  $('liveCard').hidden=!isActive;
  if(isActive){
    const artwork='assets/mode-'+mode+'.svg';if($('liveArtwork').getAttribute('src')!==artwork)$('liveArtwork').src=artwork;
    $('liveTitle').textContent=state.phase==='preparing'?'Preparing connection …':state.phase==='stopping'?'Stopping simulation …':state.phase==='paused'?'Paused · holding position':state.phase==='holding'?'Holding destination':modes[mode].label+' · travelled';
    if(preview)$('liveTitle').textContent='Preview · '+$('liveTitle').textContent;
    $('liveElapsed').textContent=clock(state.elapsed);
    $('liveDriveMetrics').hidden=mode!=='drive';$('liveSpeed').textContent=number(state.phase==='paused'?0:state.current_speed)+' km/h';$('liveRemaining').textContent=(state.phase==='paused'?'Paused · ':'~ ')+duration((state.remaining||0)/60)+' remaining';
    $('liveCoordinates').textContent=state.position?coords(state.position):'Waiting for the first location command …';
    $('liveProgress').style.width=(Math.max(0,Math.min(1,state.progress||0))*100)+'%';
    $('liveDistance').textContent=mode==='pin'?'Fixed point':meters(state.traveled||0)+' travelled';
    const age=state.last_sent?Math.max(0,Date.now()/1000-state.last_sent):null;
    $('liveSent').textContent=age===null?'No point sent yet':preview?'Map preview only':age>4?'Last command '+Math.floor(age)+' s ago':'Command '+Math.floor(age)+' s ago';
    updateMoving();
  }else if(movingMarker){map.removeLayer(movingMarker);movingMarker=null;}
  if(state.phase==='error'&&state.message!==lastError){lastError=state.message;toast(state.message,true);}
  if(state.phase!=='error')lastError='';
  renderSpeed();renderFavorites();
  if($('activityDialog').open)renderLogs();
}
let polling=false;
function isDeviceBusy(){return active()||state.busy||state.phase==='connecting';}
async function poll(){if(polling)return;polling=true;try{if(window.pywebview?.api)state=await call('get_state');renderState();}catch(error){toast('Connection to the app lost: '+error.message,true);}finally{polling=false;}}
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>switchMode(button.dataset.mode)));
map.on('click',event=>{setPoint([event.latlng.lat,((event.latlng.lng+180)%360+360)%360-180]);});
map.on('mousemove',event=>$('mouseCoordinates').textContent=event.latlng.lat.toFixed(6)+', '+event.latlng.lng.toFixed(6));
$('zoomIn').onclick=()=>map.zoomIn();$('zoomOut').onclick=()=>map.zoomOut();$('worldMap').onclick=()=>map.setView([25,12],2);
function setMapStyle(value){const light=value==='light';document.querySelector('.map-workspace').classList.toggle('light-map',light);if(routeLine)routeLine.setStyle({color:light?'#141414':'#f5f5f5'});$('mapStyleDark').setAttribute('aria-pressed',String(!light));$('mapStyleLight').setAttribute('aria-pressed',String(light));try{localStorage.setItem('atlas-map-style',light?'light':'dark');}catch{}}
$('mapStyleDark').onclick=()=>setMapStyle('dark');$('mapStyleLight').onclick=()=>setMapStyle('light');
try{setMapStyle(localStorage.getItem('atlas-map-style')||'dark');}catch{setMapStyle('dark');}
$('centerMap').onclick=()=>{if(state.position&&active())focusPoint(state.position);else if(planned.length)map.fitBounds(L.latLngBounds(planned),routeBounds());else focusPoint(selected);};
$('connectButton').onclick=()=>action('connect_device');
$('usbConnection').onclick=()=>action('set_connection','usb');$('wifiConnection').onclick=()=>action('set_connection','wifi');
$('wifiSetupButton').onclick=()=>$('wifiDialog').showModal();$('prepareWifiButton').onclick=()=>{action('prepare_wifi');$('wifiDialog').close();};
$('startButton').onclick=()=>{const points=mode==='pin'?[selected.slice()]:planned;if(!points.length){toast('Plan your route first.',true);return;}if(mode==='drive'&&autoDrive&&!drivingProfile){toast('Plan the driving route again to use road-aware speed.',true);return;}action('start_session',{mode,points,speed,loop:$('loopRoute').checked,speed_mode:mode==='drive'&&autoDrive?'auto':'fixed',driving_profile:mode==='drive'&&autoDrive?drivingProfile.samples:null});};
$('pauseButton').onclick=()=>action('pause_session');$('stopButton').onclick=()=>action('stop_session');$('resetButton').onclick=()=>action('recover_device');
$('speedRange').oninput=event=>{speed=Number(event.target.value);renderSpeed();};$('speedRange').onchange=()=>action('set_speed',speed);
$('autoDriveButton').onclick=()=>{if(active())return;autoDrive=true;renderSpeed();renderState();};$('fixedDriveButton').onclick=()=>{if(active())return;autoDrive=false;renderSpeed();renderState();};
$('undoPoint').onclick=()=>removeWaypoint(waypoints.length-1);$('clearRoute').onclick=()=>{if(active())return;waypoints=[];invalidateRoute();renderEditor();drawMap();};
$('buildRoute').onclick=async()=>{const generation=routeGeneration;planning=true;renderState();try{const result=await call('plan_route',waypoints.map(x=>x.point),mode);if(generation!==routeGeneration||active())return;planned=result.points;routeDistance=result.distance;drivingProfile=mode==='drive'?makeDrivingProfile(result.driving_profile):null;drivingNote=result.driving_note||'The routing service did not provide a driving profile. Plan again or choose fixed speed.';$('routeNote').textContent='Planned route · '+result.source;drawMap();map.fitBounds(L.latLngBounds(planned),routeBounds());toast(mode==='drive'&&autoDrive&&!drivingProfile?'Route planned. Road-aware speed is unavailable for this route.':'Your route is ready.',mode==='drive'&&autoDrive&&!drivingProfile);}catch(error){toast(error.message,true);}finally{planning=false;renderSpeed();renderState();}};
$('searchForm').onsubmit=async event=>{
  event.preventDefault();const query=$('searchInput').value.trim();if(!query)return;
  const pair=query.includes(';')?query.split(';').map(x=>Number(x.trim().replace(',','.'))):query.split(/[,\s]+/).map(Number);
  if(pair.length===2&&pair.every(Number.isFinite)){if(setPoint(pair,'Coordinates','Entered manually'))focusPoint(pair);$('searchResults').hidden=true;return;}
  const generation=++searchGeneration;searching=true;$('searchResults').replaceChildren();const note=document.createElement('div');note.className='search-empty';note.textContent='Searching places …';$('searchResults').append(note);$('searchResults').hidden=false;
  try{const results=await call('search_places',query);if(generation!==searchGeneration)return;$('searchResults').replaceChildren();if(!results.length){note.textContent='No place found. Try a city name or coordinates.';$('searchResults').append(note);}for(const item of results){const button=document.createElement('button');button.type='button';button.className='search-result';button.textContent=item.title;const small=document.createElement('small');small.textContent=item.detail;button.append(small);button.onclick=()=>{setPoint(item.point,item.title,item.detail);if(!active())focusPoint(item.point);$('searchResults').hidden=true;};$('searchResults').append(button);}}
  catch(error){toast(error.message,true);$('searchResults').hidden=true;}finally{searching=false;}
};
document.addEventListener('click',event=>{if(!$('searchForm').contains(event.target))$('searchResults').hidden=true;});
$('activityButton').onclick=()=>{renderLogs();$('activityDialog').showModal();};$('helpButton').onclick=()=>$('helpDialog').showModal();
document.querySelectorAll('.close-dialog').forEach(button=>button.onclick=()=>button.closest('dialog').close());
document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close();}}));
$('coordinateButton').onclick=()=>{$('latitudeInput').value=selected[0];$('longitudeInput').value=selected[1];$('coordinateDialog').showModal();};
$('coordinateForm').onsubmit=event=>{event.preventDefault();const point=[$('latitudeInput').value,$('longitudeInput').value].map(n=>Number(n.replace(',','.')));if(point.some(n=>!Number.isFinite(n))||Math.abs(point[0])>90||Math.abs(point[1])>180){toast('Enter valid coordinates.',true);return;}setPoint(point,'Coordinates','Entered manually');focusPoint(point);$('coordinateDialog').close();};
$('saveFavorite').onclick=()=>{$('favoriteName').value=selectedName;$('favoriteDialog').showModal();};
$('favoriteForm').onsubmit=async event=>{event.preventDefault();try{await call('save_favorite',$('favoriteName').value.trim(),selected,selectedDetail);favoriteKey='';await poll();renderFavorites();$('favoriteDialog').close();toast('Place saved on your PC.');}catch(error){toast(error.message,true);}};
document.addEventListener('keydown',event=>{if($('locationWorkspace').hidden||['INPUT','TEXTAREA','BUTTON'].includes(event.target.tagName)||document.querySelector('dialog[open]'))return;if(event.key===' '&&active()){event.preventDefault();$('pauseButton').click();}if(event.key==='Enter'&&!active()){event.preventDefault();$('startButton').click();}if(event.key==='Escape')$('searchResults').hidden=true;});
window.addEventListener('pywebviewready',async()=>{clearInterval(previewTimer);preview=false;state.phase='disconnected';state.position=null;const settings=await action('get_settings');if(settings?.tiles)useTiles(settings.tiles);await poll();});
try{const saved=JSON.parse(localStorage.getItem('atlas-favorites'));if(Array.isArray(saved))state.favorites=saved.filter(x=>typeof x.name==='string'&&Array.isArray(x.point)&&x.point.length===2&&x.point.every(Number.isFinite)).slice(0,20);}catch{}
renderEditor();renderSpeed();drawMap();renderState();setInterval(poll,600);
