import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ATHLETIQ | Neuromuscular Intelligence Platform",
  description:
    "ATHLETIQ is a patent-backed neuromuscular risk platform that combines YOLOv8 pose detection, biomechanics scoring, and an AI coaching layer."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
