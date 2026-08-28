"use server";

import { randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requirePaperOwner } from "@/lib/paper-auth";
import { chinaDate, type RecommendationFeedback } from "@/lib/papers";

type ActionResult = { ok: true } | { ok: false; error: string };

export async function setRecommendationAction(
  slug: string,
  action: RecommendationFeedback,
): Promise<ActionResult> {
  if (!slug || !["saved", "later", "dismissed"].includes(action)) {
    return { ok: false, error: "反馈内容无效。" };
  }

  const { supabase, userId } = await requirePaperOwner();
  const { data: paper, error: paperError } = await supabase
    .from("papers")
    .select("id")
    .eq("owner_id", userId)
    .eq("slug", slug)
    .single();

  if (paperError || !paper) return { ok: false, error: "没有找到这篇推荐论文。" };

  const { error: feedbackError } = await supabase
    .from("daily_recommendations")
    .update({ action, acted_at: new Date().toISOString() })
    .eq("owner_id", userId)
    .eq("paper_id", paper.id)
    .eq("recommendation_date", chinaDate());

  if (feedbackError) return { ok: false, error: "反馈保存失败，请重试。" };

  if (action === "saved") {
    const { error: saveError } = await supabase
      .from("papers")
      .update({ is_in_library: true, updated_at: new Date().toISOString() })
      .eq("owner_id", userId)
      .eq("id", paper.id);
    if (saveError) return { ok: false, error: "论文暂时无法存入库中。" };
  }

  revalidatePath("/papers");
  return { ok: true };
}

export async function registerUploadedFile(input: {
  storagePath: string;
  filename: string;
  mimeType: string;
  size: number;
}): Promise<ActionResult> {
  const { supabase, userId } = await requirePaperOwner();
  const filename = input.filename.trim().slice(0, 500);
  const allowedMimeTypes = new Set(["application/pdf", "text/markdown", "text/plain"]);

  if (
    !filename ||
    !input.storagePath.startsWith(`${userId}/`) ||
    input.storagePath.includes("..") ||
    !allowedMimeTypes.has(input.mimeType) ||
    input.size <= 0 ||
    input.size > 50 * 1024 * 1024
  ) {
    return { ok: false, error: "文件信息无效。" };
  }

  const isPdf = input.mimeType === "application/pdf";
  const title = filename.replace(/\.(pdf|md|markdown)$/i, "");
  const { error } = await supabase.from("papers").insert({
    owner_id: userId,
    slug: `upload-${randomUUID()}`,
    title,
    topic: "待分类",
    reading_status: "unread",
    origin: "upload",
    is_in_library: true,
    pdf_storage_path: isPdf ? input.storagePath : null,
    analysis_storage_path: isPdf ? null : input.storagePath,
  });

  if (error) return { ok: false, error: "文件已上传，但论文记录创建失败。" };
  revalidatePath("/papers");
  return { ok: true };
}

export async function signOutPaperLibrary() {
  const { supabase } = await requirePaperOwner();
  await supabase.auth.signOut();
  redirect("/papers/login");
}
