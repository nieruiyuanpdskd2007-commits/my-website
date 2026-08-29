import { NextResponse } from "next/server";
import { libraryPapers, recommendedPapers, type Paper } from "@/app/papers/data";
import { requirePaperOwner } from "@/lib/paper-auth";

type PaperLinkRow = {
  title: string;
  doi: string | null;
  arxiv_id: string | null;
  source_url: string | null;
  pdf_storage_path: string | null;
  analysis_storage_path: string | null;
};

function safeHttpUrl(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function sourceUrl(paper: PaperLinkRow, seed?: Paper) {
  const storedUrl = safeHttpUrl(paper.source_url);
  if (storedUrl) return storedUrl;

  const seededUrl = safeHttpUrl(seed?.sourceUrl ?? null);
  if (seededUrl) return seededUrl;

  const doi = paper.doi?.trim().replace(/^https?:\/\/(dx\.)?doi\.org\//i, "");
  if (doi) return `https://doi.org/${doi}`;

  const arxivId = (paper.arxiv_id ?? seed?.arxivId)?.trim().replace(/^arxiv:/i, "");
  if (arxivId && /^[a-z0-9.\/-]+(?:v\d+)?$/i.test(arxivId)) {
    return `https://arxiv.org/abs/${arxivId}`;
  }

  const search = new URL("https://arxiv.org/search/");
  search.searchParams.set("query", paper.title);
  search.searchParams.set("searchtype", "title");
  search.searchParams.set("abstracts", "show");
  search.searchParams.set("order", "-announced_date_first");
  return search.toString();
}

function privateRedirect(destination: string, requestUrl: string) {
  const response = NextResponse.redirect(new URL(destination, requestUrl));
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export async function GET(
  request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  const { supabase, userId } = await requirePaperOwner();
  const kind = new URL(request.url).searchParams.get("kind");

  const { data, error } = await supabase
    .from("papers")
    .select("title, doi, arxiv_id, source_url, pdf_storage_path, analysis_storage_path")
    .eq("owner_id", userId)
    .eq("slug", slug)
    .single();

  if (error || !data) return privateRedirect("/papers", request.url);
  const paper = data as PaperLinkRow;
  const seed = [...libraryPapers, ...recommendedPapers].find((item) => item.id === slug);
  const storagePath = kind === "analysis"
    ? paper.analysis_storage_path
    : kind === "pdf"
      ? paper.pdf_storage_path
      : null;

  if (storagePath) {
    const { data: signedFile, error: signedFileError } = await supabase.storage
      .from("papers")
      .createSignedUrl(storagePath, 60 * 10);

    if (!signedFileError && signedFile?.signedUrl) {
      return privateRedirect(signedFile.signedUrl, request.url);
    }
  }

  const externalPdfUrl = safeHttpUrl(seed?.externalPdfUrl ?? null);
  if (kind === "pdf" && externalPdfUrl) {
    return privateRedirect(externalPdfUrl, request.url);
  }

  return privateRedirect(sourceUrl(paper, seed), request.url);
}
