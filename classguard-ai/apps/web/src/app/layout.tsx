import type { Metadata, Viewport } from "next";
import { AppProvider } from "@/components/app-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ClassGuard AI — Learning workspace",
    template: "%s | ClassGuard AI",
  },
  description:
    "Your ClassGuard AI learning workspace for institution setup, invitations, class planning, and student enrollment.",
  applicationName: "ClassGuard AI",
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0b6253",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
