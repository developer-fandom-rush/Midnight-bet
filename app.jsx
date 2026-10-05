const {useEffect,useMemo,useState}=React;

function useHashEpisode(max){
  const read=()=>{
    const m=location.hash.match(/ep=(\d+)/i);
    const n=m?Number(m[1]):1;
    return Math.min(max,Math.max(1,n||1));
  };
  const [ep,setEp]=useState(read);
  useEffect(()=>{
    const fn=()=>setEp(read());
    addEventListener("hashchange",fn);
    return()=>removeEventListener("hashchange",fn);
  },[max]);
  const go=n=>{
    const next=Math.min(max,Math.max(1,n));
    location.hash="ep="+next;
    setEp(next);
    scrollTo({top:0,behavior:"smooth"});
  };
  return [ep,go];
}

function cleanLine(text){
  return String(text||"").replace(/\s+/g," ").trim();
}

function isDialogue(text){
  return /^[“"]/.test(text);
}

function isCue(text){
  return text.length<=120 && /:$/.test(text);
}

function isSceneTurn(text){
  return /^(At \d|By \d|Later\b|Across town\b|Meanwhile\b|That night\b|The next\b|After dinner\b|After the\b|Saturday\b|Sunday\b|The session\b|The reunion\b|Dinner\b)/i.test(text);
}

function composeStory(paragraphs){
  const lines=(paragraphs||[]).map(cleanLine).filter(Boolean);
  const blocks=[];
  let prose=[];

  const flush=()=>{
    if(!prose.length) return;
    blocks.push({type:"prose",text:prose.join(" ")});
    prose=[];
  };

  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    const next=lines[i+1];

    if(isCue(line) && next && isDialogue(next)){
      flush();
      blocks.push({type:"dialogue",text:line+" "+next});
      i++;
      continue;
    }

    if(isDialogue(line)){
      flush();
      blocks.push({type:"dialogue",text:line});
      continue;
    }

    if(isSceneTurn(line) && prose.length) flush();
    prose.push(line);

    const chars=prose.reduce((n,x)=>n+x.length,0);
    if(prose.length>=4 || chars>=480) flush();
  }

  flush();
  return blocks;
}

function AgeGate({onEnter}){
  return <div className="ageGate">
    <div className="gateCard">
      <div className="eyebrow">Adult fiction reader</div>
      <h2>Midnight Bet</h2>
      <p>This reader contains adult themes intended for adults only. Continue only if you are 18 or older and comfortable reading mature fictional material.</p>
      <button className="enterBtn" onClick={onEnter}>I’m 18+ — Enter Reader</button>
    </div>
  </div>
}

function Cast({cast,onBack}){
  return <main className="cast">
    <div className="eyebrow">Identity registry</div>
    <h1>Female cast</h1>
    <p className="castNote">{cast?.note}</p>
    <div className="castGrid">
      {(cast?.women||[]).map(w=>{
        const imageUrl=w.referenceImageUrl||w.imageUrl;
        const imageLink=w.referenceCropDriveLink||w.driveLink||imageUrl;
        return <article className="card" key={w.name}>
          <div className={"avatar "+(imageUrl?"hasImage":"")} aria-label={w.name+" portrait"}>
            {imageUrl ? <>
              <a href={imageLink} target="_blank" rel="noreferrer" aria-label={"Open "+w.name+" image"}>
                <img src={imageUrl} referrerPolicy="no-referrer" alt={w.name+" portrait"} style={{transform:`scale(${w.cropScale||1})`,transformOrigin:w.cropOrigin||"center 22%"}} onError={e=>{e.currentTarget.style.display="none";e.currentTarget.parentElement.nextElementSibling.style.display="grid"}}/>
              </a>
              <span className="avatarFallback">{w.initials}</span>
            </> : w.initials}
          </div>
          <h3>{w.name}</h3>
          <div className="small">Age {w.age} · {w.role}</div>
          <div className="connection">{w.connection}</div>
          <span className="status">{w.faceStatus}</span>
        </article>
      })}
    </div>
    <button className="navBtn" onClick={onBack}>← Back to reader</button>
  </main>
}

function reviewKey(kind,id){ return kind+":"+id; }

function applyFlags(text,flags,decisions){
  let next=String(text||"");
  (flags||[]).forEach(f=>{
    const decision=decisions[reviewKey("flag",f.id)];
    if(decision==="keep") return;
    next=next.replace(f.from,f.to??"");
  });
  return next.replace(/\s+([,.;!?])/g,"$1").replace(/ {2,}/g," ").trim();
}

