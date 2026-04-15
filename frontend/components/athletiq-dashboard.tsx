"use client";

import { ChangeEvent, DragEvent, useEffect, useMemo, useState } from "react";
import { DigitalTwinCanvas } from "./digital-twin-canvas";

type AlertLevel = "LOW" | "MODERATE" | "HIGH";

type FrameAnalysis = {
  frame: number;
  rep: number;
  left_knee_angle: number;
  right_knee_angle: number;
  angle_difference: number;
  emg_left: number;
  emg_right: number;
  asymmetry: number;
  fatigue: number;
  risk_score: number;
  alert: AlertLevel;
  grf_left: number;
  grf_right: number;
};

type PoseFrame = {
  frame: number;
  timestamp: number;
  keypoints: Record<string, [number, number, number] | null>;
};

type AnalysisResponse = {
  source: string;
  peak_risk_score: number;
  average_risk_score: number;
  alert_level: AlertLevel;
  high_risk_frame_count: number;
  total_frames_analyzed: number;
  frame_width?: number;
  frame_height?: number;
  frame_data: FrameAnalysis[];
  pose_frames: PoseFrame[];
  ai_report: string;
  message?: string;
};

const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const focusAreas = [
  { value: "full_lower_body", label: "Full Lower Body" },
  { value: "knee_focus", label: "Knee Joint Focus" },
  { value: "ankle_focus", label: "Ankle Joint Focus" },
  { value: "hamstring_focus", label: "Hamstring / Posterior Chain" }
];

const API_BASE_FROM_ENV = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE;

function getApiBase() {
  if (typeof window === "undefined") return DEFAULT_API_BASE;
  return localStorage.getItem("athletiqApiBase") || API_BASE_FROM_ENV;
}

function setApiBase(value: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("athletiqApiBase", value);
}

function riskColor(score: number) {
  if (score >= 65) return "#fb7185";
  if (score >= 40) return "#fbbf24";
  return "#34d399";
}

function getAlertClass(alert: AlertLevel) {
  if (alert === "HIGH") return "tagHigh";
  if (alert === "MODERATE") return "tagModerate";
  return "tagLow";
}

function average(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
}

function normalizeResponse(data: Partial<AnalysisResponse>): AnalysisResponse {
  return {
    source: data.source || "uploaded-video",
    peak_risk_score: data.peak_risk_score || 0,
    average_risk_score: data.average_risk_score || 0,
    alert_level: data.alert_level || "LOW",
    high_risk_frame_count: data.high_risk_frame_count || 0,
    total_frames_analyzed: data.total_frames_analyzed || data.frame_data?.length || 0,
    frame_width: data.frame_width || 720,
    frame_height: data.frame_height || 1280,
    frame_data: data.frame_data || [],
    pose_frames: data.pose_frames || [],
    ai_report: data.ai_report || "ATHLETIQ analysis complete.",
    message: data.message
  };
}

