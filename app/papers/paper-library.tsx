"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { RecommendationFeedback } from "@/lib/papers";
import { registerUploadedFile, setRecommendationAction, signOutPaperLibrary } from "./actions";
import type { Paper } from "./data";
import {
  canWritePaperDirectory,
  choosePaperDirectory,
  loadPaperDirectory,
  savePaperPdf,
  supportsPaperDirectoryPicker,
  type PaperDirectoryHandle,
} from "./local-paper-folder";

type Section = "today" | "library" | "search" | "topics" | "reading" | "import";
type Feedback = RecommendationFeedback;

const navigation: { id: Section; label: string; short: string }[] = [
  { id: "today", label: "今日推荐", short: "今日" },
  { id: "library", label: "我的论文", short: "论文" },
  { id: "search", label: "全局检索", short: "检索" },
  { id: "topics", label: "主题分类", short: "主题" },
  { id: "reading", label: "阅读清单", short: "清单" },
  { id: "import", label: "导入论文", short: "导入" },
];

function includesQuery(paper: Paper, query: string) {
  const value = query.trim().toLowerCase();
  if (!value) return true;
  return [paper.title, paper.venue, paper.topic, String(paper.year), paper.reason ?? ""]
    .join(" ")
    .toLowerCase()
    .includes(value);
}

function PaperMeta({ paper }: { paper: Paper }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="rounded-full bg-blue-50 px-2.5 py-1 font-medium text-blue-700">{paper.topic}</span>
      <span className="text-slate-500">{paper.venue} {paper.year}</span>
      {paper.match ? (
        <>
          <span className="text-slate-300">/</span>
          <span className="font-medium text-emerald-600">匹配度 {paper.match}%</span>
        </>
      ) : null}
    </div>
  );
}

function paperOpenPath(paper: Paper, kind: "pdf" | "source" | "analysis") {
  return `/papers/open/${encodeURIComponent(paper.id)}?kind=${kind}`;
}

function PaperLinks({
  paper,
  compact = false,
  onSaveLocally,
}: {
  paper: Paper;
  compact?: boolean;
  onSaveLocally?: (paper: Paper) => void;
}) {
  return (
    <div className={`flex flex-wrap items-center ${compact ? "gap-x-3 gap-y-2" : "gap-2"}`}>
      {paper.hasPdf ? (
        <>
          <a
            href={paperOpenPath(paper, "pdf")}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-9 items-center rounded-lg bg-blue-600 px-3 text-xs font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-100"
          >
            查看 PDF ↗
          </a>
          {onSaveLocally ? (
            <button
              type="button"
              onClick={() => onSaveLocally(paper)}
              className="inline-flex h-9 items-center rounded-lg border border-blue-200 bg-blue-50 px-3 text-xs font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
            >
              保存到本地
            </button>
          ) : null}
        </>
      ) : null}
      <a
        href={paperOpenPath(paper, "source")}
        target="_blank"
        rel="noopener noreferrer"
        className={`${paper.hasPdf || !compact ? "inline-flex h-9 items-center rounded-lg border border-slate-300 px-3" : "font-medium text-blue-600 hover:text-blue-700"} text-xs transition hover:border-blue-300 hover:bg-blue-50`}
      >
        {paper.sourceLinkKind === "direct" ? "论文网站 ↗" : "查找原文 ↗"}
      </a>
      {paper.hasAnalysisFile ? (
        <a
          href={paperOpenPath(paper, "analysis")}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-medium text-slate-600 transition hover:text-blue-600"
        >
          查看分析 ↗
        </a>
      ) : null}
    </div>
  );
}

