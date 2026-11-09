import type { Metadata } from "next";
import { Workspace } from "@/components/workspace";

export const metadata: Metadata = { title: "People" };
export default function PeoplePage() {
  return <Workspace page="people" />;
}
