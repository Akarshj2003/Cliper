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
  Activity
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
  const [activeTab, setActiveTab] = useState<"upload" | "link">("link");
  const [videoUrl, setVideoUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [showYoutubeModal, setShowYoutubeModal] = useState(false);
  const [isYoutubeConnected, setIsYoutubeConnected] = useState(false);
  const [activeJob, setActiveJob] = useState<JobState | null>(null);
  const [systemStatus, setSystemStatus] = useState<{
    status: string;
    database: string;
    features?: {
      youtube_direct_posting: boolean;
      url_downloads: boolean;
      file_uploads: boolean;
    };
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

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
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

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
              text: `Pipeline stage "${data.stage}" completed successfully! Ready for AI transcription & scoring.`
            });
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
            onClick={() => setShowYoutubeModal(true)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition cursor-pointer ${
              isYoutubeConnected
                ? "bg-emerald-950/40 border-emerald-800/40 text-emerald-300 hover:bg-emerald-900/50"
                : "bg-red-950/40 border-red-800/40 text-red-300 hover:bg-red-900/50"
            }`}
          >
            <Youtube className="w-4 h-4 text-red-500" />
            <span>{isYoutubeConnected ? "YouTube Connected" : "Connect YouTube"}</span>
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs">
            <Server className={`w-3.5 h-3.5 ${systemStatus ? "text-emerald-400" : "text-amber-400 animate-pulse"}`} />
            <span>API: {systemStatus ? "Online (Port 8000)" : "Offline"}</span>
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
            Paste Video Link (YouTube / URL)
          </button>
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
            Upload File (MP4, MOV)
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
              <p className="text-[11px] text-red-400 bg-red-950/40 p-2 rounded-lg border border-red-900/40 font-mono break-words mt-1">
                {activeJob.error}
              </p>
            )}
          </div>
        )}

        {/* Feedback message banner */}
        {submitMessage && (
          <div
            className={`mt-4 p-3.5 rounded-xl text-xs flex items-center justify-between border ${
              submitMessage.type === "success"
                ? "bg-emerald-950/60 border-emerald-800/80 text-emerald-300"
                : submitMessage.type === "error"
                ? "bg-red-950/60 border-red-800/80 text-red-300"
                : "bg-purple-950/60 border-purple-800/80 text-purple-300"
            }`}
          >
            <div className="flex items-center gap-2">
              {submitMessage.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
              {submitMessage.type === "error" && <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />}
              {submitMessage.type === "info" && <Sparkles className="w-4 h-4 text-purple-400 shrink-0" />}
              <span>{submitMessage.text}</span>
            </div>
            <button
              onClick={() => setSubmitMessage(null)}
              className="text-slate-400 hover:text-white shrink-0 ml-2"
            >
              <X className="w-3.5 h-3.5" />
            </button>
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

      {/* YouTube Channel Modal */}
      {showYoutubeModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Youtube className="w-5 h-5 text-red-500" />
                <h3 className="font-bold text-white text-base">YouTube Account Integration</h3>
              </div>
              <button
                onClick={() => setShowYoutubeModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Connect your YouTube channel using Google OAuth2 to publish rendered 9:16 clips straight to YouTube Shorts with automated titles, descriptions, and tags.
            </p>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between text-slate-300">
                <span>OAuth Client ID:</span>
                <span className="font-mono text-purple-400">Configured in .env</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Permissions:</span>
                <span className="text-slate-400">youtube.upload</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Current Status:</span>
                <span className={isYoutubeConnected ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                  {isYoutubeConnected ? "Channel Connected" : "Not Linked Yet"}
                </span>
              </div>
            </div>

            <div className="pt-2 flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setIsYoutubeConnected(!isYoutubeConnected);
                  setShowYoutubeModal(false);
                }}
                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-medium text-xs transition cursor-pointer"
              >
                {isYoutubeConnected ? "Disconnect Channel" : "Simulate Connect Channel"}
              </button>
              <button
                type="button"
                onClick={() => setShowYoutubeModal(false)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition cursor-pointer"
              >
                Close
              </button>
            </div>
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
