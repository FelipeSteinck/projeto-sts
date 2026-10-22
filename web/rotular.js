const get=id=>document.getElementById(id);
const player=get('label-video');let intervals=[],videoUrl=null,labelUrl=null;
const message=text=>get('annotation-status').textContent=text;
function render(){
  get('intervals').replaceChildren();
  for(const row of [...intervals].sort((a,b)=>a.start-b.start)){
    const item=document.createElement('li');item.textContent=`${row.start.toFixed(3)} a ${row.end.toFixed(3)} s · ${row.label} · ${row.usage}`;get('intervals').append(item);
  }
}
get('label-file').addEventListener('change',()=>{
  if(intervals.length){message('Baixe os rótulos antes de trocar de vídeo. Abra outra aba para um novo arquivo.');return;}
  const file=get('label-file').files[0];if(!file)return;
  if(videoUrl)URL.revokeObjectURL(videoUrl);videoUrl=URL.createObjectURL(file);player.src=videoUrl;
});
player.addEventListener('timeupdate',()=>{get('label-time').textContent=`Tempo: ${player.currentTime.toFixed(3)} s`;});
get('mark-start').addEventListener('click',()=>{get('interval-start').value=player.currentTime.toFixed(3);});
get('mark-end').addEventListener('click',()=>{get('interval-end').value=player.currentTime.toFixed(3);});
get('add-interval').addEventListener('click',()=>{
  const row={start:Number(get('interval-start').value),end:Number(get('interval-end').value),label:get('label-class').value,usage:get('label-usage').value};
  if(!Number.isFinite(row.start+row.end)||row.start<0||row.end<=row.start){message('Use 0 ≤ início < fim.');return;}
  if(Number.isFinite(player.duration)&&row.end>player.duration+.05){message('O intervalo ultrapassa a duração do vídeo.');return;}
  if(intervals.some(a=>row.start<a.end&&a.start<row.end)){message('Esse intervalo se sobrepõe a outro.');return;}
  const combined=[...intervals,row];const evaluation=combined.filter(a=>a.usage==='avaliacao');const calibration=combined.filter(a=>a.usage==='calibracao');
  if(evaluation.length&&calibration.length&&Math.max(...calibration.map(a=>a.end))>Math.min(...evaluation.map(a=>a.start))){message('Os trechos de calibração devem vir antes da avaliação.');return;}
  intervals.push(row);render();get('interval-start').value=row.end;message(`${intervals.length} intervalo(s). Continue a anotação e baixe o CSV.`);
});
get('undo-interval').addEventListener('click',()=>{intervals.pop();render();message('Último intervalo removido.');});
get('export-labels').addEventListener('click',()=>{
  if(!intervals.length){message('Adicione pelo menos um intervalo.');return;}
  const lines=['inicio_s;fim_s;rotulo;uso',...[...intervals].sort((a,b)=>a.start-b.start).map(a=>`${a.start};${a.end};${a.label};${a.usage}`)];
  if(labelUrl)URL.revokeObjectURL(labelUrl);labelUrl=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const link=document.createElement('a');link.href=labelUrl;link.download='rotulos_sts.csv';link.click();message('CSV exportado. Guarde com o vídeo e seu identificador de sessão.');
});