export function AthletiqDashboard() {
  const [apiBase, setApiBaseState] = useState(API_BASE_FROM_ENV);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState<string>("");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusText, setStatusText] = useState("Backend checking");
  const [focusJoint, setFocusJoint] = useState("full_lower_body");
  const [analysisType, setAnalysisType] = useState("movement_screen");
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [pipelineMessage, setPipelineMessage] = useState("");

  useEffect(() => {
    setApiBaseState(getApiBase());
    fetch(`${getApiBase()}/health`)
      .then((response) => response.json())
      .then(() => setStatusText("Backend online"))
      .catch(() => setStatusText("Backend unavailable"));
  }, []);

  const driverSummary = useMemo(() => {
    if (!analysis) {
      return {
        primary: "Awaiting athlete upload",
        action: "Upload movement video",
        simulation: "Simulations will populate once a real athlete session is analyzed."
      };
    }

    const lastFrames = analysis.frame_data.slice(-20);
    const fatigue = average(lastFrames.map((frame) => frame.fatigue || 0));
    const asymmetry = average(lastFrames.map((frame) => frame.asymmetry || 0));

    let primary = "Stable loading pattern";
    if (fatigue > 0.45) primary = "Fatigue accumulation";
    if (asymmetry > 14) primary = "Left-right asymmetry";

    let action = "Maintain monitoring";
    if (analysis.alert_level === "HIGH") action = "Reduce load and re-screen";
    if (analysis.alert_level === "MODERATE") action = "Correct mechanics before progression";

    const simulation =
      analysis.alert_level === "HIGH"
        ? "If workload rises 20%, projected hamstring risk increases materially."
        : "Use the next session to compare asymmetry and fatigue against this baseline.";

    return { primary, action, simulation };
  }, [analysis]);

  const topFrames = useMemo(() => {
    if (!analysis) return [];
    return [...analysis.frame_data]
      .sort((a, b) => b.risk_score - a.risk_score)
      .slice(0, 6);
  }, [analysis]);

  function updateFile(file: File | null) {
    if (uploadedVideoUrl) {
      URL.revokeObjectURL(uploadedVideoUrl);
    }
    setUploadedFile(file);
    setAnalysis(null);
    setErrorMessage("");
    setPipelineMessage("");
    if (!file) {
      setUploadedVideoUrl("");
      return;
    }
    const url = URL.createObjectURL(file);
    setUploadedVideoUrl(url);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    updateFile(event.target.files?.[0] || null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file && file.type.startsWith("video/")) {
      updateFile(file);
    }
  }

  async function analyzeVideo() {
    if (!uploadedFile) {
      document.getElementById("fileInput")?.click();
      return;
    }

    setIsAnalyzing(true);
    setProgress(12);
    setErrorMessage("");
    setPipelineMessage("");

    const steps = [
      { label: "Initializing YOLOv8 pose detection", pct: 22 },
      { label: "Extracting joint trajectories", pct: 42 },
      { label: "Running DSU patent engine", pct: 63 },
      { label: "Scoring asymmetry and fatigue", pct: 81 },
      { label: "Generating AI coach report", pct: 96 }
    ];

    for (const step of steps) {
      setStatusText(step.label);
      setProgress(step.pct);
      await new Promise((resolve) => setTimeout(resolve, 260));
    }

    try {
      const formData = new FormData();
      formData.append("video", uploadedFile);
      const response = await fetch(`${apiBase}/api/analyze`, {
        method: "POST",
        body: formData
      });
      if (!response.ok) {
        throw new Error(`Unable to analyze athlete motion. Backend returned ${response.status}.`);
      }
      const data = normalizeResponse(await response.json());
      setAnalysis(data);
      setPipelineMessage(data.message || "ATHLETIQ analyzed the latest uploaded athlete session.");
      if ((data.source || "").includes("demo fallback") || (data.message || "").toLowerCase().includes("unavailable")) {
        setErrorMessage("ATHLETIQ could not complete full live pose extraction, so the UI is showing fallback demo analytics for this upload.");
      }
      setStatusText("Live session analyzed");
      setProgress(100);
    } catch (error) {
      console.error(error);
      setStatusText("Analysis failed");
      setErrorMessage(error instanceof Error ? error.message : "The athlete upload failed. Check the backend URL and try again.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="appShell">
      <div className="orb orbBlue" />
      <div className="orb orbGreen" />
      <header className="topbar">
        <div className="brand">
          <img src="/ar-labs-logo.png" alt="A&R Labs logo" className="brandLogo" />
          <div>
            <p className="eyebrow">Patent-backed neuromuscular intelligence</p>
            <h1>ATHLETIQ</h1>
          </div>
        </div>
        <div className="statusCluster">
          <span className="statusPill">{statusText}</span>
          <span className="statusMeta">Front end: Next.js · Back end: FastAPI</span>
        </div>
      </header>

      <section className="hero">
        <div className="heroCopy">
          <span className="eyebrow">AI for athlete movement intelligence</span>
          <h2>
            Detect injury risk before it becomes missed time.
          </h2>
          <p>
            ATHLETIQ combines YOLOv8 pose detection, the DSU patent biomechanics engine, and an AI coaching layer to
            turn standard athlete video into neuromuscular risk insight.
          </p>
          <div className="heroStats">
            <article>
              <strong>YOLOv8 Pose</strong>
              <span>Real joint extraction from uploaded video</span>
            </article>
            <article>
              <strong>Patent Engine</strong>
              <span>Asymmetry, fatigue, GRF proxy, stability score</span>
            </article>
            <article>
              <strong>AI Coach</strong>
              <span>Trainer-facing movement interpretation</span>
            </article>
          </div>
        </div>

        <aside className="intakeCard">
          <div className="fieldRow">
            <label>Backend URL</label>
            <div className="inlineField">
              <input
                value={apiBase}
                onChange={(event) => setApiBaseState(event.target.value)}
                placeholder="http://127.0.0.1:8000"
              />
              <button
                type="button"
                className="subtleButton"
                onClick={() => {
                  setApiBase(apiBase.trim() || API_BASE_FROM_ENV);
                  setStatusText("Backend URL saved");
                }}
              >
                Save
              </button>
            </div>
          </div>

          <div className="dualFields">
            <label>
              Analysis Type
              <select value={analysisType} onChange={(event) => setAnalysisType(event.target.value)}>
                <option value="movement_screen">Movement Screen</option>
                <option value="jump_landing">Jump Landing</option>
                <option value="sprint_mechanics">Sprint Mechanics</option>
                <option value="lower_body_return">Lower Body Return-to-Play</option>
              </select>
            </label>
            <label>
              Focus Region
              <select value={focusJoint} onChange={(event) => setFocusJoint(event.target.value)}>
                {focusAreas.map((area) => (
                  <option key={area.value} value={area.value}>
                    {area.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div
            className="uploadZone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
            onClick={() => document.getElementById("fileInput")?.click()}
          >
            <input id="fileInput" type="file" accept="video/*" hidden onChange={handleFileChange} />
            <p className="uploadTitle">{uploadedFile ? uploadedFile.name : "Upload athlete movement video"}</p>
            <p className="uploadMeta">
              {uploadedFile
                ? "Video selected. Run athlete motion analysis."
                : "Drag and drop or click to upload MP4, MOV, or AVI"}
            </p>
          </div>

          <button type="button" className="primaryButton" onClick={analyzeVideo} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing Athlete Motion..." : uploadedFile ? "Analyze Athlete Motion" : "Upload Video"}
          </button>

          {pipelineMessage ? <div className="infoBanner">{pipelineMessage}</div> : null}
          {errorMessage ? <div className="errorBanner">{errorMessage}</div> : null}

          <div className="progressShell">
            <div className="progressMeta">
              <span>ATHLETIQ pipeline</span>
              <span>{progress}%</span>
            </div>
            <div className="progressBar">
              <span style={{ width: `${progress}%` }} />
            </div>
          </div>
        </aside>
      </section>

      <section className="workspace">
        <div className="panel sourcePanel">
          <div className="panelHeader">
            <div>
              <p className="panelEyebrow">Source video</p>
              <h3>Athlete capture</h3>
            </div>
            <span className={analysis ? getAlertClass(analysis.alert_level) : "tagLow"}>
              {analysis ? analysis.alert_level : "READY"}
            </span>
          </div>
          <div className="videoShell">
            {uploadedVideoUrl ? (
              <video src={uploadedVideoUrl} controls playsInline muted className="videoPlayer" />
            ) : (
              <div className="emptyState">Upload a movement video to begin the live analysis workflow.</div>
            )}
          </div>
          <div className="miniMetrics">
            <article>
              <strong>Capture layer</strong>
              <span>Standard camera video in this MVP</span>
            </article>
            <article>
              <strong>Multi-sport</strong>
              <span>Basketball, football, track, soccer, and other field/court sports</span>
            </article>
            <article>
              <strong>YOLO visibility</strong>
              <span>{analysis ? `${analysis.pose_frames.length} pose frames extracted` : "Pose overlay appears after analysis"}</span>
            </article>
            <article>
              <strong>Use case</strong>
              <span>Training, return-to-play screening, and sideline-informed review</span>
            </article>
          </div>
        </div>

        <div className="panel twinPanel">
          <div className="panelHeader">
            <div>
              <p className="panelEyebrow">Digital twin</p>
              <h3>Stylized athlete rig</h3>
            </div>
            <span className="panelTag">Pose-driven</span>
          </div>
          {analysis ? (
            <DigitalTwinCanvas
              poseFrames={analysis.pose_frames}
              frameData={analysis.frame_data}
              sourceWidth={analysis.frame_width}
              sourceHeight={analysis.frame_height}
              focusJoint={focusJoint}
            />
          ) : (
            <div className="emptyTwin">
              <h4>Awaiting athlete motion</h4>
              <p>
                Once analysis runs, ATHLETIQ maps YOLO pose keypoints into a synchronized digital twin for trainer review.
              </p>
            </div>
          )}
          <div className="legend">
            <span><i style={{ background: "#34d399" }} /> Low</span>
            <span><i style={{ background: "#fbbf24" }} /> Moderate</span>
            <span><i style={{ background: "#fb7185" }} /> High</span>
          </div>
          <div className="yoloSummary">
            <div>
              <span>Pose model</span>
              <strong>YOLOv8n-pose</strong>
            </div>
            <div>
              <span>Pose frames</span>
              <strong>{analysis ? analysis.pose_frames.length : "—"}</strong>
            </div>
            <div>
              <span>Video resolution</span>
              <strong>{analysis ? `${analysis.frame_width} × ${analysis.frame_height}` : "—"}</strong>
            </div>
          </div>
        </div>

        <div className="panel insightPanel">
          <div className="panelHeader">
            <div>
              <p className="panelEyebrow">Risk intelligence</p>
              <h3>Coach console</h3>
            </div>
            <span className="panelTag">AI + Patent Engine</span>
          </div>

          <div className="metricGrid">
            <div className="metricCard">
              <span>Peak Risk</span>
              <strong style={{ color: analysis ? riskColor(analysis.peak_risk_score) : "#e2e8f0" }}>
                {analysis ? analysis.peak_risk_score.toFixed(1) : "—"}
              </strong>
            </div>
            <div className="metricCard">
              <span>Average Risk</span>
              <strong>{analysis ? analysis.average_risk_score.toFixed(1) : "—"}</strong>
            </div>
            <div className="metricCard">
              <span>Flagged Frames</span>
              <strong>{analysis ? analysis.high_risk_frame_count : "—"}</strong>
            </div>
            <div className="metricCard">
              <span>Frames Analyzed</span>
              <strong>{analysis ? analysis.total_frames_analyzed : "—"}</strong>
            </div>
          </div>

          <div className="insightTiles">
            <article>
              <span>Primary Driver</span>
              <strong>{driverSummary.primary}</strong>
            </article>
            <article>
              <span>Coach Action</span>
              <strong>{driverSummary.action}</strong>
            </article>
            <article className="wideTile">
              <span>Simulation Callout</span>
              <strong>{driverSummary.simulation}</strong>
            </article>
          </div>

          <div className="aiCard">
            <p className="panelEyebrow">AI movement report</p>
            <p>{analysis?.ai_report || "Upload a video to generate an AI coach explanation."}</p>
          </div>
        </div>
      </section>

      <section className="detailGrid">
        <div className="panel">
          <div className="panelHeader">
            <div>
              <p className="panelEyebrow">Patent engine output</p>
              <h3>Joint load analysis</h3>
            </div>
          </div>
          <div className="loadBars">
            {analysis ? (
              [
                {
                  label: "Left calf activation",
                  value: average(analysis.frame_data.slice(-20).map((frame) => frame.emg_left)) * 100,
                  color: "#38bdf8"
                },
                {
                  label: "Right calf activation",
                  value: average(analysis.frame_data.slice(-20).map((frame) => frame.emg_right)) * 100,
                  color: "#22d3ee"
                },
                {
                  label: "Load asymmetry",
                  value: average(analysis.frame_data.slice(-20).map((frame) => frame.asymmetry)),
                  color: "#fbbf24"
                },
                {
                  label: "Fatigue index",
                  value: average(analysis.frame_data.slice(-20).map((frame) => frame.fatigue)) * 100,
                  color: "#34d399"
                }
              ].map((item) => (
                <div key={item.label} className="loadItem">
                  <div className="loadMeta">
                    <span>{item.label}</span>
                    <strong>{Math.round(item.value)}%</strong>
                  </div>
                  <div className="loadTrack">
                    <span style={{ width: `${Math.min(item.value, 100)}%`, background: item.color }} />
                  </div>
                </div>
              ))
            ) : (
              <div className="emptyState">Joint load metrics populate after athlete analysis.</div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panelHeader">
            <div>
              <p className="panelEyebrow">Flagged frames</p>
              <h3>Highest-risk sequence review</h3>
            </div>
          </div>
          <div className="frameList">
            {topFrames.length ? (
              topFrames.map((frame) => (
                <article key={frame.frame} className="frameCard">
                  <div>
                    <span>Frame {frame.frame}</span>
                    <strong>Rep {frame.rep}</strong>
                  </div>
                  <div>
                    <span>Risk</span>
                    <strong style={{ color: riskColor(frame.risk_score) }}>{frame.risk_score.toFixed(1)}</strong>
                  </div>
                  <div>
                    <span>Asymmetry</span>
                    <strong>{frame.asymmetry.toFixed(1)}%</strong>
                  </div>
                </article>
              ))
            ) : (
              <div className="emptyState">Run a session to review the frames with the highest neuromuscular risk.</div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
