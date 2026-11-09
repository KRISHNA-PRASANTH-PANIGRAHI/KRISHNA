import type { Metadata } from "next";
import { Workspace } from "@/components/workspace";

export const metadata: Metadata = { title: "Setup" };
export default function SetupPage() {
  return <Workspace page="setup" />;
}
