"use client";

import { useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { useRequestLifetime } from "@/lib/request-scope";
import { authConfigured, getSupabase } from "@/lib/supabase";
import type { ClassPlan } from "@/lib/types";
import { useApp } from "./app-provider";
import { Icon } from "./icons";
import { Modal } from "./modal";

export function SignInModal({ onClose }: { onClose: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const client = getSupabase();
      if (!client)
        throw new Error(
          "Configure the Supabase URL and publishable key to enable sign-in.",
        );
      const { error: signInError } = await client.auth.signInWithPassword({
        email: String(fields.get("email")).trim(),
        password: String(fields.get("password")),
      });
      if (signInError) throw signInError;
      onClose();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Sign-in failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Welcome to ClassGuard" onClose={onClose}>
      <p className="modal-intro">
        Sign in with your institution account to view your classes.
      </p>
      {!authConfigured && (
        <div className="notice">
          Add the Supabase URL and publishable key to <code>.env.local</code>,
          then restart the web app to enable sign-in.
        </div>
      )}
      <form onSubmit={submit} className="form-stack">
        <label>
          Email address
          <input
            name="email"
            type="email"
            placeholder="you@school.edu"
            autoComplete="username"
            maxLength={254}
            required
            disabled={!authConfigured || busy}
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            disabled={!authConfigured || busy}
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button
          className="button primary full"
          type="submit"
          disabled={!authConfigured || busy}
        >
          {busy ? "Signing in…" : "Sign in"}
          <Icon name="arrow" size={18} />
        </button>
      </form>
      <p className="fine-print">
        Your institution administrator creates your account and assigns access.
        Contact them if you need an account or a password reset.
      </p>
    </Modal>
  );
}

export function CreateClassModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (classPlan: ClassPlan) => void;
}) {
  const { session, institution } = useApp();
  const lifetime = useRequestLifetime();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !institution) return;
    const fields = new FormData(event.currentTarget);
    const startsAt = new Date(String(fields.get("starts_at")));
    const title = String(fields.get("title")).trim();
    const subject = String(fields.get("subject")).trim();
    if (!title || !subject) {
      setError("Enter a class title and subject.");
      return;
    }
    if (Number.isNaN(startsAt.getTime())) {
      setError("Choose a valid class date and time.");
      return;
    }
    setBusy(true);
    setError("");
    const signal = lifetime.current?.signal;
    try {
      const classPlan = await apiRequest<ClassPlan>(
        `/v1/institutions/${encodeURIComponent(institution.institution_id)}/classes`,
        {
          method: "POST",
          token: session.access_token,
          signal,
          body: {
            title,
            subject,
            description: String(fields.get("description")).trim(),
            starts_at: startsAt.toISOString(),
            duration_minutes: Number(fields.get("duration_minutes")),
          },
        },
      );
      if (signal?.aborted) return;
      onCreated(classPlan);
      onClose();
    } catch (requestError) {
      if (signal?.aborted) return;
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The class could not be created.",
      );
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }

  return (
    <Modal title="Plan a class" onClose={onClose}>
      <p className="modal-intro">
        Create a class plan for {institution?.institution_name}. Live video will
        be available after the media service is integrated.
      </p>
      <form onSubmit={submit} className="form-stack">
        <label>
          Class title
          <input
            name="title"
            placeholder="Introduction to motion"
            required
            maxLength={160}
            disabled={busy}
          />
        </label>
        <label>
          Subject
          <input
            name="subject"
            placeholder="Physics"
            required
            maxLength={100}
            disabled={busy}
          />
        </label>
        <div className="form-row">
          <label>
            Start date and time
            <input
              name="starts_at"
              type="datetime-local"
              required
              disabled={busy}
            />
          </label>
          <label>
            Duration in minutes
            <input
              name="duration_minutes"
              type="number"
              min={5}
              max={480}
              defaultValue={45}
              required
              disabled={busy}
            />
          </label>
        </div>
        <p className="field-help">
          Times use {timezone}. The API stores the equivalent time with a
          timezone.
        </p>
        <label>
          Lesson description <span className="optional">optional</span>
          <textarea
            name="description"
            placeholder="What will students learn?"
            rows={3}
            maxLength={2000}
            disabled={busy}
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="form-actions">
          <button
            className="button subtle"
            type="button"
            onClick={onClose}
            disabled={busy}
          >
            Cancel
          </button>
          <button className="button primary" type="submit" disabled={busy}>
            {busy ? "Saving class…" : "Create class plan"}
            <Icon name="plus" size={18} />
          </button>
        </div>
      </form>
    </Modal>
  );
}
