import type { Metadata } from "next";
import PaperLibrary from "./paper-library";

export const metadata: Metadata = {
  title: "Paper Library | Ruiyuan",
  description: "Ruiyuan's private computer vision paper library and daily reading feed.",
};

export default function PapersPage() {
  return <PaperLibrary />;
}