function ProposalText({text,flags}){
  const active=(flags||[]).map(f=>({f,idx:text.indexOf(f.from)})).filter(x=>x.idx>=0).sort((a,b)=>a.idx-b.idx);
  if(!active.length) return <>{text}</>;
  const parts=[];
  let cursor=0;
  active.forEach(({f,idx},n)=>{
    if(idx<cursor) return;
    if(idx>cursor) parts.push(<React.Fragment key={"t"+n}>{text.slice(cursor,idx)}</React.Fragment>);
    parts.push(<mark key={f.id} className="deleteHighlight" title={f.reason}>{f.from}</mark>);
    cursor=idx+f.from.length;
  });
  if(cursor<text.length) parts.push(<React.Fragment key="tail">{text.slice(cursor)}</React.Fragment>);
  return <>{parts}</>;
}

function ReviewPanel({paragraphId,review,decisions,setDecision}){
  const updateDecision=decisions[reviewKey("update",paragraphId)]||"pending";
  const cleaned=applyFlags(review.proposal,review.flags,decisions);
  return <aside className={"reviewPanel "+updateDecision}>
    <div className="reviewHeader">
      <div>
        <span className="reviewZone">{review.zone}</span>
        <strong>{review.label}</strong>
      </div>
      <span className={"reviewVerdict "+updateDecision}>{updateDecision==="accept"?"Accepted":updateDecision==="reject"?"Rejected":"Decision pending"}</span>
    </div>

    <div className="reviewBlock grokBlock">
      <div className="reviewBlockLabel">Grok mechanism proposal</div>
      <p className="proposalText"><ProposalText text={review.proposal} flags={review.flags}/></p>
    </div>

    {!!review.flags?.length && <div className="flagList">
      {review.flags.map(f=>{
        const choice=decisions[reviewKey("flag",f.id)]||"pending";
        return <div className="flagCard" key={f.id}>
          <div className="flagText"><span className="flagLabel">RED FLAG</span><del>{f.from}</del></div>
          <div className="flagReason">{f.reason}</div>
          {f.to && <div className="replacement"><span>Suggested replacement:</span> {f.to}</div>}
          <div className="miniActions">
            <button className={choice==="keep"?"choiceBtn activeKeep":"choiceBtn"} onClick={()=>setDecision(reviewKey("flag",f.id),"keep")}>Keep</button>
            <button className={choice==="remove"?"choiceBtn activeRemove":"choiceBtn"} onClick={()=>setDecision(reviewKey("flag",f.id),"remove")}>{f.to?"Replace":"Remove"}</button>
          </div>
        </div>
      })}
    </div>}

    <div className="reviewBlock suggestionBlock">
      <div className="reviewBlockLabel">GPT merge suggestion · {review.verdict}</div>
      <p className="suggestionNote">{review.gptNote}</p>
      <p className="cleanPreview">{cleaned}</p>
    </div>

    <div className="reviewActions">
      <button className={updateDecision==="accept"?"reviewAction accept selected":"reviewAction accept"} onClick={()=>setDecision(reviewKey("update",paragraphId),"accept")}>Accept update</button>
      <button className={updateDecision==="reject"?"reviewAction reject selected":"reviewAction reject"} onClick={()=>setDecision(reviewKey("update",paragraphId),"reject")}>Reject · keep V4</button>
    </div>
  </aside>
}

