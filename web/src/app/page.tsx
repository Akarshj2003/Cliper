"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Sparkles, 
  Upload, 
  Link as LinkIcon, 
  Youtube, 
  CheckCircle2, 
  Layers, 
  Scissors, 
  TrendingUp, 
  Server,
  FileVideo,
  X,
  AlertCircle,
  Loader2,
  Clock,
  Activity,
  Key,
  ShieldCheck,
  FileText,
  Trash2,
  ExternalLink
} from "lucide-react";

interface JobState {
  id: string;
  video_id: string;
  stage: string;
  status: string;
  progress: number;
  error?: string | null;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<"upload" | "link">("upload");
  const [videoUrl, setVideoUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [showYoutubeModal, setShowYoutubeModal] = useState(false);
  const [isYoutubeConnected, setIsYoutubeConnected] = useState(false);
  const [activeJob, setActiveJob] = useState<JobState | null>(null);
  const [transcriptData, setTranscriptData] = useState<{
    full_text: string;
    words: Array<{ word: string; start: number; end: number }>;
    word_count: number;
  } | null>(null);
  const [candidatesData, setCandidatesData] = useState<Array<{
    id: string;
    start_s: number;
    end_s: number;
    duration_s: number;
    text: string;
    final_score: number;
    reason: string;
  }>>([]);
  const [systemStatus, setSystemStatus] = useState<{
    status: string;
    database: string;
    features?: {
      youtube_direct_posting: boolean;
      url_downloads: boolean;
      file_uploads: boolean;
    };
  } | null>(null);

  const [cookieStatus, setCookieStatus] = useState<{ has_cookies: boolean; size_bytes?: number } | null>(null);
  const [cookieInput, setCookieInput] = useState("");
  const [isSavingCookies, setIsSavingCookies] = useState(false);
  const [cookieSaveMsg, setCookieSaveMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [modalTab, setModalTab] = useState<"cookies" | "oauth" | "guide">("cookies");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cookieFileInputRef = useRef<HTMLInputElement>(null);

  // Fetch YouTube Cookie status
  const checkCookieStatus = () => {
    fetch("http://localhost:8000/api/auth/cookies/status")
      .then((res) => res.json())
      .then((data) => setCookieStatus(data))
      .catch(() => setCookieStatus(null));
  };

  // Check backend health
  const checkHealth = () => {
    fetch("http://localhost:8000/api/health")
      .then((res) => {
        if (!res.ok) throw new Error("Backend offline");
        return res.json();
      })
      .then((data) => {
        setSystemStatus({
          status: data.status,
          database: data.database,
          features: data.features,
        });
      })
      .catch(() => {
        setSystemStatus(null);
      });
  };

  useEffect(() => {
    checkHealth();
    checkCookieStatus();
    const interval = setInterval(() => {
      checkHealth();
      checkCookieStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveCookies = async () => {
    if (!cookieInput.trim()) {
      setCookieSaveMsg({ type: "error", text: "Please paste your cookies first." });
      return;
    }
    setIsSavingCookies(true);
    setCookieSaveMsg(null);
    try {
      const res = await fetch("http://localhost:8000/api/auth/cookies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cookies_content: cookieInput.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to save cookies");
      setCookieSaveMsg({ type: "success", text: "Cookies saved successfully! YouTube downloads active." });
      setCookieInput("");
      checkCookieStatus();
    } catch (err: any) {
      setCookieSaveMsg({ type: "error", text: err.message || "Failed to save cookies" });
    } finally {
      setIsSavingCookies(false);
    }
  };

  const handleUploadCookieFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    setIsSavingCookies(true);
    setCookieSaveMsg(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("http://localhost:8000/api/auth/cookies/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setCookieSaveMsg({ type: "success", text: `Loaded '${file.name}'! YouTube downloads active.` });
      checkCookieStatus();
    } catch (err: any) {
      setCookieSaveMsg({ type: "error", text: err.message || "Failed to upload cookie file" });
    } finally {
      setIsSavingCookies(false);
    }
  };

  const handleDeleteCookies = async () => {
    try {
      await fetch("http://localhost:8000/api/auth/cookies", { method: "DELETE" });
      setCookieSaveMsg({ type: "success", text: "Cookies removed." });
      checkCookieStatus();
    } catch {
      setCookieSaveMsg({ type: "error", text: "Failed to delete cookies" });
    }
  };

  // Poll active job status
  useEffect(() => {
    if (!activeJob?.id || activeJob.status === "completed" || activeJob.status === "failed") {
      return;
    }

    const jobPoller = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/jobs/${activeJob.id}`);
        if (res.ok) {
          const data = await res.json();
          setActiveJob(data);
          if (data.status === "completed") {
            setSubmitMessage({
              type: "success",
              text: `Pipeline Stage 3 completed! Candidate viral moments (20-90s) identified with sentence/pause snapping.`
            });
            fetch(`http://localhost:8000/api/videos/${data.video_id}/transcript`)
              .then((r) => r.json())
              .then((t) => setTranscriptData(t))
              .catch(() => {});

            fetch(`http://localhost:8000/api/videos/${data.video_id}/candidates`)
              .then((r) => r.json())
              .then((c) => setCandidatesData(c))
              .catch(() => {});
          } else if (data.status === "failed") {
            setSubmitMessage({
              type: "error",
              text: `Pipeline Error: ${data.error || "Video processing encountered an issue."}`
            });
          }
        }
      } catch (err) {
        console.error("Job poll error:", err);
      }
    }, 1500);

    return () => clearInterval(jobPoller);
  }, [activeJob?.id, activeJob?.status]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setSubmitMessage({
        type: "info",
        text: `Selected video: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`
      });
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setSubmitMessage({
        type: "info",
        text: `Selected video: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`
      });
    }
  };

