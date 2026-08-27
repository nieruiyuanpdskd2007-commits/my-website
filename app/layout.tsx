import type { Metadata } from "next";
import "./globals.css";
import Navbar from "../components/Navbar";

export const metadata: Metadata = {
  metadataBase: new URL("https://nieruiyuan.com"),
  title: "Ruiyuan's Personal Website",
  description: "Personal website, projects, and blog.",
  openGraph: {
    type: "website",
    url: "https://nieruiyuan.com",
    title: "Ruiyuan's Digital Garden",
    description: "Artificial intelligence, machine learning, computer vision, projects, and research notes.",
    images: [
      {
        url: "/og.png",
        width: 1672,
        height: 941,
        alt: "Ruiyuan's Digital Garden — AI, Machine Learning, and Computer Vision",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ruiyuan's Digital Garden",
    description: "Artificial intelligence, machine learning, computer vision, projects, and research notes.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
