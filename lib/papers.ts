import "server-only";

import { libraryPapers as seedLibrary, recommendedPapers as seedRecommendations, type Paper } from "@/app/papers/data";
import { requirePaperOwner } from "@/lib/paper-auth";

export type RecommendationFeedback = "saved" | "later" | "dismissed";

type PaperRow = {
  id: string;
  slug: string;
  title: string;
  published_year: number | null;
  venue: string | null;
  topic: string | null;
  reading_status: "unread" | "reading" | "read";
  origin: "upload" | "doi" | "arxiv" | "recommendation";
  doi: string | null;
  arxiv_id: string | null;
  source_url: string | null;
  pdf_storage_path: string | null;
  analysis_storage_path: string | null;
  is_in_library: boolean;
};

type RecommendationRow = {
  paper_id: string;
  rank: number;
  score: number | string | null;
  reason: string | null;
  action: RecommendationFeedback | null;
};

function chinaDate() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function chinaDateLabel() {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
}

function toPaper(row: PaperRow, recommendation?: RecommendationRow): Paper {
  const originalSeed = seedLibrary.find((paper) => paper.id === row.slug);
  const score = recommendation?.score == null ? undefined : Number(recommendation.score);

  return {
    id: row.slug,
    title: row.title,
    year: row.published_year ?? new Date().getFullYear(),
    venue: row.venue ?? "待补充",
    topic: row.topic ?? "待分类",
    status: row.reading_status === "read" ? "已读" : row.reading_status === "reading" ? "阅读中" : "待读",
    source: row.origin === "recommendation" ? "推荐" : "本地 PDF",
    analysis: Boolean(row.analysis_storage_path) || Boolean(originalSeed?.analysis),
    reason: recommendation?.reason ?? undefined,
    match: score == null || Number.isNaN(score) ? undefined : Math.round(score * 100),
    hasPdf: Boolean(row.pdf_storage_path),
    hasAnalysisFile: Boolean(row.analysis_storage_path),
    sourceLinkKind: row.source_url || row.doi || row.arxiv_id ? "direct" : "search",
  };
}

async function ensureSeedData() {
  const { supabase, userId } = await requirePaperOwner();

  await supabase.from("paper_profiles").upsert(
    {
      owner_id: userId,
      interest_topics: ["视频世界模型", "人体运动恢复", "人体网格恢复", "人形机器人"],
      exploration_ratio: 0.2,
      daily_count: 10,
    },
    { onConflict: "owner_id", ignoreDuplicates: true },
  );

  const seedRows = [
    ...seedLibrary.map((paper) => ({
      owner_id: userId,
      slug: paper.id,
      title: paper.title,
      published_year: paper.year,
      venue: paper.venue,
      topic: paper.topic,
      reading_status: paper.status === "已读" ? "read" : paper.status === "阅读中" ? "reading" : "unread",
      origin: "upload",
      is_in_library: true,
    })),
    ...seedRecommendations.map((paper) => ({
      owner_id: userId,
      slug: paper.id,
      title: paper.title,
      published_year: paper.year,
      venue: paper.venue,
      topic: paper.topic,
      reading_status: "unread",
      origin: "recommendation",
      is_in_library: false,
    })),
  ];

  const { error: seedError } = await supabase
    .from("papers")
    .upsert(seedRows, { onConflict: "owner_id,slug", ignoreDuplicates: true });
  if (seedError) throw new Error(`Unable to seed paper metadata: ${seedError.message}`);

  const { data: seededPapers, error: paperError } = await supabase
    .from("papers")
    .select("id, slug")
    .eq("owner_id", userId)
    .in("slug", seedRecommendations.map((paper) => paper.id));
  if (paperError) throw new Error(`Unable to load recommendation metadata: ${paperError.message}`);

  const paperIds = new Map((seededPapers ?? []).map((paper) => [paper.slug, paper.id]));
  const recommendationRows = seedRecommendations.flatMap((paper, index) => {
    const paperId = paperIds.get(paper.id);
    if (!paperId) return [];
    return [{
      owner_id: userId,
      paper_id: paperId,
      recommendation_date: chinaDate(),
      rank: index + 1,
      score: (paper.match ?? 0) / 100,
      reason: paper.reason ?? null,
    }];
  });

  const { error: recommendationError } = await supabase
    .from("daily_recommendations")
    .upsert(recommendationRows, {
      onConflict: "owner_id,recommendation_date,paper_id",
      ignoreDuplicates: true,
    });
  if (recommendationError) throw new Error(`Unable to seed recommendations: ${recommendationError.message}`);

  return { supabase, userId };
}

export async function loadPaperLibrary() {
  const { supabase, userId } = await ensureSeedData();

  const [{ data: paperData, error: paperError }, { data: recommendationData, error: recommendationError }] = await Promise.all([
    supabase
      .from("papers")
      .select("id, slug, title, published_year, venue, topic, reading_status, origin, doi, arxiv_id, source_url, pdf_storage_path, analysis_storage_path, is_in_library")
      .eq("owner_id", userId)
      .order("created_at", { ascending: true }),
    supabase
      .from("daily_recommendations")
      .select("paper_id, rank, score, reason, action")
      .eq("owner_id", userId)
      .eq("recommendation_date", chinaDate())
      .order("rank", { ascending: true }),
  ]);

  if (paperError) throw new Error(`Unable to load papers: ${paperError.message}`);
  if (recommendationError) throw new Error(`Unable to load recommendations: ${recommendationError.message}`);

  const papers = (paperData ?? []) as PaperRow[];
  const recommendations = (recommendationData ?? []) as RecommendationRow[];
  const papersById = new Map(papers.map((paper) => [paper.id, paper]));

  const library = papers.filter((paper) => paper.is_in_library).map((paper) => toPaper(paper));
  const daily = recommendations.flatMap((recommendation) => {
    const paper = papersById.get(recommendation.paper_id);
    return paper ? [toPaper(paper, recommendation)] : [];
  });
  const feedback = Object.fromEntries(
    recommendations.flatMap((recommendation) => {
      const paper = papersById.get(recommendation.paper_id);
      return paper && recommendation.action ? [[paper.slug, recommendation.action]] : [];
    }),
  ) as Record<string, RecommendationFeedback>;

  return { library, recommendations: daily, feedback };
}

export { chinaDate };