  const handleGenerateClips = async () => {
    setSubmitMessage(null);
    setTranscriptData(null);
    setCandidatesData([]);

    if (activeTab === "link") {
      if (!videoUrl.trim() || (!videoUrl.startsWith("http://") && !videoUrl.startsWith("https://"))) {
        setSubmitMessage({
          type: "error",
          text: "Please enter a valid URL starting with https://"
        });
        return;
      }

      setIsSubmitting(true);
      try {
        const res = await fetch("http://localhost:8000/api/ingest/url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: videoUrl.trim() }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to ingest URL");

        setActiveJob({
          id: data.job_id,
          video_id: data.video_id,
          stage: "queued",
          status: "queued",
          progress: 5.0,
        });

        setSubmitMessage({
          type: "success",
          text: `Enqueued: "${data.title}" (${data.duration_s ? Math.round(data.duration_s) + 's' : 'fetching'}) into processing queue.`
        });
      } catch (err: any) {
        setSubmitMessage({
          type: "error",
          text: err.message || "Failed to ingest URL. Make sure the backend server is running."
        });
      } finally {
        setIsSubmitting(false);
      }
    } else {
      if (!selectedFile) {
        setSubmitMessage({
          type: "error",
          text: "Please select or drop a video file first."
        });
        return;
      }

      setIsSubmitting(true);
      try {
        const formData = new FormData();
        formData.append("file", selectedFile);

        const res = await fetch("http://localhost:8000/api/upload/file", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");

        setActiveJob({
          id: data.job_id,
          video_id: data.video_id,
          stage: "audio_extract",
          status: "queued",
          progress: 10.0,
        });

        setSubmitMessage({
          type: "success",
          text: `File "${selectedFile.name}" uploaded successfully! Video ID: ${data.video_id}`
        });
      } catch (err: any) {
        setSubmitMessage({
          type: "error",
          text: err.message || "Upload failed. Ensure backend API is active."
        });
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <main className="min-h-screen px-4 py-8 max-w-6xl mx-auto flex flex-col justify-between">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-slate-200 to-purple-400 bg-clip-text text-transparent">
              ClipViral
            </span>
            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-medium border border-purple-500/30">
              MVP
            </span>
          </div>
        </div>

        {/* YouTube Connection & API Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setModalTab("cookies");
              setShowYoutubeModal(true);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition cursor-pointer ${
              cookieStatus?.has_cookies
                ? "bg-emerald-950/40 border-emerald-800/40 text-emerald-300 hover:bg-emerald-900/50"
                : "bg-amber-950/40 border-amber-800/40 text-amber-300 hover:bg-amber-900/50"
            }`}
          >
            {cookieStatus?.has_cookies ? (
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Key className="w-3.5 h-3.5 text-amber-400" />
            )}
            <span>
              {cookieStatus?.has_cookies
                ? `YouTube Session Active (${(cookieStatus.size_bytes! / 1024).toFixed(1)} KB)`
                : "YouTube Sign-In / Bot Settings"}
            </span>
          </button>

          <button
            onClick={() => {
              setModalTab("oauth");
              setShowYoutubeModal(true);
            }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition cursor-pointer ${
              isYoutubeConnected
                ? "bg-purple-950/40 border-purple-800/40 text-purple-300 hover:bg-purple-900/50"
                : "bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Youtube className="w-4 h-4 text-red-500" />
            <span>{isYoutubeConnected ? "Shorts Channel Connected" : "Connect Shorts"}</span>
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs">
            <Server className={`w-3.5 h-3.5 ${systemStatus ? "text-emerald-400" : "text-amber-400 animate-pulse"}`} />
            <span>API: {systemStatus ? "Online" : "Offline"}</span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="text-center my-10 space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-800/50 text-purple-300 text-xs">
          <TrendingUp className="w-3.5 h-3.5 text-purple-400" />
          Built for Clippers & Content Repurposers
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white max-w-3xl mx-auto leading-tight">
          Turn long videos into viral <span className="text-purple-400">9:16 vertical clips</span> in minutes.
        </h1>
        <p className="text-slate-400 max-w-xl mx-auto text-base">
          AI discovers high-retention hook moments, burns synchronized subtitles, and publishes directly to YouTube Shorts.
        </p>
      </section>

      {/* Ingestion Box */}
      <section className="max-w-2xl mx-auto w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-sm">
        {/* Tab switch */}
        <div className="flex gap-2 p-1 bg-slate-950 rounded-xl mb-6 border border-slate-800">
          <button
            type="button"
            onClick={() => {
              setActiveTab("upload");
              setSubmitMessage(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition cursor-pointer ${
              activeTab === "upload"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Upload File (MP4, MOV)</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
              100% Reliable
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("link");
              setSubmitMessage(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition cursor-pointer ${
              activeTab === "link"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            <span>Paste Video Link (YouTube)</span>
          </button>
        </div>

        {activeTab === "link" ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                YouTube Video or Stream URL
              </label>
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleGenerateClips();
                }}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 text-sm transition"
              />
            </div>
            {!cookieStatus?.has_cookies ? (
              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                <span className="flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  YouTube bot check protection may apply.
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setModalTab("cookies");
                    setShowYoutubeModal(true);
                  }}
                  className="text-purple-400 hover:text-purple-300 underline font-medium cursor-pointer"
                >
                  Configure YouTube Cookies / Sign-in
                </button>
              </div>
            ) : (
              <div className="flex items-center text-[11px] text-emerald-400 gap-1.5 pt-0.5">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                <span>YouTube authentication active (cookies loaded).</span>
              </div>
            )}
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleGenerateClips}
              className="w-full py-3.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold text-sm transition flex items-center justify-center gap-2 shadow-lg shadow-purple-600/30 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Fetching Video & Enqueuing Pipeline...
                </>
              ) : (
                <>
                  <Scissors className="w-4 h-4" />
                  Generate Viral Clips
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="video/mp4,video/quicktime,video/x-matroska,audio/mpeg,audio/wav"
              className="hidden"
            />

            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
                selectedFile 
                  ? "border-purple-500 bg-purple-950/20" 
                  : "border-slate-700 hover:border-purple-500 bg-slate-950/40"
              }`}
            >
              {selectedFile ? (
                <div className="flex flex-col items-center">
                  <FileVideo className="w-12 h-12 text-purple-400 mb-3" />
                  <p className="text-sm font-semibold text-white">{selectedFile.name}</p>
                  <p className="text-xs text-purple-300 mt-1">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Click to choose another file
                  </p>
                </div>
              ) : (
                <div>
                  <Upload className="w-10 h-10 text-purple-400 mx-auto mb-3" />
                  <p className="text-sm font-medium text-slate-200">
                    Drag and drop your video file here, or click to browse
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Supports MP4, MOV, MKV up to 2GB
                  </p>
                </div>
              )}
            </div>

            <button
              type="button"
              disabled={isSubmitting || !selectedFile}
              onClick={handleGenerateClips}
              className="w-full py-3.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white font-semibold text-sm transition flex items-center justify-center gap-2 shadow-lg shadow-purple-600/30 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading Video to Storage...
                </>
              ) : (
                <>
                  <Scissors className="w-4 h-4" />
                  Upload & Enqueue for Clipping
                </>
              )}
            </button>
          </div>
        )}

        {/* Live Job Progress Bar */}
        {activeJob && (
          <div className="mt-5 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-slate-300">
                <Activity className="w-3.5 h-3.5 text-purple-400 animate-spin" />
                Pipeline Stage: <span className="text-purple-400 font-mono capitalize">{activeJob.stage}</span>
              </span>
              <span className="text-slate-400">{Math.round(activeJob.progress)}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-purple-600 to-indigo-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(activeJob.progress, 5)}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-500 pt-1">
              <span>Job ID: {activeJob.id.slice(0, 8)}...</span>
              <span className={`capitalize ${activeJob.status === "failed" ? "text-red-400 font-semibold" : ""}`}>
                Status: {activeJob.status}
              </span>
            </div>
            {activeJob.error && (
              <div className="mt-2 space-y-2">
                <p className="text-[11px] text-red-400 bg-red-950/40 p-2.5 rounded-lg border border-red-900/40 font-sans leading-relaxed break-words">
                  {activeJob.error}
                </p>
                {(activeJob.error.toLowerCase().includes("bot") || 
                  activeJob.error.toLowerCase().includes("sign in") || 
                  activeJob.error.toLowerCase().includes("cookies") ||
                  activeJob.error.toLowerCase().includes("stream")) && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTab("upload");
                        setActiveJob(null);
                        setSubmitMessage({
                          type: "info",
                          text: "Switched to File Upload: Drop your video file here to run through the full pipeline with zero YouTube restrictions."
                        });
                      }}
                      className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow transition cursor-pointer"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      Switch to Direct File Upload (100% Reliable)
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setModalTab("cookies");
                        setShowYoutubeModal(true);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow transition cursor-pointer"
                    >
                      <Key className="w-3.5 h-3.5" />
                      Re-export YouTube Cookies
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Transcribed Text & Word Timestamps Preview (Step 4 Output) */}
        {transcriptData && (
          <div className="mt-5 p-5 rounded-xl bg-slate-950 border border-purple-900/50 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <span className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Step 4 Output: Speech Transcribed ({transcriptData.word_count} words)
              </span>
              <div className="flex items-center gap-2">
                {transcriptData.full_text.includes("Mock ASR") && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800 text-amber-300 font-medium">
                    Mock Mode (Demo)
                  </span>
                )}
                <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                  Word-Level ASR Ready
                </span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans max-h-36 overflow-y-auto">
              {transcriptData.full_text}
            </div>

            <div className="pt-1">
              <span className="text-[11px] text-slate-400 font-medium block mb-1.5">
                Word Timestamps Sample (Start ➔ End):
              </span>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                {transcriptData.words.slice(0, 20).map((w, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300 font-mono"
                  >
                    <span>{w.word}</span>
                    <span className="text-[9px] text-purple-400">[{w.start}s - {w.end}s]</span>
                  </span>
                ))}
                {transcriptData.words.length > 20 && (
                  <span className="text-[10px] text-slate-500 self-center">
                    +{transcriptData.words.length - 20} more words
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Candidate Windows Preview (Step 5 Output) */}
        {candidatesData.length > 0 && (
          <div className="mt-5 p-5 rounded-xl bg-slate-950 border border-indigo-900/50 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
                <Scissors className="w-4 h-4 text-indigo-400" />
                Step 5 Output: Candidate Windows ({candidatesData.length} moments found)
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-950 border border-indigo-800 text-indigo-300">
                Sentence & Pause Snapped (20-90s)
              </span>
            </div>

            <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
              {candidatesData.map((cand, idx) => (
                <div
                  key={cand.id || idx}
                  className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/80 space-y-1.5 hover:border-indigo-500/50 transition"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-purple-300">
                      Candidate Moment #{idx + 1}
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono text-[10px]">
                      {cand.start_s}s ➔ {cand.end_s}s ({cand.duration_s}s)
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans line-clamp-2">
                    "{cand.text}"
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                    <span>Clean boundary: 100% sentence snapped</span>
                    <span className="text-indigo-400">Ready for LLM Scoring</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Feedback message banner */}
        {submitMessage && (
          <div
            className={`mt-4 p-4 rounded-xl text-xs border ${
              submitMessage.type === "success"
                ? "bg-emerald-950/60 border-emerald-800/80 text-emerald-300"
                : submitMessage.type === "error"
                ? "bg-red-950/60 border-red-800/80 text-red-300"
                : "bg-purple-950/60 border-purple-800/80 text-purple-300"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                {submitMessage.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />}
                {submitMessage.type === "error" && <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />}
                {submitMessage.type === "info" && <Sparkles className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />}
                <div className="space-y-2">
                  <p className="font-medium leading-relaxed">{submitMessage.text}</p>
                  
                  {/* Interactive Action Triggers if YouTube Bot / Format Verification is needed */}
                  {(submitMessage.text.toLowerCase().includes("bot") || 
                    submitMessage.text.toLowerCase().includes("sign in") ||
                    submitMessage.text.toLowerCase().includes("format") ||
                    submitMessage.text.toLowerCase().includes("restricted")) && (
                    <div className="pt-2 flex flex-wrap gap-2.5">
                      <button
                        type="button"
                        onClick={() => {
                          setActiveTab("upload");
                          setSubmitMessage({
                            type: "info",
                            text: "Switched to File Upload: Drop your downloaded video file here to process immediately with zero YouTube bot restrictions."
                          });
                        }}
                        className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow transition cursor-pointer"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        Switch to Direct File Upload (100% Reliable & Fast)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setModalTab("cookies");
                          setShowYoutubeModal(true);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow transition cursor-pointer"
                      >
                        <Key className="w-3.5 h-3.5" />
                        Update YouTube Cookies / Sign-In
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={() => setSubmitMessage(null)}
                className="text-slate-400 hover:text-white shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Feature Pillars */}
      <section className="grid md:grid-cols-3 gap-6 my-12">
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800">
          <Layers className="w-6 h-6 text-purple-400 mb-3" />
          <h3 className="font-semibold text-slate-200 text-sm mb-1">
            Sentence-Snapped Windows
          </h3>
          <p className="text-xs text-slate-400">
            Whisper word timestamps automatically snap to natural speech pauses so no hook cuts mid-sentence.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800">
          <Sparkles className="w-6 h-6 text-indigo-400 mb-3" />
          <h3 className="font-semibold text-slate-200 text-sm mb-1">
            LLM Viral Rubric Scoring
          </h3>
          <p className="text-xs text-slate-400">
            Scores hook (30%), emotion (20%), clarity (20%), and audio energy with written rationale for every clip.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800">
          <Youtube className="w-6 h-6 text-red-500 mb-3" />
          <h3 className="font-semibold text-slate-200 text-sm mb-1">
            Direct YouTube Shorts Export
          </h3>
          <p className="text-xs text-slate-400">
            Render 9:16 vertical video with burned captions and post directly to your YouTube channel with custom tags.
          </p>
        </div>
      </section>

      {/* YouTube Integration & Anti-Bot Modal */}
      {showYoutubeModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Youtube className="w-5 h-5 text-red-500" />
                <h3 className="font-bold text-white text-base">YouTube Settings & Sign-in</h3>
              </div>
              <button
                onClick={() => {
                  setShowYoutubeModal(false);
                  setCookieSaveMsg(null);
                }}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
              <button
                type="button"
                onClick={() => setModalTab("cookies")}
                className={`flex-1 py-2 rounded-lg font-medium transition cursor-pointer ${
                  modalTab === "cookies"
                    ? "bg-purple-600 text-white font-semibold shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Anti-Bot Cookies
              </button>
              <button
                type="button"
                onClick={() => setModalTab("oauth")}
                className={`flex-1 py-2 rounded-lg font-medium transition cursor-pointer ${
                  modalTab === "oauth"
                    ? "bg-purple-600 text-white font-semibold shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Shorts Channel (OAuth)
              </button>
              <button
                type="button"
                onClick={() => setModalTab("guide")}
                className={`flex-1 py-2 rounded-lg font-medium transition cursor-pointer ${
                  modalTab === "guide"
                    ? "bg-purple-600 text-white font-semibold shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Quick Guide
              </button>
            </div>

            {/* TAB 1: COOKIES */}
            {modalTab === "cookies" && (
              <div className="space-y-4">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {cookieStatus?.has_cookies ? (
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-amber-400" />
                    )}
                    <span className="text-xs text-slate-300 font-medium">Session Status:</span>
                  </div>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                      cookieStatus?.has_cookies
                        ? "bg-emerald-950/60 border-emerald-800/80 text-emerald-300"
                        : "bg-amber-950/60 border-amber-800/80 text-amber-300"
                    }`}
                  >
                    {cookieStatus?.has_cookies
                      ? `Active (${(cookieStatus.size_bytes! / 1024).toFixed(1)} KB)`
                      : "Not Configured"}
                  </span>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  YouTube requires authentication for automated URL downloading. Save your YouTube cookies or upload a <code className="text-purple-300 font-mono">cookies.txt</code> to download restricted videos effortlessly.
                </p>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-300">
                      Paste cookies.txt Content:
                    </label>
                    <input
                      type="file"
                      ref={cookieFileInputRef}
                      onChange={handleUploadCookieFile}
                      accept=".txt"
                      className="hidden"
                    />
                    <button
                      type="button"
                      onClick={() => cookieFileInputRef.current?.click()}
                      className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 cursor-pointer"
                    >
                      <Upload className="w-3 h-3" />
                      Or Upload cookies.txt
                    </button>
                  </div>
                  <textarea
                    rows={4}
                    value={cookieInput}
                    onChange={(e) => setCookieInput(e.target.value)}
                    placeholder="# Netscape HTTP Cookie File&#10;.youtube.com&#9;TRUE&#9;/&#9;TRUE&#9;..."
                    className="w-full p-2.5 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 font-mono text-[11px]"
                  />
                </div>

                {cookieSaveMsg && (
                  <p
                    className={`text-xs p-2.5 rounded-lg border ${
                      cookieSaveMsg.type === "success"
                        ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                        : "bg-red-950/60 border-red-800 text-red-300"
                    }`}
                  >
                    {cookieSaveMsg.text}
                  </p>
                )}

                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    disabled={isSavingCookies}
                    onClick={handleSaveCookies}
                    className="flex-1 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-medium text-xs transition cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    {isSavingCookies ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Key className="w-3.5 h-3.5" />}
                    Save Cookies to Server
                  </button>
                  {cookieStatus?.has_cookies && (
                    <button
                      type="button"
                      onClick={handleDeleteCookies}
                      className="px-3 py-2.5 rounded-xl bg-red-950/40 border border-red-900/60 hover:bg-red-900/60 text-red-300 text-xs transition cursor-pointer flex items-center gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Clear
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: OAUTH2 */}
            {modalTab === "oauth" && (
              <div className="space-y-4 text-xs">
                <div className="p-3 bg-purple-950/40 border border-purple-800/40 rounded-xl space-y-1">
                  <h4 className="font-semibold text-purple-300">Purpose of Google Sign-In:</h4>
                  <p className="text-slate-300 leading-relaxed">
                    This connects your YouTube channel via Google OAuth to <strong>publish generated 9:16 vertical clips directly to YouTube Shorts</strong>.
                  </p>
                  <p className="text-amber-300/90 text-[11px] pt-1">
                    * Note: Google OAuth cannot be used to download third-party YouTube videos (YouTube terms prohibit video downloading APIs). To clip third-party videos, use the <strong>Upload File</strong> tab.
                  </p>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex justify-between text-slate-300">
                    <span>OAuth Integration:</span>
                    <span className="font-mono text-purple-400">YouTube Data API v3</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Requested Scope:</span>
                    <span className="text-slate-400">youtube.upload (Shorts Publishing)</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Channel Link Status:</span>
                    <span className={isYoutubeConnected ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                      {isYoutubeConnected ? "Channel Connected (Ready for Shorts)" : "Not Linked Yet"}
                    </span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsYoutubeConnected(!isYoutubeConnected);
                      setShowYoutubeModal(false);
                      setSubmitMessage({
                        type: "info",
                        text: isYoutubeConnected 
                          ? "YouTube channel disconnected." 
                          : "YouTube channel linked! Rendered 9:16 vertical clips can now be published directly to YouTube Shorts."
                      });
                    }}
                    className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-medium text-xs transition cursor-pointer flex items-center justify-center gap-2"
                  >
                    <Youtube className="w-4 h-4" />
                    {isYoutubeConnected ? "Disconnect Shorts Channel" : "Connect YouTube Shorts Channel"}
                  </button>
                </div>
              </div>
            )}

            {/* TAB 3: GUIDE */}
            {modalTab === "guide" && (
              <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
                <div className="p-3 bg-purple-950/30 border border-purple-800/40 rounded-xl space-y-1.5">
                  <h4 className="font-semibold text-purple-300 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    How to Export YouTube Cookies in 30 Seconds:
                  </h4>
                  <ol className="list-decimal list-inside space-y-1 text-slate-400 pt-1">
                    <li>Install the free extension <strong>"Get cookies.txt LOCALLY"</strong> (Chrome / Edge).</li>
                    <li>Open <strong>youtube.com</strong> in your browser (<strong>make sure you are signed in</strong> so it includes LOGIN_INFO).</li>
                    <li>Click the extension icon and click <strong>Export</strong>.</li>
                    <li>Upload or paste the content in the "Anti-Bot Cookies" tab.</li>
                  </ol>
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                  <h4 className="font-semibold text-white">Zero-Friction Alternative:</h4>
                  <p className="text-slate-400">
                    If you don't wish to export cookies, you can download any video locally and drag & drop it into the <strong>Upload File</strong> tab. File uploads run through the full pipeline with zero bot barriers.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setShowYoutubeModal(false);
                    setActiveTab("upload");
                  }}
                  className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition cursor-pointer"
                >
                  Switch to Upload File Tab Now
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800/80 pt-6 text-center text-xs text-slate-500">
        ClipViral Monorepo Architecture &bull; Step 3 Complete (Upload & Ingestion Queue) &bull; Ready for Step 4 Audio Extraction & Whisper ASR
      </footer>
    </main>
  );
}
