import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return <><header className="topbar"><a className="brand" href="/"><span className="brand-mark">IW</span><span>INCIDENT<span className="brand-sub">WORKBENCH</span></span></a><span className="lab-label">LOCAL OPERATIONS LAB</span></header><main><section className="landing"><p className="eyebrow">EVIDENCE BEFORE ACTION</p><h1>From alarm<br/>to <em>understanding.</em></h1><p>Collect the signals. Review the diagnosis. Approve an exact plan, then verify that the service recovered.</p></section></main></>;
}
createRoot(document.getElementById("root")!).render(<App />);
