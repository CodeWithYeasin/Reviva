import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Sparkles,
  ShieldCheck,
  Image as ImageIcon,
  Film,
  Download,
  RotateCcw,
  Loader2,
  ScanFace,
} from "lucide-react";
import { HaloDropzone } from "@/components/ui/halo-dropzone";
import { BeforeAfter } from "@/components/BeforeAfter";

type Mode = "photo" | "video";
type Phase = "idle" | "working" | "done" | "error";

const ACCEPT: Record<Mode, string> = {
  photo: "image/jpeg,image/png,image/webp",
  video: "video/mp4,video/quicktime,video/webm",
};
const HINT: Record<Mode, string> = {
  photo: "JPG · PNG · WebP — up to 15 MB",
  video: "MP4 · MOV · WebM — up to 15 s",
};

export default function App() {
  const [mode, setMode] = useState<Mode>("photo");
  const [restoreFaces, setRestoreFaces] = useState(true);
  const [phase, setPhase] = useState<Phase>("idle");
  const [beforeUrl, setBeforeUrl] = useState<string | null>(null);
  const [afterUrl, setAfterUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const urls = useRef<string[]>([]);

  const revoke = () => {
    urls.current.forEach((u) => URL.revokeObjectURL(u));
    urls.current = [];
  };

  const reset = () => {
    revoke();
    setPhase("idle");
    setBeforeUrl(null);
    setAfterUrl(null);
    setErrorMsg("");
  };

  const switchMode = (m: Mode) => {
    if (m === mode) return;
    reset();
    setMode(m);
  };

  const onFiles = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;
      revoke();

      const bUrl = URL.createObjectURL(file);
      urls.current.push(bUrl);
      setBeforeUrl(bUrl);
      setErrorMsg("");
      setPhase("working");

      const form = new FormData();
      form.append("file", file);
      form.append("restore_faces", restoreFaces ? "true" : "false");

      try {
        const res = await fetch(`/api/enhance/${mode}`, {
          method: "POST",
          body: form,
        });
        if (!res.ok) {
          let detail = "Something went wrong.";
          try {
            detail = (await res.json()).detail || detail;
          } catch {
            /* ignore */
          }
          throw new Error(detail);
        }
        const blob = await res.blob();
        const aUrl = URL.createObjectURL(blob);
        urls.current.push(aUrl);
        setAfterUrl(aUrl);
        setPhase("done");
      } catch (e) {
        setErrorMsg(e instanceof Error ? e.message : "Enhancement failed.");
        setPhase("error");
      }
    },
    [mode, restoreFaces]
  );

  return (
    <div className="relative min-h-screen w-full">
      {/* ── Aurora background ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-32 h-[32rem] w-[32rem] rounded-full bg-primary/30 blur-[120px] animate-aurora" />
        <div className="absolute top-20 right-[-10rem] h-[30rem] w-[30rem] rounded-full bg-accent/25 blur-[120px] animate-aurora [animation-delay:-6s]" />
        <div className="absolute bottom-[-12rem] left-1/3 h-[28rem] w-[28rem] rounded-full bg-cyan-500/20 blur-[120px] animate-aurora [animation-delay:-12s]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,transparent,hsl(var(--background))_75%)]" />
      </div>

      <main className="relative z-10 mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-10 sm:py-16">
        {/* ── Header ── */}
        <header className="animate-fade-up flex flex-col items-center text-center">
          <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            Nothing stored · No sign-in
          </span>
          <h1 className="flex items-center gap-3 text-4xl font-extrabold tracking-tight sm:text-6xl">
            <Sparkles className="h-8 w-8 text-primary sm:h-11 sm:w-11" />
            <span className="text-gradient">Reviva</span>
          </h1>
          <p className="mt-4 max-w-md text-balance text-sm text-muted-foreground sm:text-base">
            Bring old &amp; blurry photos and videos back to life. AI enhancement
            that runs in the moment and forgets you were ever here.
          </p>
        </header>

        {/* ── Control bar ── */}
        <div className="animate-fade-up mt-10 flex flex-col items-center gap-4 [animation-delay:80ms] sm:flex-row sm:justify-between">
          <div className="flex rounded-2xl border border-white/10 bg-white/5 p-1 backdrop-blur">
            <ModeButton active={mode === "photo"} onClick={() => switchMode("photo")} icon={<ImageIcon className="h-4 w-4" />} label="Photo" />
            <ModeButton active={mode === "video"} onClick={() => switchMode("video")} icon={<Film className="h-4 w-4" />} label="Video" />
          </div>

          <button
            type="button"
            onClick={() => setRestoreFaces((v) => !v)}
            className={`flex items-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-medium backdrop-blur transition-colors ${
              restoreFaces
                ? "border-primary/40 bg-primary/15 text-foreground"
                : "border-white/10 bg-white/5 text-muted-foreground hover:text-foreground"
            }`}
          >
            <ScanFace className="h-4 w-4" />
            Restore faces
            <span className={`ml-1 h-2 w-2 rounded-full ${restoreFaces ? "bg-emerald-400" : "bg-muted-foreground/40"}`} />
          </button>
        </div>

        {/* ── Stage ── */}
        <section className="animate-fade-up mt-8 [animation-delay:160ms]">
          <AnimatePresence mode="wait">
            {phase === "idle" && (
              <motion.div
                key="drop"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
              >
                <HaloDropzone
                  accept={ACCEPT[mode]}
                  formatHint={HINT[mode]}
                  multiple={false}
                  translucent
                  onFiles={onFiles}
                  showSuccessThumbnails={false}
                />
              </motion.div>
            )}

            {phase === "working" && (
              <motion.div
                key="working"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass glow flex flex-col items-center justify-center gap-5 rounded-2xl px-6 py-20 text-center"
              >
                <div className="relative">
                  <Loader2 className="h-10 w-10 animate-spin text-primary" />
                  <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
                </div>
                <div>
                  <p className="font-semibold">Enhancing your {mode}…</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {mode === "video"
                      ? "Frame by frame — short clips take a little while."
                      : "Sharpening details and restoring faces."}
                  </p>
                </div>
              </motion.div>
            )}

            {phase === "done" && (
              <motion.div
                key="done"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-5"
              >
                {mode === "photo" && beforeUrl && afterUrl ? (
                  <BeforeAfter before={beforeUrl} after={afterUrl} />
                ) : (
                  afterUrl && (
                    <video
                      src={afterUrl}
                      controls
                      className="w-full rounded-2xl bg-black glow"
                    />
                  )
                )}

                <div className="flex gap-3">
                  <a
                    href={afterUrl ?? "#"}
                    download={mode === "photo" ? "reviva.png" : "reviva.mp4"}
                    className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-primary to-accent py-3.5 text-sm font-semibold text-white transition hover:brightness-110"
                  >
                    <Download className="h-4 w-4" />
                    Download result
                  </a>
                  <button
                    onClick={reset}
                    className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-sm font-semibold backdrop-blur transition hover:bg-white/10"
                  >
                    <RotateCcw className="h-4 w-4" />
                    New
                  </button>
                </div>
              </motion.div>
            )}

            {phase === "error" && (
              <motion.div
                key="error"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="glass rounded-2xl p-6 text-center"
              >
                <p className="font-medium text-rose-400">{errorMsg}</p>
                <button
                  onClick={reset}
                  className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold transition hover:bg-white/10"
                >
                  <RotateCcw className="h-4 w-4" />
                  Try again
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* ── Privacy strip ── */}
        <div className="animate-fade-up mt-8 grid grid-cols-1 gap-3 [animation-delay:240ms] sm:grid-cols-3">
          <Feature title="In-memory only" body="Processed in RAM, shredded the instant it's sent back." />
          <Feature title="No database" body="No accounts, no history, no content logging." />
          <Feature title="Open source" body="MIT licensed. Independent project, not affiliated with any app." />
        </div>

        <footer className="mt-auto pt-12 text-center text-xs text-muted-foreground">
          Reviva · open source · MIT
        </footer>
      </main>
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-colors ${
        active ? "bg-white/10 text-foreground shadow-inner" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{body}</p>
    </div>
  );
}
