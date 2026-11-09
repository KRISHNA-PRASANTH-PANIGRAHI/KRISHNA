import type { Metadata } from "next";
import { Workspace } from "@/components/workspace";

export const metadata: Metadata = { title: "Classes" };
export default function ClassesPage() {
  return <Workspace page="classes" />;
}
