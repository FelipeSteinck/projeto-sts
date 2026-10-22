const $ = id => document.getElementById(id);
const video=$('video'), canvas=$('overlay'), ctx=canvas.getContext('2d');
const capture=document.createElement('canvas'), cc=capture.getContext('2d');
let sid=null,running=false,inFlight=false,stream=null,fileUrl=null,lastTime=-1,epoch=0,models=[];
const connections=[[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28],[27,31],[28,32]];
async function api(path,options={}) {
  const response=await fetch(path,options);
  if(!response.ok) {
    let message=`Erro ${response.status}`;
    try { const error=await response.json(); message=typeof error.detail==='string'?error.detail:JSON.stringify(error.detail); } catch {}
    throw Error(message);
  }
  return response.json();
}
function status(message){$('status').textContent=message;}
function chosen(){return models.find(m=>m.id===$('method').value);}
function configureMethod() {
  const model=chosen();
  if(model){$('alpha').value=model.alpha;$('stable').value=model.stable_frames;}
  $('alpha').disabled=running||Boolean(model);$('stable').disabled=running||Boolean(model);
  $('method-badge').textContent=model?`${model.name}${model.data_kind==='sintetico'?' · DEMO SINTÉTICA':''}`:'Regras geométricas';
  $('model-note').textContent=model?(model.data_kind==='sintetico'?'DEMONSTRAÇÃO SINTÉTICA: modelo treinado em coordenadas artificiais. Não é resultado experimental com pessoas.':'Modelo treinado com dados reais. Consulte a avaliação por sessão antes de interpretar seu desempenho.'):'Regras calibráveis. Modelos reais aparecem após treinamento com dados próprios.';
}
function enable(active) {
  ['source','method','mirror','file','session-id','participant-id'].forEach(id=>$(id).disabled=active);
  $('start').disabled=active;
  ['stop','sitting','standing'].forEach(id=>$(id).disabled=!active);
  configureMethod();
}
function activateLink(id,url){$(id).href=url;$(id).classList.remove('disabled');$(id).setAttribute('aria-disabled','false');}
function disableLink(id){$(id).removeAttribute('href');$(id).classList.add('disabled');$(id).setAttribute('aria-disabled','true');}
function draw(points) {
  canvas.width=capture.width;canvas.height=capture.height;ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle='#34d399';ctx.lineWidth=3;
  for(const[a,b] of connections) if(points[a]?.visibility>.35&&points[b]?.visibility>.35) {
    ctx.beginPath();ctx.moveTo(points[a].x*canvas.width,points[a].y*canvas.height);ctx.lineTo(points[b].x*canvas.width,points[b].y*canvas.height);ctx.stroke();
  }
}
function update(data,elapsed) {
  activateLink('csv',`/api/sessions/${sid}/csv`);
  if(data.calibrated) activateLink('config',`/api/sessions/${sid}/config`);
  for(const[id,key] of [['quality','quality'],['phase','phase'],['reps','repetitions'],['incomplete','incomplete'],['cancelled','cancelled'],['feedback','feedback']]) $(id).textContent=data[key];
  $('cal-status').textContent=data.calibrated?'Calibração concluída':'Calibração pendente';
  for(const[id,key] of [['knee','angulo_joelho'],['hip','angulo_quadril'],['trunk','inclinacao_tronco']]) $(id).textContent=data.metrics?`${data.metrics[key].toFixed(1)}°`:'—';
  $('comparison').textContent=`Regras em paralelo: ${data.rule_repetitions} repetição(ões)${data.model_score===null?'':` · Pontuação do modelo: ${data.model_score.toFixed(2)} (não é garantia de acerto)`}`;
  $('timing').textContent=`Resposta: ${elapsed.toFixed(0)} ms · Inferência e lógica: ${data.processing_ms.toFixed(0)} ms · Fonte: ${lastTime.toFixed(2)} s`;
  draw(data.landmarks);
}
async function stop() {
  running=false;video.pause();if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
  while(inFlight) await new Promise(resolve=>setTimeout(resolve,40));
  if(sid) try{await api(`/api/sessions/${sid}/stop`,{method:'POST'});}catch(error){status(error.message);enable(false);return;}
  enable(false);status('Sessão encerrada. Baixe o CSV e a calibração para guardar os registros.');
}
async function loop() {
  if(!running)return;
  if(video.readyState<2||video.paused){setTimeout(loop,60);return;}
  const time=$('source').value==='video'?video.currentTime:(performance.now()-epoch)/1000;
  if(time<=lastTime+.03){requestAnimationFrame(loop);return;}
  lastTime=time;capture.width=Math.min(video.videoWidth,640);capture.height=Math.round(capture.width*video.videoHeight/video.videoWidth);
  cc.save();if($('mirror').checked){cc.translate(capture.width,0);cc.scale(-1,1);}cc.drawImage(video,0,0,capture.width,capture.height);cc.restore();
  inFlight=true;
  try {
    const blob=await new Promise(resolve=>capture.toBlob(resolve,'image/jpeg',.8));
    if(!blob)throw Error('Não foi possível codificar o quadro.');
    const begin=performance.now();
    const data=await api(`/api/sessions/${sid}/frame?timestamp_ms=${Math.round(time*1000)}`,{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob});
    update(data,performance.now()-begin);
  } catch(error) { status(error.message);running=false; }
  finally {inFlight=false;}
  if(running)requestAnimationFrame(loop);
  else {enable(false);if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}}
}
$('method').addEventListener('change',configureMethod);
$('source').addEventListener('change',()=>{$('file-label').hidden=$('source').value!=='video';});
$('start').addEventListener('click',async()=>{
  running=true;enable(true);disableLink('csv');disableLink('config');status('Preparando a fonte…');
  try {
    const config={source:$('source').value,method:$('method').value,alpha:Number($('alpha').value),stable_frames:Number($('stable').value),mirrored:$('mirror').checked,session_id:$('session-id').value,participant_id:$('participant-id').value};
    if(!/^[A-Za-z0-9_-]{1,40}$/.test(config.session_id)||!/^[A-Za-z0-9_-]{1,40}$/.test(config.participant_id))throw Error('Use códigos de sessão e participante com letras, números, _ ou -.');
    const data=await api('/api/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)});sid=data.id;
    if(config.source==='camera'){
      if(!navigator.mediaDevices?.getUserMedia)throw Error('Abra a aplicação em HTTPS para acessar a câmera.');
      stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});video.srcObject=stream;video.controls=false;
    } else {
      const file=$('file').files[0];if(!file)throw Error('Selecione um vídeo primeiro.');
      if(fileUrl)URL.revokeObjectURL(fileUrl);fileUrl=URL.createObjectURL(file);video.srcObject=null;video.src=fileUrl;video.controls=true;
    }
    await video.play();lastTime=-1;epoch=performance.now();$('empty').hidden=true;
    video.style.transform=config.mirrored?'scaleX(-1)':'none';
    status('Sessão ativa. Registre sentado e em pé. Para avaliar vídeos, prefira a extração offline; a prévia pode ignorar quadros.');loop();
  } catch(error) {
    status(error.message);running=false;enable(false);
    if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
    if(sid){try{await api(`/api/sessions/${sid}/stop`,{method:'POST'});}catch{}sid=null;}
  }
});
$('stop').addEventListener('click',stop);
video.addEventListener('ended',()=>{if(running)stop();});
for(const[id,posture] of [['sitting','sitting'],['standing','standing']]) $(id).addEventListener('click',async()=>{
  try{
    const result=await api(`/api/sessions/${sid}/calibrate/${posture}`,{method:'POST'});
    if(result.calibrated)activateLink('config',`/api/sessions/${sid}/config`);
    status(result.calibrated?'Calibração concluída. Sente-se para iniciar a contagem.':'Postura registrada. Registre também a outra postura.');
  }catch(error){status(error.message);}
});
window.addEventListener('beforeunload',()=>{if(stream)stream.getTracks().forEach(t=>t.stop());});
Promise.all([api('/api/health'),api('/api/models')]).then(([health,catalog])=>{
  models=catalog.models;
  for(const model of models){const option=document.createElement('option');option.value=model.id;option.textContent=`${model.name} · ${model.data_kind==='sintetico'?'DEMO SINTÉTICA':'dados reais'}`;$('method').append(option);}
  configureMethod();status(health.model_ready?'Ambiente pronto. Escolha o método e a fonte.':'Modelo de pose ausente: execute python scripts/download_model.py.');
}).catch(error=>status(error.message));
