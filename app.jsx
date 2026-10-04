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
      {(cast?.women||[]).map(w=><article className="card" key={w.name}>
        <div className={"avatar "+(w.imageUrl?"hasImage":"")} aria-label={w.name+" portrait"}>
          {w.imageUrl ? <>
            <img src={w.imageUrl} alt={w.name+" baseline portrait"} onError={e=>{e.currentTarget.style.display="none";e.currentTarget.nextElementSibling.style.display="grid"}}/>
            <span className="avatarFallback">{w.initials}</span>
          </> : w.initials}
        </div>
        {w.driveLink && <a className="masterLink" href={w.driveLink} target="_blank" rel="noreferrer">Open master ↗</a>}
        <h3>{w.name}</h3>
        <div className="small">Age {w.age} · {w.role}</div>
        <div className="connection">{w.connection}</div>
        <span className="status">{w.faceStatus}</span>
      </article>)}
    </div>
    <button className="navBtn" onClick={onBack}>← Back to reader</button>
  </main>
}

function Reader(){
  const [index,setIndex]=useState(null);
  const [cast,setCast]=useState(null);
  const [episode,setEpisode]=useState(null);
  const [drawer,setDrawer]=useState(false);
  const [castMode,setCastMode]=useState(false);
  const [progress,setProgress]=useState(0);
  const [adult,setAdult]=useState(()=>sessionStorage.getItem("midnightbet-adult")==="yes");
  const max=index?.episodes?.length||12;
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
    fetch(item.file).then(r=>r.json()).then(setEpisode);
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

  if(!adult) return <AgeGate onEnter={()=>{sessionStorage.setItem("midnightbet-adult","yes");setAdult(true)}}/>;

  return <>
    <div className="progress" style={{width:progress+"%"}}/>
    <header className="topbar">
      <div className="brand">
        <button className="iconBtn" aria-label="Open episodes" onClick={()=>setDrawer(true)}>☰</button>
        <div className="brandMark">MB</div>
        <div className="brandText"><strong>Midnight Bet</strong><span>Integrated ARC I</span></div>
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
        <div className="sideTitle">Arc I · 12 Episodes</div>
        {(index?.episodes||[]).map(x=><button key={x.episode}
          className={"episodeBtn "+(x.episode===ep?"active":"")}
          onClick={()=>{go(x.episode);setDrawer(false)}}>
          <span className="epNum">{String(x.episode).padStart(2,"0")}</span>
          <span className="epName">{x.title}</span>
        </button>)}
      </aside>

      <main className="main">
        <section className="hero">
          <div className="eyebrow">ARC I · Episode {String(ep).padStart(2,"0")}</div>
          <h1>{item?.title||"Loading…"}</h1>
          <p className="sub">Old friends, new heat. Integrated final edition combining the revised episode prose with restored continuity beats from the canonical Arc I flow.</p>
          <div className="metaRow">
            <span className="pill">12 episodes</span>
            <span className="pill">Single-page reader</span>
            <span className="pill">← / → keyboard navigation</span>
          </div>
        </section>

        {!episode ? <div className="loading">Loading episode…</div> :
        <article className="reader">
          {episode.paragraphs.map((p,i)=>{
            const t=p.trim();
            const short=t.length<72;
            const quote=/^[“"]/.test(t);
            return <p key={i} className={(short?"short ":"")+(quote?"quote":"")}>{p}</p>
          })}
        </article>}

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