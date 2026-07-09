import { useState, useCallback, lazy, Suspense, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Header from "./components/Header";
import DragDropZone from "./components/DragDropZone";
import LoadingState from "./components/LoadingState";
import ResultsDashboard from "./components/ResultsDashboard";
import FeatureStrip from "./components/FeatureStrip";
import { getEndpoint, validateCaptionResponse } from "./api/client.js";

const SceneBackground = lazy(() => import("./components/SceneBackground"));

// App states: "idle" | "processing" | "results" | "error"

const pageTransition = {
  initial: { opacity: 0, y: 30, scale: 0.98, filter: "blur(8px)" },
  animate: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)" },
  exit: { opacity: 0, y: -20, scale: 0.98, filter: "blur(6px)" },
  transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
};

export default function App() {
  const [appState, setAppState] = useState("idle");
  const [loadingStep, setLoadingStep] = useState(0);
  const [captions, setCaptions] = useState(null);
  const [fileName, setFileName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  // Check backend connectivity on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const endpoint = getEndpoint("/api/health");
        console.log("[APP] Checking backend health at:", endpoint);
        const response = await fetch(endpoint);
        if (!response.ok) {
          console.warn("[APP] Backend health check failed:", response.status);
        } else {
          const data = await response.json();
          console.log("[APP] Backend is ready:", data);
        }
      } catch (error) {
        console.warn("[APP] Backend not yet available:", error.message);
      }
    };
    checkBackend();
  }, []);

  const handleFileSelect = useCallback(async (file) => {
    setAppState("processing");
    setLoadingStep(0);
    setFileName(file.name);
    setErrorMsg("");
    setErrorDetails("");

    const formData = new FormData();
    formData.append("video", file);

    // Simulate step progression
    const stepTimers = [
      setTimeout(() => setLoadingStep(1), 2000),
      setTimeout(() => setLoadingStep(2), 6000),
      setTimeout(() => setLoadingStep(3), 10000),
    ];

    try {
      console.log("[APP] Uploading video:", file.name);
      const endpoint = getEndpoint("/api/caption");
      console.log("[APP] Using endpoint:", endpoint);

      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });

      stepTimers.forEach(clearTimeout);

      if (!response.ok) {
        let errorDetail = `Server error: ${response.status}`;
        try {
          const errData = await response.json();
          errorDetail = errData.detail || errorDetail;
        } catch (e) {
          console.error("[APP] Failed to parse error response:", e);
        }
        throw new Error(errorDetail);
      }

      const data = await response.json();
      console.log("[APP] Response received:", data);

      // Validate response structure
      try {
        validateCaptionResponse(data);
      } catch (validationError) {
        console.error("[APP] Response validation failed:", validationError);
        throw validationError;
      }

      setCaptions(data.captions || {});
      setAppState("results");
      console.log("[APP] Caption generation succeeded");
    } catch (err) {
      stepTimers.forEach(clearTimeout);
      console.error("[APP] Caption generation failed:", err);
      
      // Parse error message and provide details
      let userMessage = err.message || "Failed to generate captions";
      let details = "";

      if (err.message.includes("Network Error")) {
        userMessage = "Cannot connect to the backend server";
        details = "Make sure the backend is running. Check environment variables.";
      } else if (err.message.includes("Invalid response")) {
        userMessage = "Invalid response from server";
        details = err.message;
      } else if (err.status === 413) {
        userMessage = "Video file is too large";
        details = "Maximum file size is 100MB";
      } else if (err.status === 400) {
        userMessage = "Invalid video format";
        details = "Supported formats: MP4, WebM, MOV";
      } else if (err.status >= 500) {
        userMessage = "Server error occurred";
        details = `Server responded with: ${err.message}`;
      }

      setErrorMsg(userMessage);
      setErrorDetails(details);
      setAppState("error");
    }
  }, []);

  const handleReset = useCallback(() => {
    setAppState("idle");
    setCaptions(null);
    setFileName("");
    setErrorMsg("");
    setErrorDetails("");
    setLoadingStep(0);
  }, []);

  return (
    <div className="min-h-screen bg-surface-dim relative overflow-hidden">
      {/* Three.js 3D Background */}
      <Suspense fallback={null}>
        <SceneBackground />
      </Suspense>

      {/* Content */}
      <div className="relative z-10">
        <Header onReset={handleReset} showReset={appState !== "idle"} />

        <main className="px-4 sm:px-6 pb-20">
          <AnimatePresence mode="wait">
            {appState === "idle" && (
              <motion.div
                key="idle"
                {...pageTransition}
                className="pt-12 sm:pt-20"
              >
                {/* Hero text */}
                <div className="text-center mb-12 max-w-3xl mx-auto">
                  <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7 }}
                    className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight"
                  >
                    Transform Your Videos Into{" "}
                    <span className="gradient-text">Captivating Captions</span>
                  </motion.h1>
                  <motion.p
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.15 }}
                    className="text-on-surface-variant text-lg mt-5 max-w-xl mx-auto"
                  >
                    AI-powered multi-style caption generation in seconds
                  </motion.p>
                </div>

                <DragDropZone onFileSelect={handleFileSelect} isUploading={false} />
                <FeatureStrip />
              </motion.div>
            )}

            {appState === "processing" && (
              <motion.div
                key="processing"
                {...pageTransition}
                className="pt-20 sm:pt-32"
              >
                <LoadingState step={loadingStep} />
              </motion.div>
            )}

            {appState === "results" && (
              <motion.div
                key="results"
                {...pageTransition}
                className="pt-10 sm:pt-16"
              >
                <ResultsDashboard
                  captions={captions}
                  fileName={fileName}
                  onReset={handleReset}
                />
              </motion.div>
            )}

            {appState === "error" && (
              <motion.div
                key="error"
                {...pageTransition}
                className="pt-20 sm:pt-32 text-center max-w-lg mx-auto"
              >
                <div className="glass-card gradient-border rounded-2xl p-8">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-error/10 border border-error/20 flex items-center justify-center">
                    <span className="text-3xl">✕</span>
                  </div>
                  <h2 className="text-xl font-bold text-on-surface mb-2">
                    {errorMsg || "Something Went Wrong"}
                  </h2>
                  {errorDetails && (
                    <p className="text-on-surface-variant text-xs mb-4 p-3 bg-surface-bright rounded border border-outline/20 font-mono">
                      {errorDetails}
                    </p>
                  )}
                  <p className="text-on-surface-variant text-sm mb-6">
                    Please try again or contact support if the issue persists.
                  </p>
                  <button
                    onClick={handleReset}
                    className="px-6 py-3 rounded-xl font-medium gradient-primary text-white magnetic-btn
                               hover:brightness-110 transition-all duration-200 cursor-pointer"
                  >
                    Try Again
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
