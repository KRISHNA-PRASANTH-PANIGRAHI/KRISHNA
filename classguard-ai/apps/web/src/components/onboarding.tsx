"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { requestMessage, useRequestLifetime } from "@/lib/request-scope";
import type { Membership } from "@/lib/types";
import { useApp } from "./app-provider";
import { Icon } from "./icons";
import { Modal } from "./modal";
import { SignInModal } from "./forms";

export function InstitutionSetup({ onSignIn }: { onSignIn: () => void }) {
  const app = useApp();
  const [createOpen, setCreateOpen] = useState(false);
  useEffect(() => setCreateOpen(false), [app.session?.user.id, app.preview]);
  if (app.preview) return null;
  return (
    <section className="panel institution-onboarding">
      <span className="onboarding-symbol">
        <Icon name="book" size={25} />
      </span>
      <div className="onboarding-copy">
        <h2>
          {app.institution
            ? "Grow your learning community"
            : "Your institution starts here"}
        </h2>
        <p>
          {app.institution
            ? "Manage people and give students access to their classes."
            : "Set up a school, college, or coaching workspace. Joining an existing institution? Open the invitation link your administrator shared."}
        </p>
      </div>
      <div className="onboarding-actions">
        {!app.session ? (
          <button className="button primary" onClick={onSignIn}>
            <Icon name="lock" size={16} />
            Sign in to get started
          </button>
        ) : app.profileLoading ? (
          <span role="status" className="muted">
            Loading access…
          </span>
        ) : app.profileError ? (
          <button className="button secondary" onClick={app.refresh}>
            Retry connection
          </button>
        ) : (
          <>
            {app.institution && (
              <Link href="/people" className="button secondary">
                View people
                <Icon name="arrow" size={16} />
              </Link>
            )}
            <button
              className={`button ${app.institution ? "subtle" : "primary"}`}
              disabled={app.apiStatus !== "online"}
              onClick={() => setCreateOpen(true)}
            >
              <Icon name="plus" size={16} />
              Create institution
            </button>
          </>
        )}
      </div>
      {createOpen && app.session && (
        <CreateInstitutionModal
          key={app.session.user.id}
          onClose={() => setCreateOpen(false)}
        />
      )}
    </section>
  );
}

function CreateInstitutionModal({ onClose }: { onClose: () => void }) {
  const app = useApp();
  const lifetime = useRequestLifetime();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!app.session || app.preview || busy) return;
    const name = String(
      new FormData(event.currentTarget).get("name") || "",
    ).trim();
    if (!name) {
      setError("Enter your institution’s name.");
      return;
    }
    const signal = lifetime.current?.signal;
    setBusy(true);
    setError("");
    try {
      const membership = await apiRequest<Membership>("/v1/institutions", {
        method: "POST",
        token: app.session.access_token,
        signal,
        body: { name },
      });
      if (signal?.aborted) return;
      app.setInstitutionId(membership.institution_id);
      app.refresh();
      onClose();
    } catch (error) {
      if (!signal?.aborted)
        setError(
          requestMessage(error, "The institution could not be created."),
        );
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }
  return (
    <Modal title="Create your institution" onClose={onClose}>
      <p className="modal-intro">
        You’ll become the administrator of this new workspace. Invite your
        teachers and students once it’s ready.
      </p>
      <form className="form-stack" onSubmit={submit}>
        <label>
          Institution name
          <input
            name="name"
            placeholder="e.g. Greenfield Academy"
            required
            maxLength={160}
            disabled={busy}
            autoComplete="organization"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="form-actions">
          <button
            type="button"
            className="button subtle"
            onClick={onClose}
            disabled={busy}
          >
            Cancel
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Creating…" : "Create institution"}
            <Icon name="plus" size={16} />
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function JoinInstitution() {
  const app = useApp();
  const [token, setToken] = useState("");
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    const readFragment = () => {
      const value =
        new URLSearchParams(window.location.hash.slice(1)).get("token") || "";
      setToken(value.length <= 512 ? value : "");
      setLoaded(true);
    };
    readFragment();
    window.addEventListener("hashchange", readFragment);
    return () => window.removeEventListener("hashchange", readFragment);
  }, []);
  return (
    <JoinInvitationForm
      key={`${app.session?.user.id || "signed-out"}:${token}`}
      token={token}
      loaded={loaded}
      onAccepted={() => {
        window.history.replaceState(
          null,
          "",
          window.location.pathname + window.location.search,
        );
      }}
    />
  );
}

