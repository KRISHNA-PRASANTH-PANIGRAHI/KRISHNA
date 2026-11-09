"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { apiRequest } from "@/lib/api";
import { authConfigured, getSupabase } from "@/lib/supabase";
import type { Capabilities, ClassPlan, Membership, Profile } from "@/lib/types";

interface AppContextValue {
  session: Session | null;
  authLoading: boolean;
  authError: string;
  profile: Profile | null;
  profileLoading: boolean;
  profileError: string;
  institution: Membership | undefined;
  setInstitutionId: (value: string) => void;
  classes: ClassPlan[];
  classesLoading: boolean;
  classesError: string;
  apiStatus: "checking" | "online" | "offline";
  capabilities: Capabilities | null;
  preview: boolean;
  setPreview: (value: boolean) => void;
  refresh: () => void;
  refreshClasses: () => void;
  signOut: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(authConfigured);
  const [authError, setAuthError] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [institutionId, setInstitutionId] = useState("");
  const [classes, setClasses] = useState<ClassPlan[]>([]);
  const [classesLoading, setClassesLoading] = useState(false);
  const [classesError, setClassesError] = useState("");
  const [apiStatus, setApiStatus] =
    useState<AppContextValue["apiStatus"]>("checking");
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [preview, setPreview] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [classesVersion, setClassesVersion] = useState(0);
  const token = session?.access_token;

  useEffect(() => {
    let active = true;
    try {
      const client = getSupabase();
      if (!client) {
        setAuthLoading(false);
        return;
      }
      client.auth
        .getSession()
        .then(({ data, error }) => {
          if (!active) return;
          setSession(data.session);
          setAuthError(error?.message || "");
          setAuthLoading(false);
        })
        .catch((error: Error) => {
          if (!active) return;
          setAuthError(error.message);
          setAuthLoading(false);
        });
      const { data } = client.auth.onAuthStateChange((_event, nextSession) => {
        if (!active) return;
        setSession(nextSession);
        setAuthLoading(false);
      });
      return () => {
        active = false;
        data.subscription.unsubscribe();
      };
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Authentication configuration is invalid.",
      );
      setAuthLoading(false);
    }
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => {
      controller.abort();
      if (active) setApiStatus("offline");
    }, 8000);
    setApiStatus("checking");
    setCapabilities(null);
    const healthRequest = apiRequest<{ status: string; service: string }>(
      "/health",
      { signal: controller.signal },
    )
      .then((health) => {
        if (active && !controller.signal.aborted)
          setApiStatus(
            health.status === "ok" && health.service === "classguard-api"
              ? "online"
              : "offline",
          );
      })
      .catch(() => {
        if (active) setApiStatus("offline");
      });
    const capabilitiesRequest = apiRequest<Capabilities>("/v1/capabilities", {
      signal: controller.signal,
    })
      .then((data) => {
        if (active && !controller.signal.aborted) setCapabilities(data);
      })
      .catch(() => {
        if (active) setCapabilities(null);
      });
    Promise.allSettled([healthRequest, capabilitiesRequest]).then(() =>
      window.clearTimeout(timeout),
    );
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [refreshVersion]);

  useEffect(() => {
    setProfile(null);
    setProfileError("");
    setClasses([]);
    if (!token) {
      setProfileLoading(false);
      return;
    }
    const controller = new AbortController();
    setProfileLoading(true);
    apiRequest<Profile>("/v1/me", { token, signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setProfile(data);
        setInstitutionId((current) =>
          data.memberships.some(
            (membership) => membership.institution_id === current,
          )
            ? current
            : data.memberships[0]?.institution_id || "",
        );
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setProfileError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setProfileLoading(false);
      });
    return () => controller.abort();
  }, [token, refreshVersion]);

  const institution = profile?.memberships.find(
    (membership) => membership.institution_id === institutionId,
  );

  useEffect(() => {
    setClasses([]);
    setClassesError("");
    if (!token || !institution) {
      setClassesLoading(false);
      return;
    }
    const controller = new AbortController();
    setClassesLoading(true);
    apiRequest<{ items: ClassPlan[] }>(
      `/v1/institutions/${encodeURIComponent(institution.institution_id)}/classes`,
      { token, signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) setClasses(data.items);
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setClassesError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setClassesLoading(false);
      });
    return () => controller.abort();
  }, [token, institution, classesVersion]);

  const refresh = useCallback(
    () => setRefreshVersion((value) => value + 1),
    [],
  );
  const refreshClasses = useCallback(
    () => setClassesVersion((value) => value + 1),
    [],
  );
  const signOut = useCallback(async () => {
    try {
      const client = getSupabase();
      const result = await client?.auth.signOut({ scope: "local" });
      if (result?.error) throw result.error;
      setSession(null);
      setPreview(false);
      setAuthError("");
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Sign out failed. Please try again.",
      );
    }
  }, []);

  const value = useMemo(
    () => ({
      session,
      authLoading,
      authError,
      profile,
      profileLoading,
      profileError,
      institution,
      setInstitutionId,
      classes,
      classesLoading,
      classesError,
      apiStatus,
      capabilities,
      preview,
      setPreview,
      refresh,
      refreshClasses,
      signOut,
    }),
    [
      session,
      authLoading,
      authError,
      profile,
      profileLoading,
      profileError,
      institution,
      classes,
      classesLoading,
      classesError,
      apiStatus,
      capabilities,
      preview,
      refresh,
      refreshClasses,
      signOut,
    ],
  );
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