export default function PaperLibrary({
  library,
  recommendations,
  feedback: initialFeedback,
  dateLabel,
}: {
  library: Paper[];
  recommendations: Paper[];
  feedback: Record<string, Feedback>;
  dateLabel: string;
}) {
  const router = useRouter();
  const [section, setSection] = useState<Section>("today");
  const [query, setQuery] = useState("");
  const [feedback, setFeedback] = useState<Record<string, Feedback>>(initialFeedback);
  const [notice, setNotice] = useState("推荐反馈会安全保存，并用于调整后续推荐");
  const [paperDirectory, setPaperDirectory] = useState<PaperDirectoryHandle | null>(null);
  const [directoryPickerSupported, setDirectoryPickerSupported] = useState(false);
  const [pickedFiles, setPickedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [, startTransition] = useTransition();
  const fileInput = useRef<HTMLInputElement>(null);

  const savedRecommendations = recommendations.filter((paper) => feedback[paper.id] === "saved");
  const readingList = recommendations.filter((paper) => feedback[paper.id] === "later");
  const fullLibrary = useMemo(
    () => [...new Map([...library, ...savedRecommendations].map((paper) => [paper.id, paper])).values()],
    [library, savedRecommendations],
  );
  const processedCount = Object.keys(feedback).length;

  useEffect(() => {
    const supported = supportsPaperDirectoryPicker();
    loadPaperDirectory()
      .then((handle) => {
        setDirectoryPickerSupported(supported);
        setPaperDirectory(handle);
      })
      .catch(() => {
        setDirectoryPickerSupported(supported);
        setPaperDirectory(null);
      });
  }, []);

  const searchResults = useMemo(
    () => [...fullLibrary, ...recommendations.filter((paper) => !feedback[paper.id])].filter((paper) => includesQuery(paper, query)),
    [feedback, fullLibrary, query, recommendations],
  );

  const topics = useMemo(() => {
    const counts = new Map<string, number>();
    fullLibrary.forEach((paper) => counts.set(paper.topic, (counts.get(paper.topic) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [fullLibrary]);

  async function configurePaperDirectory() {
    try {
      const handle = await choosePaperDirectory();
      setPaperDirectory(handle);
      setNotice(`已选择“${handle.name}”，有可用 PDF 时将自动保存到此文件夹`);
      return handle;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setNotice("未更改本地保存文件夹");
      } else {
        setNotice("无法使用该文件夹，请检查 Chrome 的文件访问权限");
      }
      return null;
    }
  }

  async function preparePaperDirectory() {
    let directory = paperDirectory;
    if (!directory) directory = await configurePaperDirectory();
    if (!directory) return null;

    const canWrite = await canWritePaperDirectory(directory, true).catch(() => false);
    if (!canWrite) {
      setNotice("未获得文件夹写入权限，请重新选择本地保存文件夹");
      return null;
    }
    return directory;
  }

  async function savePaperLocally(paper: Paper) {
    if (!paper.hasPdf) {
      setNotice(`《${paper.title}》暂时没有可直接下载的 PDF`);
      return;
    }
    const directory = await preparePaperDirectory();
    if (!directory) return;

    setNotice(`正在把《${paper.title}》保存到“${directory.name}”…`);
    try {
      await savePaperPdf(directory, paper.id, paper.title);
      setNotice(`《${paper.title}》已保存到“${directory.name}”`);
    } catch {
      setNotice("PDF 下载失败，请稍后重试或点击“查看 PDF”阅读");
    }
  }

  async function giveFeedback(paper: Paper, value: Feedback) {
    let directory = paperDirectory;
    let canSaveLocally = false;
    if (value === "saved" && paper.hasPdf && (directoryPickerSupported || supportsPaperDirectoryPicker())) {
      directory = await preparePaperDirectory();
      canSaveLocally = Boolean(directory);
    }

    const previous = feedback[paper.id];
    setFeedback((current) => ({ ...current, [paper.id]: value }));
    const message = value === "saved"
      ? `已将《${paper.title}》存入论文库`
      : value === "later"
        ? `已将《${paper.title}》加入稍后阅读`
        : `已减少与《${paper.title}》相似的推荐`;
    setNotice(message);

    startTransition(async () => {
      const result = await setRecommendationAction(paper.id, value);
      if (result.ok) {
        if (value === "saved" && paper.hasPdf && directory && canSaveLocally) {
          try {
            await savePaperPdf(directory, paper.id, paper.title);
            setNotice(`《${paper.title}》已存入论文库，并下载到“${directory.name}”`);
          } catch {
            setNotice(`《${paper.title}》已存入论文库；PDF 下载失败，可点击“查看 PDF”阅读`);
          }
        } else if (value === "saved" && !paper.hasPdf) {
          setNotice(`《${paper.title}》已存入论文库；暂未找到可直接下载的 PDF`);
        } else if (value === "saved" && directoryPickerSupported && !canSaveLocally) {
          setNotice(`《${paper.title}》已存入论文库；本次未获得文件夹写入权限`);
        }
        return;
      }

      setFeedback((current) => {
        const next = { ...current };
        if (previous) next[paper.id] = previous;
        else delete next[paper.id];
        return next;
      });
      setNotice(result.error);
    });
  }

  async function uploadPickedFiles() {
    if (!pickedFiles.length || uploading) return;
    setUploading(true);
    setNotice(`正在上传 0 / ${pickedFiles.length} 个文件`);

    const supabase = createClient();
    const { data: claimsData } = await supabase.auth.getClaims();
    const userId = String(claimsData?.claims?.sub ?? "");
    if (!userId) {
      setNotice("登录已过期，请重新登录后再上传。");
      setUploading(false);
      return;
    }

    let completed = 0;
    for (const file of pickedFiles) {
      const extension = file.name.split(".").pop()?.toLowerCase();
      const mimeType = file.type || (extension === "pdf" ? "application/pdf" : "text/markdown");
      if (!["application/pdf", "text/markdown", "text/plain"].includes(mimeType) || file.size > 50 * 1024 * 1024) {
        setNotice(`已跳过不支持或超过 50 MB 的文件：${file.name}`);
        continue;
      }

      const safeName = file.name.replace(/[\\/]/g, "-");
      const storagePath = `${userId}/${crypto.randomUUID()}/${safeName}`;
      const { error: uploadError } = await supabase.storage.from("papers").upload(storagePath, file, {
        contentType: mimeType,
        upsert: false,
      });

      if (uploadError) {
        setNotice(`上传失败：${file.name}`);
        continue;
      }

      const result = await registerUploadedFile({
        storagePath,
        filename: file.name,
        mimeType,
        size: file.size,
      });

      if (!result.ok) {
        await supabase.storage.from("papers").remove([storagePath]);
        setNotice(`${file.name}：${result.error}`);
        continue;
      }

      completed += 1;
      setNotice(`正在上传 ${completed} / ${pickedFiles.length} 个文件`);
    }

    setUploading(false);
    if (completed) {
      setPickedFiles([]);
      setNotice(`已安全上传 ${completed} 个文件，并加入论文库`);
      router.refresh();
    }
  }

  function openSection(next: Section) {
    setSection(next);
    if (next !== "search") setQuery("");
  }

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-slate-950">
      <div aria-live="polite" className="sr-only">{notice}</div>
      <div className="mx-auto grid min-h-[calc(100vh-69px)] max-w-[1440px] lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-[#0f1b2d] px-5 py-5 text-white lg:border-b-0 lg:border-r lg:border-slate-800 lg:py-6">
          <div className="flex items-center justify-between lg:block">
            <button type="button" onClick={() => openSection("today")} className="text-left">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-300">Ruiyuan&apos;s</p>
              <h1 className="mt-1.5 text-xl font-semibold">Paper Library</h1>
            </button>
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-300">Private</span>
              <form action={signOutPaperLibrary}>
                <button type="submit" className="rounded-full px-2 py-1 text-xs text-slate-400 transition hover:bg-white/10 hover:text-white">退出</button>
              </form>
            </div>
          </div>

          <nav aria-label="论文库导航" className="mt-5 grid grid-cols-3 gap-2 lg:mt-10 lg:grid-cols-1">
            {navigation.map((item, index) => (
              <button
                key={item.id}
                type="button"
                onClick={() => openSection(item.id)}
                aria-current={section === item.id ? "page" : undefined}
                className={`rounded-lg px-2 py-2.5 text-center text-sm transition lg:px-3 lg:text-left ${
                  section === item.id
                    ? "bg-blue-500 font-medium text-white"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <span className="mr-2 hidden w-5 text-center text-xs opacity-70 lg:inline-block">0{index + 1}</span>
                <span className="lg:hidden">{item.short}</span>
                <span className="hidden lg:inline">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="mt-8 hidden rounded-xl border border-slate-700 bg-white/5 p-4 lg:block">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>本周阅读目标</span>
              <span>3 / 5</span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-700">
              <div className="h-full w-3/5 rounded-full bg-orange-400" />
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-400">连续阅读 4 天，保持节奏。</p>
          </div>
        </aside>

        <section className="min-w-0 px-5 py-6 sm:px-8 lg:px-10 lg:py-8">
          <header className="flex flex-col gap-5 border-b border-slate-200 pb-6 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600">{dateLabel}</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                {section === "today" && "今日为你挑选的论文"}
                {section === "library" && "我的论文库"}
                {section === "search" && "全局检索"}
                {section === "topics" && "主题分类"}
                {section === "reading" && "稍后阅读"}
                {section === "import" && "导入论文"}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                {section === "today" && "根据你的 11 篇论文与深度分析生成。每一次选择，都会改善下一次推荐。"}
                {section === "library" && `共 ${fullLibrary.length} 篇论文，已有 ${fullLibrary.filter((paper) => paper.analysis).length} 篇关联深度分析。`}
                {section === "search" && "同时检索已入库论文和今日推荐，支持标题、会议、年份与研究主题。"}
                {section === "topics" && "一篇论文可以属于多个研究项目；这里展示当前主要研究脉络。"}
                {section === "reading" && "把感兴趣但暂时没有时间读的论文集中放在这里。"}
                {section === "import" && "拖入 PDF 或 Markdown，也可以粘贴 DOI、arXiv 或论文网页地址。"}
              </p>
            </div>

            {section !== "import" ? (
              <div className="flex w-full flex-col gap-2 sm:flex-row xl:w-auto">
                {directoryPickerSupported ? (
                  <button
                    type="button"
                    onClick={configurePaperDirectory}
                    className="h-11 shrink-0 rounded-xl border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50"
                    title="选择自动保存 PDF 的本地文件夹"
                  >
                    {paperDirectory ? `自动保存：${paperDirectory.name}` : "设置自动保存文件夹"}
                  </button>
                ) : null}
                <label className="relative block w-full sm:w-80">
                  <span className="sr-only">搜索论文</span>
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => {
                      setQuery(event.target.value);
                      if (event.target.value && section !== "search") setSection("search");
                    }}
                    placeholder="搜索标题、会议或方法…"
                    className="h-11 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />
                </label>
              </div>
            ) : (
              <button type="button" onClick={() => fileInput.current?.click()} className="h-11 rounded-xl bg-slate-950 px-5 text-sm font-medium text-white transition hover:bg-blue-600">选择文件</button>
            )}
          </header>

          {section === "today" ? <TodayView papers={recommendations} libraryCount={fullLibrary.length} analysisCount={fullLibrary.filter((paper) => paper.analysis).length} feedback={feedback} processedCount={processedCount} onFeedback={giveFeedback} onLocalSave={savePaperLocally} onOpenLibrary={() => openSection("library")} /> : null}
          {section === "library" ? <LibraryView papers={fullLibrary.filter((paper) => includesQuery(paper, query))} onLocalSave={savePaperLocally} /> : null}
          {section === "search" ? <SearchView query={query} results={searchResults} onLocalSave={savePaperLocally} /> : null}
          {section === "topics" ? <TopicsView topics={topics} papers={fullLibrary} /> : null}
          {section === "reading" ? <ReadingView papers={readingList} onSave={(paper) => giveFeedback(paper, "saved")} onLocalSave={savePaperLocally} /> : null}
          {section === "import" ? <ImportView pickedFiles={pickedFiles} fileInput={fileInput} uploading={uploading} onUpload={uploadPickedFiles} onFiles={(files) => setPickedFiles(Array.from(files))} /> : null}
        </section>
      </div>

      <div className="fixed bottom-4 left-1/2 z-20 hidden -translate-x-1/2 rounded-full bg-slate-950 px-4 py-2 text-xs text-white shadow-xl sm:block">{notice}</div>
    </main>
  );
}

function Stats({ libraryCount, analysisCount, processedCount, recommendationCount, onOpenLibrary }: { libraryCount: number; analysisCount: number; processedCount: number; recommendationCount: number; onOpenLibrary: () => void }) {
  return (
    <div className="mt-6 grid gap-4 sm:grid-cols-3">
      {[[String(libraryCount), "已收录论文"], [String(analysisCount), "已关联深度分析"], [processedCount ? `${processedCount}/${recommendationCount}` : String(recommendationCount), processedCount ? "今日已反馈" : "今日待筛选"]].map(([value, label], index) => (
        <button key={label} type="button" onClick={index === 0 ? onOpenLibrary : undefined} className="rounded-xl border border-slate-200 bg-white px-5 py-4 text-left shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:border-slate-300">
          <p className="text-2xl font-semibold tracking-tight">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{label}</p>
        </button>
      ))}
    </div>
  );
}

function TodayView({ papers, libraryCount, analysisCount, feedback, processedCount, onFeedback, onLocalSave, onOpenLibrary }: { papers: Paper[]; libraryCount: number; analysisCount: number; feedback: Record<string, Feedback>; processedCount: number; onFeedback: (paper: Paper, value: Feedback) => void; onLocalSave: (paper: Paper) => void; onOpenLibrary: () => void }) {
  const progress = papers.length ? Math.round((processedCount / papers.length) * 100) : 0;
  return (
    <>
      <Stats libraryCount={libraryCount} analysisCount={analysisCount} processedCount={processedCount} recommendationCount={papers.length} onOpenLibrary={onOpenLibrary} />
      <div className="mt-8 flex items-end justify-between gap-4">
        <div><h3 className="text-lg font-semibold">推荐队列</h3><p className="mt-1 text-xs text-slate-500">每日更新 10 篇 · 20% 用于探索新方向</p></div>
        <div className="text-right"><p className="text-xs font-medium text-slate-600">今日进度 {processedCount}/{papers.length}</p><div className="mt-2 h-1.5 w-28 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} /></div></div>
      </div>

      <div className="mt-4 space-y-4">
        {papers.map((paper, index) => {
          const state = feedback[paper.id];
          return (
            <article key={paper.id} className={`grid gap-5 rounded-2xl border bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition md:grid-cols-[1fr_auto] md:p-6 ${state ? "border-slate-200 opacity-70" : "border-slate-200 hover:border-blue-200"}`}>
              <div className="min-w-0">
                <PaperMeta paper={paper} />
                <h4 className="mt-3 text-lg font-semibold leading-7 tracking-tight sm:text-xl"><span className="mr-3 text-sm font-medium text-slate-300">{String(index + 1).padStart(2, "0")}</span>{paper.title}</h4>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{paper.reason}</p>
                <div className="mt-4"><PaperLinks paper={paper} compact onSaveLocally={onLocalSave} /></div>
                {state ? <p className="mt-3 text-xs font-medium text-blue-600">{state === "saved" && "✓ 已存入论文库"}{state === "later" && "✓ 已加入稍后阅读"}{state === "dismissed" && "✓ 已记录为不感兴趣"}</p> : null}
              </div>
              <div className="flex flex-wrap items-center gap-2 md:w-36 md:flex-col md:items-stretch md:justify-center">
                <button disabled={Boolean(state)} type="button" onClick={() => onFeedback(paper, "saved")} className="h-10 rounded-lg bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-blue-600 disabled:cursor-default disabled:bg-slate-300">存入论文库</button>
                <button disabled={Boolean(state)} type="button" onClick={() => onFeedback(paper, "later")} className="h-10 rounded-lg border border-slate-300 px-4 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-default disabled:text-slate-300">稍后阅读</button>
                <button disabled={Boolean(state)} type="button" onClick={() => onFeedback(paper, "dismissed")} className="h-8 px-3 text-xs text-slate-400 transition hover:text-rose-600 disabled:cursor-default disabled:text-slate-300">不感兴趣</button>
              </div>
            </article>
          );
        })}
      </div>
      {papers.length === 0 ? <EmptyState title="今天还没有推荐" text="推荐任务生成后会显示在这里。" /> : null}
    </>
  );
}

function LibraryView({ papers, onLocalSave }: { papers: Paper[]; onLocalSave: (paper: Paper) => void }) {
  return (
    <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="hidden grid-cols-[minmax(0,1fr)_140px_100px_220px] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-medium text-slate-500 md:grid"><span>论文</span><span>主题</span><span>状态</span><span>打开资料</span></div>
      {papers.map((paper) => (
        <article key={paper.id} className="grid gap-3 border-b border-slate-100 px-5 py-4 last:border-0 md:grid-cols-[minmax(0,1fr)_140px_100px_220px] md:items-center md:gap-4">
          <div className="min-w-0"><h3 className="truncate text-sm font-semibold" title={paper.title}>{paper.title}</h3><p className="mt-1 text-xs text-slate-500">{paper.venue} · {paper.year}</p></div>
          <span className="text-xs text-slate-600">{paper.topic}</span>
          <span className={`w-fit rounded-full px-2 py-1 text-xs ${paper.status === "已读" ? "bg-emerald-50 text-emerald-700" : paper.status === "阅读中" ? "bg-blue-50 text-blue-700" : "bg-slate-100 text-slate-600"}`}>{paper.status}</span>
          <PaperLinks paper={paper} onSaveLocally={onLocalSave} />
        </article>
      ))}
      {papers.length === 0 ? <EmptyState title="没有找到论文" text="试试标题、会议名称或研究主题。" /> : null}
    </div>
  );
}

function SearchView({ query, results, onLocalSave }: { query: string; results: Paper[]; onLocalSave: (paper: Paper) => void }) {
  if (!query) return <EmptyState title="输入你想研究的问题" text="例如：无动作标签的视频世界模型、世界坐标人体恢复、CVPR 2025。" />;
  return (
    <div className="mt-6">
      <p className="text-sm text-slate-500">找到 {results.length} 条与“{query}”相关的结果</p>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        {results.map((paper) => <article key={paper.id} className="rounded-2xl border border-slate-200 bg-white p-5"><PaperMeta paper={paper} /><h3 className="mt-3 text-base font-semibold leading-6">{paper.title}</h3><p className="mt-3 text-xs text-slate-500">来源：{paper.source}{paper.analysis ? " · 已关联深度分析" : ""}</p><div className="mt-4"><PaperLinks paper={paper} compact onSaveLocally={onLocalSave} /></div></article>)}
      </div>
      {results.length === 0 ? <EmptyState title="没有匹配结果" text="换一个更宽泛的关键词，或到导入页面添加论文。" /> : null}
    </div>
  );
}

function TopicsView({ topics, papers }: { topics: [string, number][]; papers: Paper[] }) {
  const max = Math.max(...topics.map(([, count]) => count), 1);
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-2">
      {topics.map(([topic, count]) => <article key={topic} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center justify-between"><h3 className="font-semibold">{topic}</h3><span className="text-xs text-slate-500">{count} 篇</span></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.max((count / max) * 100, 16)}%` }} /></div><p className="mt-4 line-clamp-2 text-xs leading-5 text-slate-500">{papers.filter((paper) => paper.topic === topic).map((paper) => paper.title.split(":")[0]).join(" · ")}</p></article>)}
    </div>
  );
}

function ReadingView({ papers, onSave, onLocalSave }: { papers: Paper[]; onSave: (paper: Paper) => void; onLocalSave: (paper: Paper) => void }) {
  if (!papers.length) return <EmptyState title="稍后阅读还是空的" text="在今日推荐中点击“稍后阅读”，论文就会出现在这里。" />;
  return <div className="mt-6 space-y-4">{papers.map((paper) => <article key={paper.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"><div><PaperMeta paper={paper} /><h3 className="mt-3 font-semibold">{paper.title}</h3><div className="mt-4"><PaperLinks paper={paper} compact onSaveLocally={onLocalSave} /></div></div><button type="button" onClick={() => onSave(paper)} className="h-10 shrink-0 rounded-lg bg-slate-950 px-4 text-sm font-medium text-white hover:bg-blue-600">读完后入库</button></article>)}</div>;
}

function ImportView({ pickedFiles, fileInput, uploading, onUpload, onFiles }: { pickedFiles: File[]; fileInput: React.RefObject<HTMLInputElement | null>; uploading: boolean; onUpload: () => void; onFiles: (files: FileList) => void }) {
  return (
    <div className="mt-6 grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
      <button type="button" onClick={() => fileInput.current?.click()} className="group flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center transition hover:border-blue-400 hover:bg-blue-50/30">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-2xl text-blue-600 transition group-hover:scale-105">＋</span><span className="mt-5 text-base font-semibold">选择 PDF 或 Markdown</span><span className="mt-2 max-w-sm text-sm leading-6 text-slate-500">支持批量选择；系统会提取标题、作者、摘要并检查重复论文。</span>
        <input ref={fileInput} className="hidden" type="file" multiple accept=".pdf,.md,text/markdown,application/pdf" onChange={(event) => event.target.files && onFiles(event.target.files)} />
      </button>
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="font-semibold">已发现的本地资料</h3><div className="mt-4 space-y-3"><SourceRow name="桌面 / 论文" detail="11 份 PDF · 约 90 MB" status="待安全上传" /><SourceRow name="桌面 / 论文方法深度分析" detail="42 份 Markdown · 含重复版本" status="待去重关联" /></div><p className="mt-5 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">在私人存储与登录保护完成前，不会把这些文件放进公开网站仓库。</p>
      </div>
      {pickedFiles.length ? <div className="rounded-2xl border border-slate-200 bg-white p-5 xl:col-span-2"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">本次选择</h3><span className="mt-1 block text-xs text-slate-500">{pickedFiles.length} 个文件 · 将上传到私人存储</span></div><button type="button" disabled={uploading} onClick={onUpload} className="h-10 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-wait disabled:bg-slate-400">{uploading ? "正在上传…" : "开始安全上传"}</button></div><ul className="mt-4 grid gap-2 sm:grid-cols-2">{pickedFiles.slice(0, 8).map((file, index) => <li key={`${file.name}-${index}`} className="flex min-w-0 items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"><span className="truncate">{file.name}</span><span className="shrink-0 text-slate-400">{(file.size / 1024 / 1024).toFixed(1)} MB</span></li>)}</ul></div> : null}
    </div>
  );
}

function SourceRow({ name, detail, status }: { name: string; detail: string; status: string }) {
  return <div className="rounded-xl border border-slate-200 p-4"><p className="text-sm font-medium">{name}</p><p className="mt-1 text-xs text-slate-500">{detail}</p><p className="mt-3 text-xs font-medium text-blue-600">{status}</p></div>;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="mt-6 flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center"><span className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-lg text-slate-400">⌕</span><h3 className="mt-4 font-semibold">{title}</h3><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">{text}</p></div>;
}
