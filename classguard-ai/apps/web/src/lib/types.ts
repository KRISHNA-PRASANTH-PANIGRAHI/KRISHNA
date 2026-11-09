export type Role = "admin" | "teacher" | "student";

export interface Membership {
  institution_id: string;
  institution_name: string;
  role: Role;
}

export interface Profile {
  id: string;
  email: string | null;
  memberships: Membership[];
}

export interface ClassPlan {
  id: string;
  institution_id: string;
  title: string;
  subject: string;
  description: string;
  starts_at: string;
  duration_minutes: number;
  created_by: string;
  created_at: string;
}

export interface NewClassPlan {
  title: string;
  subject: string;
  description?: string;
  starts_at: string;
  duration_minutes: number;
}

export interface Capabilities {
  authentication_configured: boolean;
  stage: string;
  features: {
    class_planning: boolean;
    institution_management: boolean;
    invitations: boolean;
    enrollment: boolean;
    verified_entry: boolean;
    live_video: boolean;
    attendance: boolean;
    polls: boolean;
  };
}

export interface MemberRecord {
  user_id: string;
  email: string | null;
  role: Role;
  active: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: "teacher" | "student";
  created_at: string;
  expires_at: string;
  status: "pending" | "accepted" | "revoked" | "expired";
}

export type PageName =
  | "dashboard"
  | "classes"
  | "people"
  | "join"
  | "attendance"
  | "setup";
