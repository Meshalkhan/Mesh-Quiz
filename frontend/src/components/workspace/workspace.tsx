"use client";

import {
  ArrowUp,
  ChevronDown,
  FileText,
  LoaderCircle,
  Menu,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { FormEvent, MouseEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  askQuestion,
  deleteDocument,
  getHealth,
  listDocuments,
  uploadDocument,
} from "@/lib/api";
import type {
  ChatResponse,
  DocumentSummary,
  HealthResponse,
  LlmProviderName,
} from "@/types/api";

type ChatTurn = {
  id: string;
  question: string;
  answer: string;
  sources: ChatResponse["sources"];
  provider: LlmProviderName;
};

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

const PROVIDER_LABELS: Record<LlmProviderName, string> = {
  groq: "Groq",
};

const PROVIDER_KEY_HINTS: Record<LlmProviderName, string> = {
  groq: "GROQ_API_KEY",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function Workspace() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [deletingFilename, setDeletingFilename] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [llmStatus, setLlmStatus] = useState<HealthResponse | null>(null);
  const [llmStatusError, setLlmStatusError] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] =
    useState<LlmProviderName>("groq");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const providerConfigured = useMemo(() => {
    if (!llmStatus) return false;
    return (
      llmStatus.llm_providers.find((item) => item.name === selectedProvider)
        ?.configured ?? false
    );
  }, [llmStatus, selectedProvider]);

  const providerBlockMessage = useMemo(() => {
    if (llmStatusError) {
      return llmStatusError;
    }
    if (!llmStatus) {
      return "Checking available models…";
    }
    if (!providerConfigured) {
      return `${PROVIDER_LABELS[selectedProvider]} is not configured. Set ${PROVIDER_KEY_HINTS[selectedProvider]} on the server, then restart the API.`;
    }
    return null;
  }, [llmStatus, llmStatusError, providerConfigured, selectedProvider]);

  const refreshDocuments = useCallback(async (preferFilename?: string) => {
    try {
      const response = await listDocuments();
      const next = response.data.documents;
      setDocuments(next);
      setListError(null);
      setSelectedFilename((current) => {
        if (
          preferFilename &&
          next.some((doc) => doc.filename === preferFilename)
        ) {
          return preferFilename;
        }
        if (current && next.some((doc) => doc.filename === current)) {
          return current;
        }
        return next[0]?.filename ?? null;
      });
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Could not load documents.";
      setListError(message);
    }
  }, []);

  const refreshLlmStatus = useCallback(async () => {
    try {
      const health = await getHealth();
      setLlmStatus(health);
      setLlmStatusError(null);
      setSelectedProvider((current) => {
        const currentConfigured =
          health.llm_providers.find((item) => item.name === current)
            ?.configured ?? false;
        if (currentConfigured) {
          return current;
        }
        const defaultConfigured =
          health.llm_providers.find(
            (item) => item.name === health.default_llm_provider,
          )?.configured ?? false;
        if (defaultConfigured) {
          return health.default_llm_provider;
        }
        const firstConfigured = health.llm_providers.find(
          (item) => item.configured,
        );
        return firstConfigured?.name ?? health.default_llm_provider;
      });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Could not load model availability.";
      setLlmStatusError(message);
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
    void refreshLlmStatus();
  }, [refreshDocuments, refreshLlmStatus]);

  useEffect(() => {
    setTurns([]);
    setChatError(null);
    setQuestion("");
  }, [selectedFilename]);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) {
      node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
    }
  }, [turns]);

  async function handleUpload(fileList: FileList | null) {
    const file = fileList?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadMessage("Only PDF files are supported.");
      return;
    }

    setUploading(true);
    setUploadMessage(null);
    try {
      const response = await uploadDocument(file);
      setUploadMessage(
        `Indexed ${response.data.filename} — ${response.data.indexed_count} chunks, ${formatSize(response.data.size)}`,
      );
      await refreshDocuments(response.data.filename);
      setSidebarOpen(false);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Upload failed.";
      setUploadMessage(message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function handleDelete(
    event: MouseEvent<HTMLButtonElement>,
    filename: string,
  ) {
    event.stopPropagation();
    if (deletingFilename) return;

    const confirmed = window.confirm(
      `Delete "${filename}" from the index? This cannot be undone.`,
    );
    if (!confirmed) return;

    setDeletingFilename(filename);
    setUploadMessage(null);
    try {
      const response = await deleteDocument(filename);
      setUploadMessage(
        `Deleted ${response.data.filename} — ${response.data.deleted_chunks} chunks`,
      );
      await refreshDocuments();
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Delete failed.";
      setUploadMessage(message);
    } finally {
      setDeletingFilename(null);
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || !selectedFilename || asking || !providerConfigured) return;

    setAsking(true);
    setChatError(null);
    try {
      const response = await askQuestion(
        trimmed,
        selectedFilename,
        selectedProvider,
      );
      setTurns((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          question: trimmed,
          answer: response.answer,
          sources: response.sources,
          provider: selectedProvider,
        },
      ]);
      setQuestion("");
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Could not get an answer.";
      setChatError(message);
    } finally {
      setAsking(false);
    }
  }

  const canAsk =
    Boolean(selectedFilename) &&
    !asking &&
    Boolean(question.trim()) &&
    providerConfigured;

  const providerOptions = llmStatus?.llm_providers ?? [
    { name: "groq" as const, configured: false },
  ];

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <AnimatePresence>
        {sidebarOpen ? (
          <motion.button
            aria-label="Close sidebar"
            onClick={() => setSidebarOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm lg:hidden"
          />
        ) : null}
      </AnimatePresence>

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 flex-col border-r border-border bg-card transition-transform duration-300 ease-out lg:static lg:z-auto lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex shrink-0 items-center justify-between gap-2 px-4 py-4">
          <div className="flex items-center gap-2.5">
            <span className="gradient-accent flex size-8 items-center justify-center rounded-xl text-accent-foreground shadow-soft">
              <Sparkles className="size-4" />
            </span>
            <span className="text-[0.95rem] font-semibold tracking-tight">
              Mesh Quiz
            </span>
          </div>
          <button
            type="button"
            aria-label="Close sidebar"
            onClick={() => setSidebarOpen(false)}
            className="inline-flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-surface hover:text-foreground lg:hidden"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="px-4">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(event) => void handleUpload(event.target.files)}
          />
          <Button
            variant="outline"
            className="w-full justify-start rounded-xl border-dashed"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <FileText className="size-4" />
            )}
            {uploading ? "Indexing…" : "Upload PDF"}
          </Button>

          <AnimatePresence initial={false}>
            {uploadMessage ? (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="mt-2.5 text-xs leading-relaxed text-muted-foreground"
              >
                {uploadMessage}
              </motion.p>
            ) : null}
          </AnimatePresence>

          {listError ? (
            <p className="mt-2.5 text-xs leading-relaxed text-destructive">
              {listError}
            </p>
          ) : null}
        </div>

        <div className="mt-4 flex min-h-0 flex-1 flex-col px-2 pb-4">
          <p className="px-2.5 pb-2 text-xs font-medium tracking-wide text-muted-foreground">
            Documents
          </p>
          <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-1">
            <AnimatePresence initial={false}>
              {documents.map((doc) => {
                const selected = doc.filename === selectedFilename;
                const deleting = deletingFilename === doc.filename;
                return (
                  <motion.div
                    key={doc.filename}
                    layout
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25, ease: EASE }}
                    className={`group relative flex items-center gap-2 rounded-xl pr-1 transition-colors duration-200 ${
                      selected
                        ? "bg-secondary"
                        : "hover:bg-surface"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFilename(doc.filename);
                        setSidebarOpen(false);
                      }}
                      className="flex min-w-0 flex-1 items-center gap-2.5 py-2.5 pl-2.5 text-left"
                    >
                      <FileText
                        className={`size-4 shrink-0 ${selected ? "text-accent" : "text-muted-foreground"}`}
                      />
                      <span className="min-w-0 flex-1">
                        <span
                          className={`block truncate text-sm ${
                            selected
                              ? "font-medium text-foreground"
                              : "text-foreground/80"
                          }`}
                        >
                          {doc.filename}
                        </span>
                        <span className="block text-[0.7rem] text-muted-foreground">
                          {doc.chunk_count} chunks
                        </span>
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label={`Delete ${doc.filename}`}
                      disabled={deleting || deletingFilename !== null}
                      onClick={(event) => void handleDelete(event, doc.filename)}
                      className="inline-flex size-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground/0 transition-colors duration-200 group-hover:text-muted-foreground/60 hover:!bg-destructive/10 hover:!text-destructive disabled:pointer-events-none disabled:opacity-40"
                    >
                      {deleting ? (
                        <LoaderCircle className="size-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="size-3.5" />
                      )}
                    </button>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {documents.length === 0 && !listError ? (
              <div className="mx-1 mt-2 rounded-xl border border-dashed border-border px-3 py-8 text-center text-xs leading-relaxed text-muted-foreground">
                No documents yet.
                <br />
                Upload a PDF to begin.
              </div>
            ) : null}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <button
              type="button"
              aria-label="Open sidebar"
              onClick={() => setSidebarOpen(true)}
              className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-surface hover:text-foreground lg:hidden"
            >
              <Menu className="size-4.5" />
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">
                {selectedFilename ?? "No document selected"}
              </p>
              <p className="hidden truncate text-xs text-muted-foreground sm:block">
                Answers are grounded in this document only
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2 sm:gap-2.5">
            <div className="relative">
              <select
                value={selectedProvider}
                onChange={(event) =>
                  setSelectedProvider(event.target.value as LlmProviderName)
                }
                className="h-9 w-28 cursor-pointer appearance-none truncate rounded-full border border-border bg-surface py-0 pr-7 pl-3 text-sm text-foreground transition-colors duration-200 outline-none hover:border-accent/50 focus:border-accent sm:w-auto sm:pr-8 sm:pl-3.5"
              >
                {providerOptions.map((item) => (
                  <option
                    key={item.name}
                    value={item.name}
                    className="bg-card text-foreground"
                  >
                    {PROVIDER_LABELS[item.name]}
                    {item.configured ? "" : " — not configured"}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
            </div>
            <ThemeToggle />
          </div>
        </header>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-end px-4 py-6 sm:px-6">
            {!selectedFilename ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
                <span className="gradient-accent flex size-12 items-center justify-center rounded-2xl text-accent-foreground shadow-soft">
                  <Sparkles className="size-5" />
                </span>
                <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                  Choose a document from the library to ask questions scoped
                  to that file.
                </p>
              </div>
            ) : null}

            {selectedFilename && turns.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
                <span className="gradient-accent flex size-12 items-center justify-center rounded-2xl text-accent-foreground shadow-soft">
                  <Sparkles className="size-5" />
                </span>
                <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                  Ask anything covered by this document. Answers cite the
                  pages they came from.
                </p>
              </div>
            ) : null}

            <div className="space-y-6">
              <AnimatePresence initial={false}>
                {turns.map((turn) => (
                  <motion.article
                    key={turn.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.45, ease: EASE }}
                    className="space-y-4"
                  >
                    <div className="flex justify-end">
                      <p className="max-w-[80%] rounded-2xl rounded-br-md bg-secondary px-4 py-2.5 text-sm leading-relaxed text-secondary-foreground">
                        {turn.question}
                      </p>
                    </div>

                    <div className="flex items-start gap-3">
                      <span className="gradient-accent mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full text-accent-foreground">
                        <Sparkles className="size-4" />
                      </span>
                      <div className="min-w-0 flex-1 space-y-3 pt-1">
                        <p className="text-[0.95rem] leading-[1.75] whitespace-pre-wrap text-foreground/90">
                          {turn.answer}
                        </p>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {turn.sources.map((source) => (
                            <span
                              key={`${turn.id}-${source.filename}-${source.page_number}`}
                              className="rounded-full border border-border px-2.5 py-1 text-[0.7rem] text-muted-foreground"
                            >
                              {source.filename} · p.{source.page_number}
                            </span>
                          ))}
                          <span className="ml-auto rounded-full bg-surface px-2.5 py-1 text-[0.7rem] text-muted-foreground">
                            {PROVIDER_LABELS[turn.provider]}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.article>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </div>

        <div className="shrink-0 px-4 pb-4 sm:px-6">
          <div className="mx-auto w-full max-w-3xl">
            <AnimatePresence initial={false}>
              {chatError ? (
                <motion.p
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-2 text-xs leading-relaxed text-destructive"
                >
                  {chatError}
                </motion.p>
              ) : null}
              {!chatError && providerBlockMessage ? (
                <motion.p
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-2 text-xs leading-relaxed text-muted-foreground"
                >
                  {providerBlockMessage}
                </motion.p>
              ) : null}
            </AnimatePresence>

            <form
              onSubmit={(event) => void handleAsk(event)}
              className="shadow-float flex items-end gap-2 rounded-2xl border border-border bg-card p-2 transition-colors duration-200 focus-within:border-accent/60"
            >
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                rows={1}
                placeholder={
                  !selectedFilename
                    ? "Select a document first"
                    : !providerConfigured
                      ? `${PROVIDER_LABELS[selectedProvider]} key missing on server`
                      : "Ask a question…"
                }
                disabled={!selectedFilename || asking || !providerConfigured}
                className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2 text-sm leading-[1.6] outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
              />
              <Button
                type="submit"
                size="icon"
                disabled={!canAsk}
                aria-label="Send question"
              >
                {asking ? (
                  <LoaderCircle className="size-4 animate-spin" />
                ) : (
                  <ArrowUp className="size-4" />
                )}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