function JoinInvitationForm({
  token,
  loaded,
  onAccepted,
}: {
  token: string;
  loaded: boolean;
  onAccepted: () => void;
}) {
  const app = useApp();
  const lifetime = useRequestLifetime();
  const [signInOpen, setSignInOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [joined, setJoined] = useState<Membership | null>(null);
  async function accept() {
    if (!app.session || !token || busy || app.preview) return;
    const signal = lifetime.current?.signal;
    setBusy(true);
    setError("");
    try {
      const membership = await apiRequest<Membership>(
        "/v1/invitations/accept",
        {
          method: "POST",
          token: app.session.access_token,
          signal,
          body: { token },
        },
      );
      if (signal?.aborted) return;
      setJoined(membership);
      onAccepted();
      app.setInstitutionId(membership.institution_id);
      app.refresh();
    } catch (error) {
      if (!signal?.aborted)
        setError(
          requestMessage(error, "The invitation could not be accepted."),
        );
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A PLACE IN YOUR COMMUNITY</div>
          <h1>Join your institution.</h1>
          <p>
            Use your personal invitation to connect to your learning workspace.
          </p>
        </div>
      </div>
      <section className="panel join-panel">
        <div className="empty-icon">
          <Icon name={joined ? "check" : "users"} size={32} />
        </div>
        {joined ? (
          <>
            <h2>You’re part of {joined.institution_name}</h2>
            <p className="muted" role="status">
              Your {joined.role} access is ready. Your institution controls
              which classes are shared with you.
            </p>
            <Link href="/classes" className="button primary">
              Go to classes
              <Icon name="arrow" size={17} />
            </Link>
          </>
        ) : !loaded || app.authLoading ? (
          <p role="status">Loading invitation…</p>
        ) : !token ? (
          <>
            <h2>Open your invitation link</h2>
            <p className="muted">
              Ask your administrator to share a new invitation link. It includes
              the details needed to join your institution.
            </p>
            <Link href="/" className="button secondary">
              Back to dashboard
            </Link>
          </>
        ) : app.preview ? (
          <>
            <h2>Return to your workspace to join</h2>
            <p className="muted">
              Invitations connect a real account to an institution.
            </p>
            <button
              className="button primary"
              onClick={() => app.setPreview(false)}
            >
              Exit design preview
            </button>
          </>
        ) : !app.session ? (
          <>
            <h2>Your invitation is ready</h2>
            <p className="muted">
              Sign in with the email address your administrator invited. Keep
              this page open while signing in.
            </p>
            <button
              className="button primary"
              onClick={() => setSignInOpen(true)}
            >
              Sign in to accept
              <Icon name="lock" size={17} />
            </button>
            <p className="fine-print">
              If you don’t have an account yet, ask your administrator to create
              one before using this invitation.
            </p>
          </>
        ) : (
          <>
            <h2>Ready to join?</h2>
            <p className="muted">
              You’re signed in as{" "}
              <strong className="wrap-anywhere">
                {app.session.user.email || "your institution account"}
              </strong>
              . This invitation must match your email address.
            </p>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="button primary"
              onClick={accept}
              disabled={busy || app.apiStatus !== "online"}
            >
              {busy ? "Joining…" : "Accept invitation"}
              <Icon name="arrow" size={17} />
            </button>
            {app.apiStatus !== "online" && (
              <p className="fine-print">
                Waiting for a connection to the classroom service.{" "}
                <button className="text-link" onClick={app.refresh}>
                  Check again
                </button>
              </p>
            )}
            <p className="fine-print">
              Wrong account?{" "}
              <button
                className="text-link"
                onClick={app.signOut}
                disabled={busy}
              >
                Sign out
              </button>{" "}
              and sign in with the invited email.
            </p>
          </>
        )}
      </section>
      {signInOpen && <SignInModal onClose={() => setSignInOpen(false)} />}
    </>
  );
}
