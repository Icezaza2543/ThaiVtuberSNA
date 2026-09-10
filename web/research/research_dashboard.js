(function () {
  'use strict';
  let data;
  const palette = ['#62e7ff', '#a78bfa', '#ff7ac8', '#6ef0c2', '#ffd16a', '#e6e8f2'];
  const el = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = value => Number.isFinite(value) ? value.toLocaleString('th-TH', {maximumFractionDigits: 2}) : 'ไม่มีข้อมูล';
  const pct = value => Number.isFinite(value) ? num(value * 100) + '%' : 'ไม่มีข้อมูล';
  const group = value => value ? 'สายกลุ่ม ' + value.replace('LINEAGE_', '') : 'ไม่ระบุ';
  const agency = value => value === 'Independent' ? 'อิสระ' : value === 'Unknown' || !value ? 'ไม่ระบุ' : value;
  const tier = value => ({HIGH:'สูง',MODERATE:'ปานกลาง',LOW:'ต่ำ'}[value] || 'ไม่ระบุ');
  const year = value => String(value) + (value === data.meta.partial_year ? ' (ยังไม่ครบปี)' : '');
  function table(target, headings, rows) {
    target.innerHTML = '<table><thead><tr>' + headings.map(h => '<th scope="col">'+esc(h)+'</th>').join('') + '</tr></thead><tbody>' + (rows.length ? rows.map(row => '<tr>'+row.map(v => '<td>'+esc(v)+'</td>').join('')+'</tr>').join('') : '<tr><td colspan="'+headings.length+'">ไม่พบข้อมูลที่ตรงกัน</td></tr>') + '</tbody></table>';
    target.tabIndex = 0;
    target.setAttribute('role', 'region');
    target.setAttribute('aria-label', target.closest('.card')?.querySelector('h3')?.textContent || 'ตารางข้อมูล');
  }
  function chart(id, labels, series, {percent = false, min = 0, ticks = null} = {}) {
    const canvas = el(id), width = canvas.getBoundingClientRect().width;
    const height = Number(canvas.dataset.chartHeight || canvas.getAttribute('height')) || 260;
    canvas.dataset.chartHeight = height;
    const dpr = devicePixelRatio || 1;
    canvas.width = Math.round(width*dpr); canvas.height = Math.round(height*dpr); canvas.style.height = height+'px';
    const ctx = canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
    const values = series.flatMap(s => s.values).filter(Number.isFinite);
    const low = Math.min(min, ...values), high = Math.max(percent ? 1 : 1, ...values);
    const left = 66, right = 18, top = 22, bottom = 42;
    const x = i => left + (width-left-right)*i/Math.max(1,labels.length-1);
    const y = v => top + (height-top-bottom)*(1-(v-low)/(high-low || 1));
    ctx.font = '12px "Noto Sans Thai", sans-serif';
    for(const v of (ticks || Array.from({length:5},(_,i)=>low+(high-low)*i/4))) {
      ctx.strokeStyle = 'rgba(214,216,227,.12)';ctx.beginPath();ctx.moveTo(left,y(v));ctx.lineTo(width-right,y(v));ctx.stroke();
      ctx.fillStyle='#aeb4c5';ctx.textAlign='right';ctx.fillText(ticks ? String(v).padStart(2,'0') : percent ? num(v*100)+'%' : num(Math.round(v*100)/100),left-10,y(v)+4);
    }
    ctx.textAlign='center';
    labels.forEach((label,i) => {
      if(width < 500 && i%2 && i!==labels.length-1) return;
      const text=String(label), half=ctx.measureText(text).width/2;
      ctx.fillText(text,Math.max(half+4,Math.min(width-half-4,x(i))),height-15);
    });
    series.forEach((s,index) => {
      ctx.strokeStyle=palette[index%palette.length];ctx.lineWidth=2.5;ctx.setLineDash(index>2 ? [6,4] : []);ctx.beginPath();let started=false;
      s.values.forEach((v,i) => {if(!Number.isFinite(v)){started=false;return;} if(started)ctx.lineTo(x(i),y(v));else ctx.moveTo(x(i),y(v));started=true;});ctx.stroke();ctx.setLineDash([]);
      s.values.forEach((v,i) => {if(!Number.isFinite(v))return;ctx.fillStyle=palette[index%palette.length];ctx.beginPath();ctx.arc(x(i),y(v),3.5,0,Math.PI*2);ctx.fill();});
    });
    if(!values.length){ctx.fillStyle='#d6d8e3';ctx.fillText('ไม่มีข้อมูลสำหรับกราฟนี้',width/2,height/2);}
    let support=canvas.nextElementSibling;
    if(!support?.classList.contains('chart-support')) {support=document.createElement('div');support.className='chart-support';canvas.after(support);}
    const open=support.querySelector('details')?.open;
    support.innerHTML='<div class="chart-legend">'+series.map((s,i)=>'<span><i style="background:'+palette[i%palette.length]+'"></i>'+esc(s.name)+'</span>').join('')+'</div><details><summary>ดูตัวเลขในตาราง</summary><div class="scrollable-table"></div></details>';
    support.querySelector('details').open=!!open;
    table(support.querySelector('.scrollable-table'),['ช่วง / กลุ่ม',...series.map(s=>s.name)],labels.map((label,i)=>[label,...series.map(s=>percent?pct(s.values[i]):num(s.values[i]))]));
    canvas.setAttribute('role','img');canvas.setAttribute('aria-label',canvas.closest('.card').querySelector('h3').textContent+' มีตัวเลขครบในตารางถัดจากกราฟ');
  }
  const s = (rows,key,name) => ({name,values:rows.map(r=>r[key])});
  function annual(id,rows,key,name,percent=false,min=0){chart(id,rows.map(r=>r.year === data.meta.partial_year ? r.year+'*' : r.year),[s(rows,key,name)],{percent,min});}
  function overview(){
    const rows=data.ecosystem.yearly_metrics, selected=rows.find(r=>r.year===Number(el('summaryYear').value)) || rows.at(-1);
    el('periodNote').textContent=selected.is_ytd ? 'ปี '+selected.year+' ยังไม่ครบปี · ข้อมูลถึง '+date((data.meta.caveats?.partial_window_2026_ytd?.match(/to (\d{4}-\d{2}-\d{2})/)?.[1] || data.meta.generated_at))+' · ใช้บรรยายช่วงนี้ ห้ามเทียบกับปีเต็มเพื่อสรุปการเติบโต' : 'สรุปปี '+selected.year+' · จำนวนที่พบในชุดข้อมูล ไม่ใช่จำนวนทั้งหมดของวงการ';
    el('kpiStrip').innerHTML=[['ช่องในเครือข่าย',selected.active_channels,'ช่องที่พบหลักฐานในปีนี้'],['คู่ช่องที่เชื่อมกัน',selected.edges,'พบผู้มีปฏิสัมพันธ์ร่วมกัน'],['กลุ่มที่คำนวณได้',selected.community_count,'แบ่งจากรูปแบบความสัมพันธ์']].map(([label,value,note])=>'<div class="kpi-card"><div class="kpi-label">'+label+'</div><strong class="kpi-value">'+num(value)+'</strong><div class="kpi-sub">'+note+'</div></div>').join('');
    el('summaryHeadline').textContent=num(selected.giant_component_nodes)+' จาก '+num(selected.active_channels)+' ช่อง เชื่อมถึงกันในเครือข่ายส่วนใหญ่';
    el('summaryDetail').textContent='คิดเป็น '+pct(selected.giant_component_share)+' ของช่องในปี '+selected.year+' โดยอาจเชื่อมผ่านช่องอื่น ไม่จำเป็นต้องมีเส้นเชื่อมตรงถึงกันทุกคู่ ตัวเลขนี้บอกโครงสร้างความสัมพันธ์ ไม่ใช่ความนิยม';
    annual('canvasEcosystemGrowth',rows,'active_channels','ช่อง');annual('canvasModDensity',rows,'edges','คู่ช่อง');
    chart('canvasSurvivalOverview',data.cohorts.survival_curve.map(r=>r.elapsed_years+' ปี'),[s(data.cohorts.survival_curve,'persistence_rate','ยังพบปฏิสัมพันธ์')],{percent:true});
    annual('canvasQualityOverview',data.quality.yearly_quality,'total_interactions','รายการปฏิสัมพันธ์');
    const metrics={active_channels:'จำนวนช่อง',edges:'คู่ช่อง',density:'ความหนาแน่น',modularity:'ความชัดของกลุ่ม',cross_community_edge_share:'เส้นข้ามกลุ่ม',agency_independent_mixing:'การเชื่อมค่ายกับอิสระ',agency_at_selection_independent_mixing:'การเชื่อมค่ายกับอิสระ',agency_assortativity:'ความสัมพันธ์ภายในค่าย',agency_at_selection_assortativity:'ความสัมพันธ์ภายในค่าย'};
    table(el('breaksTable'),['ช่วงปี','ตัวชี้วัด','ก่อน','หลัง','ขอบเขต'],data.ecosystem.structural_breaks.map(r=>[r.transition.replace('->',' → ').replace('YTD','ยังไม่ครบปี'),metrics[r.metric_dimension] || 'ตัวชี้วัดโครงสร้าง',num(r.from_value),num(r.to_value),r.break_scope==='FULL_CALENDAR'?'ปีเต็ม':'ช่วงที่ยังไม่ครบปี']));
  }
  function ecosystem(){const rows=data.ecosystem.yearly_metrics;
    annual('canvasEcoFull',rows,'active_channels','ช่อง');annual('canvasEcoModDens',rows,'modularity','ความชัดของกลุ่ม');annual('canvasAgencyAssort',rows,'agency_at_selection_assortativity','ความเอนเอียงเข้าค่ายเดียวกัน',false,-1);annual('canvasCrossComm',rows,'cross_community_edge_share','เส้นข้ามกลุ่ม',true);
    table(el('ecosystemTable'),['ปี','ช่อง','คู่ช่อง','จำนวนกลุ่ม','ความหนาแน่น','เส้นเฉลี่ยต่อช่อง','ช่องในส่วนใหญ่'],rows.map(r=>[year(r.year),num(r.active_channels),num(r.edges),num(r.community_count),pct(r.density),num(r.average_degree),num(r.giant_component_nodes)]));
  }
  function lineage(){const rows=data.lineage.lifecycles;
    const years=data.meta.years;
    chart('canvasLineageTimeline',years,rows.map(r=>({name:group(r.lineage_id),values:years.map(y=>y>=r.birth_year&&y<=r.last_observed_year?Number(r.lineage_id.replace('LINEAGE_','')):null)})),{ticks:rows.map(r=>Number(r.lineage_id.replace('LINEAGE_','')))});
    table(el('lineageLifecycleTable'),['สายกลุ่ม','พบครั้งแรก','พบล่าสุด','ช่วงที่ติดตาม (ปี)','สถานะ','ค่ายหลัก','ช่องที่ไม่ซ้ำ'],rows.map(r=>[group(r.lineage_id),r.birth_year,r.last_observed_year,num(r.lifespan_years),r.lifecycle_status==='ACTIVE'?'ยังพบอยู่':'ไม่พบต่อ',agency(r.dominant_agency),num(r.total_unique_creators)]));
    const relation={continuation:'ต่อเนื่อง',merge_tributary:'ส่วนที่มารวม',split_branch:'ส่วนที่แยกออก'};
    table(el('lineageTransitionsTable'),['ช่วงปี','กลุ่มเดิม','กลุ่มถัดไป','รูปแบบ','ช่องร่วมกัน','ความเหมือน'],data.lineage.transitions.map(r=>[r.from_year+' → '+r.to_year,group(r.from_lineage_id),group(r.to_lineage_id),relation[r.relation_type]||'ไม่ระบุ',num(r.shared_channels),pct(r.jaccard_similarity)]));
  }
  function cohorts(){const rows=data.cohorts.survival_curve;
    chart('canvasCohortSurvival',rows.map(r=>r.elapsed_years+' ปี'),[s(rows,'persistence_rate','ยังพบปฏิสัมพันธ์'),s(rows,'same_channel_persistence_rate','พบกับช่องเดิม'),s(rows,'cross_channel_persistence_rate','พบกับช่องอื่น')],{percent:true});
    table(el('cohortRetentionTable'),['ปีที่พบครั้งแรก','ปีที่ติดตาม','คนในกลุ่มเริ่มต้น','คนที่พบซ้ำ','สัดส่วนที่พบซ้ำ','พบกับช่องเดิม','พบกับช่องอื่น'],data.cohorts.retention_matrix.map(r=>[r.cohort_year,year(r.observation_year),num(r.cohort_size),num(r.reobserved_viewers),pct(r.continuation_rate),pct(r.same_channel_retention_rate),pct(r.cross_channel_rate)]));
    const gaps=[...new Set(data.cohorts.reactivation.map(r=>r.gap_years))].sort((a,b)=>a-b);
    chart('canvasReactivation',gaps.map(g=>'ห่าง '+g+' ปี'),[{name:'การกลับมาพบปฏิสัมพันธ์',values:gaps.map(g=>data.cohorts.reactivation.filter(r=>r.gap_years===g).reduce((sum,r)=>sum+r.reactivated_viewers,0))}]);
  }
  function centrality(){const labels={DECLINING_BRIDGE:'บทบาทเชื่อมกลุ่มลดลง',EMERGING_BRIDGE:'เริ่มมีบทบาทเชื่อมกลุ่ม',INSUFFICIENT_EVIDENCE:'หลักฐานยังไม่พอ',MODERATE_PERIPHERAL:'บทบาทปานกลางหรือรอบนอก',STABLE_BRIDGE:'เชื่อมกลุ่มต่อเนื่อง',STABLE_BRIDGE_CANONICAL_ONLY:'ต่อเนื่องเฉพาะชุดหลัก',VOLATILE:'บทบาทเปลี่ยนแปลงมาก'};
    const rows=data.centrality.bridge_dynamics.filter(r=>r.channel_name.toLocaleLowerCase().includes(el('bridgeSearch').value.toLocaleLowerCase()));
    el('bridgeCount').textContent='พบ '+num(rows.length)+' ช่อง จาก '+num(data.centrality.bridge_dynamics.length)+' ช่อง';
    table(el('bridgeTable'),['ชื่อช่อง','ค่าย ณ เวลาเลือก','บทบาท','ปีที่พบ','ปีที่อยู่ในกลุ่มบนสุด 10%','อันดับสัมพัทธ์เฉลี่ย'],rows.map(r=>[r.channel_name,agency(r.agency_at_selection),labels[r.bridge_classification]||'ไม่ระบุ',num(r.years_observed_count),num(r.years_in_top_decile_count),pct(r.mean_betweenness_percentile)]));
    const years=[...new Set(data.centrality.change_points.map(r=>r.to_year))].sort();
    chart('canvasChangePoints',years.map(year),[1,-1].map((sign)=>({name:sign>0?'ตำแหน่งสูงขึ้น':'ตำแหน่งต่ำลง',values:years.map(y=>data.centrality.change_points.filter(r=>r.to_year===y&&r.percentile_delta*sign>0).length)})));
  }
  function quality(){table(el('qualityTable'),['ปี','รายการปฏิสัมพันธ์','ช่องในบัญชีที่พบหลักฐาน','วิดีโอที่เก็บ / ในบัญชี','สัดส่วนวิดีโอ','ระดับหลักฐาน'],data.quality.yearly_quality.map(r=>[year(r.year),num(r.total_interactions),num(r.intersection_count)+' / '+num(r.catalog_published_channel_count)+' ('+pct(r.catalog_active_recall)+')',num(r.sampled_videos)+' / '+num(r.catalog_videos),pct(r.video_sampling_ratio),tier(r.evidence_support_tier)]));
    const dist=data.quality.channel_tier_distribution;
    chart('canvasTierDonut',['สูง','ปานกลาง','ต่ำ'],[{name:'จำนวนช่อง',values:['HIGH','MODERATE','LOW'].map(k=>dist[k])}]);
    const names={BASELINE_UNIFIED_TH1:'ชุดหลัก',COMMENT_ONLY_TH1:'เฉพาะความคิดเห็น',DROPOUT_10PCT_MEAN:'สุ่มตัดข้อมูล 10% (ค่าเฉลี่ย)',LOW_COVERAGE_EXCLUDED:'ตัดช่องหลักฐานน้อย',THRESHOLD_TH3:'ผู้ร่วมอย่างน้อย 3 คน',THRESHOLD_TH5:'ผู้ร่วมอย่างน้อย 5 คน'};
    chart('canvasSensitivity',data.meta.years.map(y=>y===data.meta.partial_year?y+'*':y),Object.entries(names).map(([key,name])=>({name,values:data.meta.years.map(y=>data.quality.bias_sensitivity.find(r=>r.year===y&&r.perturbation_scenario===key)?.modularity)})));
  }
  const renderers={overview,ecosystem,lineage,cohorts,centrality,quality};
  function render(){renderers[document.querySelector('.tab-btn.active').dataset.tab]();}
  function activate(name){document.querySelectorAll('.tab-btn').forEach(button=>{const active=button.dataset.tab===name;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;el('panel-'+button.dataset.tab).classList.toggle('active',active);});render();}
  function date(value){return new Intl.DateTimeFormat('th-TH-u-ca-gregory',{day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Bangkok'}).format(new Date(value));}
  async function init(){try{const response=await fetch('research/dashboard_data.json');if(!response.ok)throw new Error('load');data=await response.json();
    el('genTimestamp').textContent='ข้อมูล ณ '+date(data.meta.generated_at);el('footerGen').textContent='จัดทำเมื่อ '+date(data.meta.generated_at);
    el('summaryYear').innerHTML=data.meta.years.map(y=>'<option value="'+y+'">'+year(y)+'</option>').join('');el('summaryYear').value=data.meta.years.at(-1);
    const buttons=[...document.querySelectorAll('.tab-btn')];buttons.forEach((button,index)=>{button.id='tab-'+button.dataset.tab;button.setAttribute('role','tab');button.setAttribute('aria-controls','panel-'+button.dataset.tab);const panel=el('panel-'+button.dataset.tab);panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby',button.id);button.addEventListener('click',()=>activate(button.dataset.tab));button.addEventListener('keydown',event=>{const next=event.key==='ArrowRight'?(index+1)%buttons.length:event.key==='ArrowLeft'?(index+buttons.length-1)%buttons.length:event.key==='Home'?0:event.key==='End'?buttons.length-1:null;if(next!==null){event.preventDefault();buttons[next].focus();buttons[next].click();}});});
    document.querySelectorAll('[data-open-tab]').forEach(button=>button.addEventListener('click',()=>{activate(button.dataset.openTab);el('tab-'+button.dataset.openTab).focus();}));
    el('summaryYear').addEventListener('change',overview);el('bridgeSearch').addEventListener('input',centrality);
    await document.fonts.ready;el('loadStatus').hidden=true;activate('overview');let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(render,120);});
  }catch(error){el('loadStatus').textContent='โหลดข้อมูลไม่สำเร็จ โปรดลองโหลดหน้านี้ใหม่';el('loadStatus').setAttribute('role','alert');}}
  init();
})();
