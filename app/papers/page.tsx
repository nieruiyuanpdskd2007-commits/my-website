import type { Metadata } from "next";
import { chinaDateLabel, loadPaperLibrary } from "@/lib/papers";
import { requirePaperOwner } from "@/lib/paper-auth";
import PaperLibrary from "./paper-library";

export const metadata: Metadata = {
  title: "Paper Library | Ruiyuan",
  description: "Ruiyuan's private computer vision paper library and daily reading feed.",
};

export default async function PapersPage() {
  await requirePaperOwner();
  const data = await loadPaperLibrary();

  return <PaperLibrary {...data} dateLabel={chinaDateLabel()} />;
}
