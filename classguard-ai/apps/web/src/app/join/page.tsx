import type { Metadata } from "next";
import { Workspace } from "@/components/workspace";

export const metadata: Metadata = {
  title: "Join your institution",
  robots: { index: false, follow: false },
};
export default function JoinPage() {
  return <Workspace page="join" />;
}
