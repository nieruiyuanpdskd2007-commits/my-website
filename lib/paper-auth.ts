import "server-only";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

type PaperOwner = {
  supabase: Awaited<ReturnType<typeof createClient>>;
  userId: string;
  email: string;
};

export async function getPaperOwner(): Promise<PaperOwner | null> {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getClaims();
  const ownerEmail = process.env.PAPER_LIBRARY_OWNER_EMAIL?.trim().toLowerCase();
  const email = String(data?.claims?.email ?? "").trim().toLowerCase();
  const userId = String(data?.claims?.sub ?? "");

  if (error || !ownerEmail || !userId || email !== ownerEmail) return null;
  return { supabase, userId, email };
}

export async function requirePaperOwner(): Promise<PaperOwner> {
  const owner = await getPaperOwner();
  if (!owner) redirect("/papers/login");
  return owner;
}
