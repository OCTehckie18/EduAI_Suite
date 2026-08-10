import React, { useState, useRef, useEffect } from "react";
import {
  Send, BrainCircuit, User, Sparkles, RotateCcw,
  Copy, ThumbsUp, ThumbsDown, Paperclip, Mic,
  ChevronDown, X, Loader,
} from "lucide-react";
import { GlassCard } from "../../shared/components/GlassCard";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  ts: string;
  liked?: boolean | null;
}

const suggestedPrompts = [
  "#",
  "#",
  "#",
  "#",
  "#",
  "#",
];

const mockResponses: Record<string, string> = {
  "summarize": `#`,
  "risk": `#`,
  "generate": `#`,
  "default": `#`,
};

const getAIResponse = (input: string): string => {
  const lower = input.toLowerCase();
  if (lower.includes("summar") || lower.includes("outcome") || lower.includes("learning")) return mockResponses.summarize;
  if (lower.includes("risk") || lower.includes("at-risk") || lower.includes("student")) return mockResponses.risk;
  if (lower.includes("mcq") || lower.includes("question") || lower.includes("backprop") || lower.includes("generate")) return mockResponses.generate;
  return mockResponses.default;
};

/* ─── Simple Markdown Renderer ─────────────────────────── */
const Markdown: React.FC<{ content: string }> = ({ content }) => {
  const lines = content.split("\n");
  return (
    <div className="space-y-1.5">
      {lines.map((line, i) => {
        if (line.startsWith("**") && line.endsWith("**") && line.length > 4) {
          return <p key={i} className="font-bold text-sm" style={{ color: "var(--color-text-primary)" }}>{line.slice(2, -2)}</p>;
        }
        if (line.startsWith("> ")) {
          return (
            <div key={i} className="border-l-2 pl-3 text-xs italic" style={{ borderColor: "var(--color-brand-gold)", color: "var(--color-text-muted)" }}>
              {line.slice(2).replace(/\*\*(.*?)\*\*/g, "$1")}
            </div>
          );
        }
        if (line.startsWith("| ") && line.includes("|")) {
          const cells = line.split("|").filter(c => c.trim()).map(c => c.trim());
          return (
            <div key={i} className="flex gap-0 text-xs overflow-x-auto">
              {cells.map((c, ci) => (
                <div key={ci} className="flex-1 min-w-20 px-2 py-1 border-b" style={{ borderColor: "rgba(38,71,150,0.1)" }}>
                  {c.replace(/\[correct\]|\[high\]|\[moderate\]/g, c.includes("[correct]") ? "✓" : "").trim()}
                </div>
              ))}
            </div>
          );
        }
        if (line.startsWith("- ") || line.startsWith("• ")) {
          const text = line.slice(2);
          return (
            <p key={i} className="text-sm flex gap-2" style={{ color: "var(--color-text-secondary)" }}>
              <span style={{ color: "var(--color-brand-blue)", flexShrink: 0 }}>•</span>
              <span dangerouslySetInnerHTML={{ __html: text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") }} />
            </p>
          );
        }
        if (/^\*\*Q\d/.test(line)) {
          return <p key={i} className="text-sm font-semibold mt-3" style={{ color: "var(--color-text-primary)" }}>{line.replace(/\*\*/g, "")}</p>;
        }
        if (/^[a-d]\)/.test(line)) {
          const isCorrect = line.includes("[correct]");
          return (
            <p key={i} className={`text-sm pl-4 ${isCorrect ? "font-semibold" : ""}`}
              style={{ color: isCorrect ? "#16a34a" : "var(--color-text-secondary)" }}>
              {line.replace(" ", isCorrect ? " " : "")}
            </p>
          );
        }
        if (line.trim() === "" || line.startsWith("---")) return <div key={i} className="h-1" />;
        // inline bold
        const parts = line.split(/\*\*(.*?)\*\*/g);
        return (
          <p key={i} className="text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            {parts.map((p, pi) =>
              pi % 2 === 1 ? <strong key={pi} style={{ color: "var(--color-text-primary)" }}>{p}</strong> : p
            )}
          </p>
        );
      })}
    </div>
  );
};

