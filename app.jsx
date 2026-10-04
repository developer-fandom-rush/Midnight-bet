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

    if(isSceneTurn(line) && prose.length){
      flush();
    }

    prose.push(line);

    const chars=prose.reduce((n,x)=>n+x.length,0);
    if(prose.length>=4 || chars>=480){
      flush();
    }
  }

  flush();
  return blocks;
}

const EP1_SPEAKERS={
  1:"Ananya",9:"Ananya",16:"Ananya",17:"Aarav",18:"Ananya",19:"Aarav",20:"Ananya",22:"Aarav",25:"Ananya",
  33:"Kabir",35:"Aarav",36:"Kabir",37:"Aarav",38:"Kabir",
  57:"Arjun",59:"Rhea",60:"Arjun",62:"Rhea",
  76:"Tara",78:"Kabir",79:"Tara",89:"Tara",91:"Kabir",92:"Tara",101:"Tara",102:"Kabir",103:"Tara",104:"Kabir",105:"Tara",107:"Kabir",109:"Tara",
  127:"Naina",129:"Dev",130:"Naina",131:"Dev",132:"Naina",
  145:"Kabir",146:"Rhea",147:"Kabir",
  172:"Sana",174:"Aarav",179:"Naina",181:"Mira",182:"Naina",
  192:"Kabir",194:"Aarav",210:"Tara",212:"Kabir",213:"Tara",
  259:"Kabir",261:"Aarav",265:"Aarav",268:"Mira",287:"Neha",
  310:"Aarav",312:"Mira",313:"Aarav",
  332:"Dev",334:"Naina",335:"Dev",336:"Naina",
  342:"Tara",344:"Kabir",345:"Tara",346:"Kabir",347:"Tara",
  361:"Rhea",363:"Kabir",366:"Rhea",
  385:"Rhea",387:"Arjun",388:"Rhea",392:"Arjun",395:"Neha",397:"Rhea",
  420:"Ananya",429:"Shalini"
};
const EP1_CUES=new Set([191,193,258,341,384,419,428]);
const EP1_SCENES=new Set([26,40,67,113,155,217,253,296,339,369,399,415]);

function composeEpisode1(paragraphs){
  const lines=(paragraphs||[]).map(cleanLine);
  const blocks=[];
  let prose=[];
  const flush=()=>{
    if(!prose.length) return;
    blocks.push({type:"prose",text:prose.join(" ")});
    prose=[];
  };
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    if(!line) continue;
    if(EP1_SCENES.has(i)){ flush(); blocks.push({type:"break"}); }
    if(EP1_CUES.has(i)) continue;
    if(isDialogue(line)){
      flush();
      blocks.push({type:"dialogue",speaker:EP1_SPEAKERS[i]||"",text:line});
      continue;
    }
    prose.push(line);
    const chars=prose.reduce((n,x)=>n+x.length+1,0);
    if(chars>=650) flush();
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
    <p className="castNote">{cast?.note}</p>\n    {cast?.referenceGalleryDriveUrl && <p><a className="masterLink" href={cast.referenceGalleryDriveUrl} target="_blank" rel="noreferrer">Open Drive reference gallery ↗</a></p>}
    <div className="castGrid">
      {(cast?.women||[]).map(w=><article className="card" key={w.name}>
        <div className={"avatar "+(w.imageUrl?"hasImage":"")} aria-label={w.name+" portrait"}>
          {w.imageUrl ? <>
            <img src={w.imageUrl} alt={w.name+" baseline portrait"} onError={e=>{e.currentTarget.style.display="none";e.currentTarget.nextElementSibling.style.display="grid"}}/>
            <span className="avatarFallback">{w.initials}</span>
          </> : w.initials}
        </div>
        <div className="cardLinks">
          {w.driveLink && <a className="masterLink" href={w.driveLink} target="_blank" rel="noreferrer">Open master ↗</a>}
          {w.referenceSourceUrl && <a className="masterLink" href={w.referenceSourceUrl} target="_blank" rel="noreferrer">Reference source ↗</a>}
        </div>
        <h3>{w.name}</h3>
        <div className="small">Age {w.age} · {w.role}</div>
        {w.visualReference && <div className="small">Visual reference: {w.visualReference}</div>}
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
  const storyBlocks=useMemo(()=>ep===1?composeEpisode1(episode?.paragraphs||[]):composeStory(episode?.paragraphs||[]),[episode,ep]);

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
          <span className="epName">{x.title}</span>
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
          <p className="sub">Reader edition: scene prose, named dialogue and clean episode navigation.</p>
          <div className="metaRow">
            <span className="pill">24 episodes · 2 arcs</span>
            <span className="pill">Reader edition</span>
            <span className="pill">← / → keyboard navigation</span>
          </div>
        </section>

        {!episode ? <div className="loading">Loading episode…</div> :
        <article className="reader storyReader">
          {storyBlocks.map((b,i)=>
            b.type==="break"
              ? <div key={i} className="sceneBreak" aria-hidden="true">◆</div>
              : b.type==="dialogue"
                ? <p key={i} className="dialogueLine">{b.speaker&&<span className="speaker">{b.speaker}</span>}{b.text}</p>
                : <p key={i} className="storyPara">{b.text}</p>
          )}
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