import { libraryPapers, recommendedPapers } from "@/app/papers/data";
import { requirePaperOwner } from "@/lib/paper-auth";

function downloadHeaders(title: string) {
  const encodedFilename = encodeURIComponent(`${title.slice(0, 180)}.pdf`);
  return {
    "Cache-Control": "private, no-store",
    "Content-Disposition": `attachment; filename="paper.pdf"; filename*=UTF-8''${encodedFilename}`,
    "Content-Type": "application/pdf",
    "X-Content-Type-Options": "nosniff",
  };
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  const { supabase, userId } = await requirePaperOwner();
  const { data: paper, error } = await supabase
    .from("papers")
    .select("title, pdf_storage_path")
    .eq("owner_id", userId)
    .eq("slug", slug)
    .single();

  if (error || !paper) {
    return Response.json({ error: "没有找到这篇论文。" }, { status: 404 });
  }

  if (paper.pdf_storage_path) {
    const { data: storedFile, error: storageError } = await supabase.storage
      .from("papers")
      .download(paper.pdf_storage_path);

    if (!storageError && storedFile) {
      return new Response(storedFile.stream(), { headers: downloadHeaders(paper.title) });
    }
  }

  const seed = [...libraryPapers, ...recommendedPapers].find((item) => item.id === slug);
  if (!seed?.externalPdfUrl) {
    return Response.json({ error: "这篇论文暂时没有可直接下载的 PDF。" }, { status: 404 });
  }

  const upstream = await fetch(seed.externalPdfUrl, {
    cache: "no-store",
    redirect: "follow",
    headers: { Accept: "application/pdf" },
  });
  const contentType = upstream.headers.get("content-type") ?? "";
  if (!upstream.ok || !upstream.body || !contentType.toLowerCase().includes("pdf")) {
    return Response.json({ error: "原文网站暂时无法提供 PDF 下载。" }, { status: 502 });
  }

  return new Response(upstream.body, { headers: downloadHeaders(paper.title) });
}