export const AIChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "ai",
      content: mockResponses.default,
      ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text.trim(),
      ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages(m => [...m, userMsg]);
    setInput("");
    setLoading(true);

    setTimeout(() => {
      const aiMsg: Message = {
        id: crypto.randomUUID(),
        role: "ai",
        content: getAIResponse(text),
        ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages(m => [...m, aiMsg]);
      setLoading(false);
    }, 1200 + Math.random() * 600);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  const like = (id: string, val: boolean) => {
    setMessages(msgs => msgs.map(m => m.id === id ? { ...m, liked: m.liked === val ? null : val } : m));
  };

  const copy = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopied(id);
    setTimeout(() => setCopied(null), 1800);
  };

  const clearChat = () => {
    setMessages([{
      id: "welcome",
      role: "ai",
      content: mockResponses.default,
      ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }]);
  };

  return (
    <div className="h-[calc(100vh-130px)] flex gap-5 animate-fade-in">
      {/* ── Sidebar ── */}
      <div className="w-64 shrink-0 space-y-4 hidden lg:flex flex-col">
        <GlassCard padding="sm">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#264796,#3460c4)" }}>
              <BrainCircuit size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold" style={{ color: "var(--color-text-primary)" }}>EduAI Assistant</p>
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>Online</span>
              </div>
            </div>
          </div>
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            Powered by AI · Trained on your institutional context · All queries are private.
          </p>
        </GlassCard>

        <GlassCard padding="sm" className="flex-1">
          <p className="text-xs font-bold mb-3" style={{ color: "var(--color-text-muted)" }}>SUGGESTED PROMPTS</p>
          <div className="space-y-1.5">
            {suggestedPrompts.map((p, i) => (
              <button
                key={i}
                onClick={() => { setInput(p); inputRef.current?.focus(); }}
                className="w-full text-left text-xs px-3 py-2.5 rounded-lg transition-all hover:shadow-sm flex items-start gap-2 group"
                style={{ background: "rgba(38,71,150,0.04)", border: "1px solid rgba(38,71,150,0.08)" }}
              >
                <Sparkles size={11} className="shrink-0 mt-0.5 group-hover:text-yellow-500 transition-colors" style={{ color: "var(--color-brand-gold)" }} />
                <span style={{ color: "var(--color-text-secondary)" }}>{p}</span>
              </button>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* ── Chat Area ── */}
      <div className="flex-1 flex flex-col glass-card overflow-hidden p-0">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b"
          style={{ borderColor: "rgba(38,71,150,0.1)" }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl gradient-blue flex items-center justify-center">
              <BrainCircuit size={17} className="text-white" />
            </div>
            <div>
              <p className="font-bold text-sm" style={{ color: "var(--color-text-primary)" }}>EduAI Assistant</p>
              <p className="text-[11px]" style={{ color: "var(--color-text-muted)" }}>
                {loading ? "Thinking…" : `${messages.length - 1} message${messages.length !== 2 ? "s" : ""} in this session`}
              </p>
            </div>
          </div>
          <button onClick={clearChat} className="btn btn-ghost text-xs gap-1.5 text-slate-400">
            <RotateCcw size={13} /> New Chat
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 animate-fade-in ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                msg.role === "ai"
                  ? "gradient-blue"
                  : ""
              }`}
                style={msg.role === "user"
                  ? { background: "linear-gradient(135deg,#264796,#3460c4)" }
                  : {}}>
                {msg.role === "ai"
                  ? <BrainCircuit size={14} className="text-white" />
                  : <User size={14} className="text-white" />
                }
              </div>

              <div className={`flex flex-col gap-1.5 max-w-[78%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                {msg.role === "user" ? (
                  <div className="chat-bubble-user">
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  </div>
                ) : (
                  <div className="chat-bubble-ai">
                    <Markdown content={msg.content} />
                  </div>
                )}
                <div className={`flex items-center gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                  <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>{msg.ts}</span>
                  {msg.role === "ai" && (
                    <>
                      <button onClick={() => copy(msg.content, msg.id)}
                        className="text-[10px] flex items-center gap-0.5 transition-colors hover:text-blue-600"
                        style={{ color: "var(--color-text-muted)" }}>
                        {copied === msg.id ? "Copied!" : <><Copy size={11} /></>}
                      </button>
                      <button onClick={() => like(msg.id, true)} className={`transition-colors ${msg.liked === true ? "text-green-500" : "hover:text-green-500 text-slate-300"}`}>
                        <ThumbsUp size={12} />
                      </button>
                      <button onClick={() => like(msg.id, false)} className={`transition-colors ${msg.liked === false ? "text-red-500" : "hover:text-red-500 text-slate-300"}`}>
                        <ThumbsDown size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex gap-3 items-start animate-fade-in">
              <div className="w-8 h-8 rounded-full gradient-blue flex items-center justify-center shrink-0 mt-1">
                <BrainCircuit size={14} className="text-white" />
              </div>
              <div className="chat-bubble-ai flex items-center gap-2">
                <Loader size={14} className="animate-spin" style={{ color: "var(--color-brand-blue)" }} />
                <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>Thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input Area */}
        <div className="px-5 py-4 border-t" style={{ borderColor: "rgba(38,71,150,0.1)" }}>
          {/* Mobile Suggestions */}
          <div className="flex gap-2 overflow-x-auto pb-2 mb-3 lg:hidden">
            {suggestedPrompts.slice(0, 3).map((p, i) => (
              <button key={i} onClick={() => { setInput(p); inputRef.current?.focus(); }}
                className="btn btn-ghost text-xs shrink-0 border border-slate-200 py-1.5 px-3">
                {p.slice(0, 30)}…
              </button>
            ))}
          </div>

          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                className="form-input text-sm resize-none pr-10"
                style={{ minHeight: 44, maxHeight: 140 }}
                placeholder="Ask me anything about your students, classrooms, or content…"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                rows={1}
              />
              <button className="absolute right-3 bottom-3 text-slate-300 hover:text-blue-500 transition-colors">
                <Paperclip size={15} />
              </button>
            </div>
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              className="btn btn-primary p-3 shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ borderRadius: "12px", aspectRatio: "1" }}
            >
              <Send size={17} />
            </button>
          </div>
          <p className="text-[10px] text-center mt-2" style={{ color: "var(--color-text-muted)" }}>
            EduAI may make mistakes. Always verify critical academic decisions with your own judgment.
          </p>
        </div>
      </div>
    </div>
  );
};
