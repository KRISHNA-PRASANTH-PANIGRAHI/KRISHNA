import type { Metadata } from "next";
import { Workspace } from "@/components/workspace";

export const metadata: Metadata = { title: "Attendance" };
export default function AttendancePage() {
  return <Workspace page="attendance" />;
}