function EpisodeOneReview({episode}){
  const storageKey="midnightbet-e01-v41-review";
  const [decisions,setDecisions]=useState(()=>{
    try{return JSON.parse(localStorage.getItem(storageKey)||"{}")}catch{return {}}
  });
  useEffect(()=>{localStorage.setItem(storageKey,JSON.stringify(decisions));},[decisions]);
  const setDecision=(key,value)=>setDecisions(prev=>({...prev,[key]:value}));

  const reviews=episode?.reviewSuggestions||{};
  const reviewIds=Object.keys(reviews);
  const accepted=reviewIds.filter(id=>decisions[reviewKey("update",id)]==="accept").length;
  const rejected=reviewIds.filter(id=>decisions[reviewKey("update",id)]==="reject").length;
  const pending=reviewIds.length-accepted-rejected;
  const flagTotal=reviewIds.reduce((n,id)=>n+(reviews[id].flags?.length||0),0);
  const flagResolved=reviewIds.reduce((n,id)=>n+(reviews[id].flags||[]).filter(f=>decisions[reviewKey("flag",f.id)]==="keep"||decisions[reviewKey("flag",f.id)]==="remove").length,0);

  const jump=id=>document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"});
  const reset=()=>{
    if(confirm("Reset all Episode 01 review choices in this browser?")) setDecisions({});
  };

  return <>
    <section className="reviewDashboard">
      <div className="reviewIntro">
        <div className="eyebrow">ARC I · EP01 · V4.1 REVIEW MODE</div>
        <h2>Scene-by-scene final pass</h2>
        <p>Read the V4 episode in full. Only Grok/GPT merge zones are annotated. Yellow shows a proposed deepening; red marks details I recommend removing or replacing. Your choices stay in this browser until we commit the final episode.</p>
      </div>
      <div className="reviewStats">
        <div><strong>{accepted}</strong><span>accepted</span></div>
        <div><strong>{rejected}</strong><span>rejected</span></div>
        <div><strong>{pending}</strong><span>pending</span></div>
        <div><strong>{flagResolved}/{flagTotal}</strong><span>red flags decided</span></div>
      </div>
      <button className="resetBtn" onClick={reset}>Reset review choices</button>
    </section>

    <nav className="sceneIndex" aria-label="Episode 01 scene index">
      {(episode.acts||[]).map(act=><div className="actIndex" key={act.id}>
        <button className="actJump" onClick={()=>jump(act.id)}>{act.title}</button>
        <div className="sceneChips">
          {act.scenes.map((s,i)=><button key={s.id} onClick={()=>jump(s.id)}>{String(i+1).padStart(2,"0")} · {s.title}</button>)}
        </div>
      </div>)}
    </nav>

    <article className="reader storyReader structuredReader">
      {(episode.acts||[]).map(act=><section className="actSection" id={act.id} key={act.id}>
        <div className="actHeading">
          <div className="eyebrow">Episode 01</div>
          <h2>{act.title}</h2>
        </div>
        {act.scenes.map((scene,sceneIndex)=><section className="sceneSection" id={scene.id} key={scene.id}>
          <div className="sceneHeading">
            <span>Scene {String(sceneIndex+1).padStart(2,"0")}</span>
            <h3>{scene.title}</h3>
          </div>
          {scene.paragraphs.map(p=>{
            const review=reviews[p.id];
            const decision=decisions[reviewKey("update",p.id)]||"pending";
            const text=review && decision==="accept" ? applyFlags(review.proposal,review.flags,decisions) : p.text;
            return <React.Fragment key={p.id}>
              <p className={"storyPara "+(review?"reviewTarget "+decision:"")}>{text}</p>
              {review && <ReviewPanel paragraphId={p.id} review={review} decisions={decisions} setDecision={setDecision}/>}
            </React.Fragment>
          })}
        </section>)}
      </section>)}
    </article>
  </>;
}

function Reader(){
  const [index,setIndex]=useState(null);
  const [cast,setCast]=useState(null);
  const [episode,setEpisode]=useState(null);
  const [drawer,setDrawer]=useState(false);
  const [castMode,setCastMode]=useState(false);
  const [progress,setProgress]=useState(0);
  const [adult,setAdult]=useState(()=>sessionStorage.getItem("midnightbet-adult")==="yes");
  const max=index?.episodes?.length||24;
  const [ep,go]=useHashEpisode(max);

  useEffect(()=>{
    Promise.all([
      fetch("./data/episodes.json").then(r=>r.json()),
      fetch("./data/cast.json").then(r=>r.json())
    ]).then(([i,c])=>{setIndex(i);setCast(c);});
  },[]);

  useEffect(()=>{
    if(!index) return;
    const item=index.episodes.find(x=>x.episode===ep)||index.episodes[0];
    setEpisode(null);
    fetch(item.file+"?v="+Date.now()).then(r=>r.json()).then(setEpisode);
  },[index,ep]);

  useEffect(()=>{
    const onScroll=()=>{
      const maxScroll=document.documentElement.scrollHeight-innerHeight;
      setProgress(maxScroll>0?Math.min(100,(scrollY/maxScroll)*100):0);
    };
    onScroll();
    addEventListener("scroll",onScroll,{passive:true});
    return()=>removeEventListener("scroll",onScroll);
  },[]);

  useEffect(()=>{
    const key=e=>{
      if(castMode) return;
      if(e.key==="ArrowLeft" && ep>1) go(ep-1);
      if(e.key==="ArrowRight" && ep<max) go(ep+1);
    };
    addEventListener("keydown",key);
    return()=>removeEventListener("keydown",key);
  },[ep,max,castMode]);

  const item=useMemo(()=>index?.episodes?.find(x=>x.episode===ep),[index,ep]);
  const storyBlocks=useMemo(()=>ep===1?[]:composeStory(episode?.paragraphs||[]),[episode,ep]);

  if(!adult) return <AgeGate onEnter={()=>{sessionStorage.setItem("midnightbet-adult","yes");setAdult(true)}}/>;

  return <>
    <div className="progress" style={{width:progress+"%"}}/>
    <header className="topbar">
      <div className="brand">
        <button className="iconBtn" aria-label="Open episodes" onClick={()=>setDrawer(true)}>☰</button>
        <div className="brandMark">MB</div>
        <div className="brandText"><strong>Midnight Bet</strong><span>{item?.arc===2?"Integrated ARC II":"Integrated ARC I"}</span></div>
      </div>
      <div className="topActions">
        <button className="iconBtn" onClick={()=>setCastMode(v=>!v)}>{castMode?"Reader":"Cast"}</button>
        {!castMode && <button className="iconBtn" onClick={()=>scrollTo({top:0,behavior:"smooth"})}>↑</button>}
      </div>
    </header>

    {castMode ? <Cast cast={cast} onBack={()=>setCastMode(false)}/> :
    <div className="layout">
      {drawer && <div className="drawerBackdrop" onClick={()=>setDrawer(false)}/>}
      <aside className={"sidebar "+(drawer?"open":"")}>
        <div className="sideTitle">ARC I · EP01–EP12</div>
        {(index?.episodes||[]).filter(x=>x.arc===1).map(x=><button key={x.episode}
          className={"episodeBtn "+(x.episode===ep?"active":"")}
          onClick={()=>{go(x.episode);setDrawer(false)}}>
          <span className="epNum">{String(x.episode).padStart(2,"0")}</span>
          <span className="epName">{x.title}{x.episode===1?<small className="reviewTag">V4 review</small>:null}</span>
        </button>)}
        <div className="sideTitle arcBreak">ARC II · EP13–EP24</div>
        {(index?.episodes||[]).filter(x=>x.arc===2).map(x=><button key={x.episode}
          className={"episodeBtn "+(x.episode===ep?"active":"")}
          onClick={()=>{go(x.episode);setDrawer(false)}}>
          <span className="epNum">{String(x.episode).padStart(2,"0")}</span>
          <span className="epName">{x.title}</span>
        </button>)}
      </aside>

      <main className="main">
        <section className="hero">
          <div className="eyebrow">ARC {item?.arc===2?"II":"I"} · Episode {String(ep).padStart(2,"0")}</div>
          <h1>{item?.title||"Loading…"}</h1>
          <p className="sub">{ep===1?"V4 story + Grok mechanism review. Scene-by-scene decisions are interactive and saved locally in your browser.":"Reader edition: scene prose, named dialogue and clean episode navigation."}</p>
          <div className="metaRow">
            <span className="pill">24 episodes · 2 arcs</span>
            <span className="pill">{ep===1?"V4.1 review candidate":"Reader edition"}</span>
            <span className="pill">← / → keyboard navigation</span>
          </div>
        </section>

        {!episode ? <div className="loading">Loading episode…</div> :
          ep===1 && episode.acts
            ? <EpisodeOneReview episode={episode}/>
            : <article className="reader storyReader">
                {storyBlocks.map((b,i)=>
                  b.type==="dialogue"
                    ? <p key={i} className="dialogueLine">{b.text}</p>
                    : <p key={i} className="storyPara">{b.text}</p>
                )}
              </article>
        }

        <nav className="bottomNav" aria-label="Episode navigation">
          <button className="navBtn" disabled={ep<=1} onClick={()=>go(ep-1)}>← Previous</button>
          <div className="centerCount">{String(ep).padStart(2,"0")} / {String(max).padStart(2,"0")}</div>
          <button className="navBtn next" disabled={ep>=max} onClick={()=>go(ep+1)}>Next →</button>
        </nav>
      </main>
    </div>}
  </>;
}

ReactDOM.createRoot(document.getElementById("root")).render(<Reader/>);